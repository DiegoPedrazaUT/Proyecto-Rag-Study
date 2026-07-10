import httpx
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from fastapi import HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import jwt, JWTError

from core.config import settings
from core.security import create_access_token, create_refresh_token, hash_token
from repositories.user_repository import UserRepository, RefreshTokenRepository
from database.models import Role, Career, User


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

GOOGLE_TEMP_TOKEN_EXPIRE_MINUTES = 15


def get_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def get_google_user_info(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error al intercambiar código con Google")

        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google no devolvió access token")

        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error al obtener la información de Google")

        google_user = user_response.json()

        email = google_user.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google no devolvió correo electrónico")

        if google_user.get("verified_email") is False:
            raise HTTPException(status_code=400, detail="El correo de Google no está verificado")

        return google_user


def _create_google_temp_token(google_user: dict) -> str:
    now = datetime.now(timezone.utc)

    temp_payload = {
        "email": google_user.get("email", "").lower(),
        "first_name": google_user.get("given_name", ""),
        "last_name": google_user.get("family_name", ""),
        "google_id": google_user.get("id"),
        "type": "google_temp",
        "iat": now,
        "exp": now + timedelta(minutes=GOOGLE_TEMP_TOKEN_EXPIRE_MINUTES),
    }

    if not temp_payload["email"] or not temp_payload["google_id"]:
        raise HTTPException(status_code=400, detail="Información de Google incompleta")

    return jwt.encode(temp_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_google_temp_token(temp_token: str) -> dict:
    try:
        payload = jwt.decode(temp_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != "google_temp":
            raise HTTPException(status_code=401, detail="Token temporal inválido")

        if not payload.get("email") or not payload.get("google_id"):
            raise HTTPException(status_code=401, detail="Token temporal incompleto")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="El token temporal expiró o fue alterado")


def _set_session_cookies_and_store_refresh(db: Session, user: User, response: Response) -> dict:
    token_data = {
        "sub": str(user.id),
        "role": str(user.role.role_name),
        "username": f"{user.first_name} {user.last_name}",
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    RefreshTokenRepository.create(
        db=db,
        user_id=str(user.id),
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {
        "message": "Sesión iniciada correctamente",
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role.role_name,
            "is_mfa_enabled": user.is_mfa_enabled
        }
    }


def process_google_login(db: Session, google_user: dict, response: Response):
    email = google_user.get("email", "").lower()
    google_id = google_user.get("id")

    user = UserRepository.get_by_email(db, email)

    if user:
        if not user.google_id: # type: ignore
            user.google_id = google_id  # type: ignore
            user.is_verified = True  # type: ignore
            UserRepository.update(db)

        return _set_session_cookies_and_store_refresh(db, user, response)

    temp_token = _create_google_temp_token(google_user)

    return {
        "status": "needs_completion",
        "message": "Google enlazado. Completa tu perfil para finalizar el registro.",
        "temp_token": temp_token,
        "temp_info": {
            "first_name": google_user.get("given_name", ""),
            "last_name": google_user.get("family_name", ""),
            "email": email
        }
    }


def complete_google_student_registration(db: Session, request_data, response: Response):
    payload = _decode_google_temp_token(request_data.temp_token)

    if UserRepository.get_by_email(db, payload["email"]):
        raise HTTPException(status_code=400, detail="El correo ya fue registrado. Intenta iniciar sesión.")

    existing_google_user = db.query(User).filter(User.google_id == payload["google_id"]).first()
    if existing_google_user:
        raise HTTPException(status_code=400, detail="Esta cuenta de Google ya fue registrada.")

    student_role = db.query(Role).filter(Role.role_name == "student").first()
    if not student_role:
        raise HTTPException(status_code=500, detail="Error en BD: Rol 'student' no existe")

    career = db.query(Career).filter(Career.career_id == request_data.career_id).first()
    if not career:
        raise HTTPException(status_code=400, detail="La carrera especificada no existe")

    base_user_data = {
        "role_id": student_role.role_id,
        "first_name": payload["first_name"],
        "last_name": payload["last_name"],
        "email": payload["email"],
        "password_hash": None,
        "google_id": payload["google_id"],
        "is_verified": True
    }

    profile_data = {
        "matricula": request_data.matricula,
        "career_id": request_data.career_id
    }

    try:
        new_user = UserRepository.create_student(db, base_user_data, profile_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo o la matrícula ya se encuentran registrados.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al guardar el perfil.")

    return _set_session_cookies_and_store_refresh(db, new_user, response)


def complete_google_teacher_registration(db: Session, request_data, response: Response):
    payload = _decode_google_temp_token(request_data.temp_token)

    if UserRepository.get_by_email(db, payload["email"]):
        raise HTTPException(status_code=400, detail="El correo ya fue registrado. Intenta iniciar sesión.")

    existing_google_user = db.query(User).filter(User.google_id == payload["google_id"]).first()
    if existing_google_user:
        raise HTTPException(status_code=400, detail="Esta cuenta de Google ya fue registrada.")

    teacher_role = db.query(Role).filter(Role.role_name == "teacher").first()
    if not teacher_role:
        raise HTTPException(status_code=500, detail="Error en BD: Rol 'teacher' no existe")

    career = db.query(Career).filter(Career.career_id == request_data.career_id).first()
    if not career:
        raise HTTPException(status_code=400, detail="La carrera/departamento especificado no existe")

    base_user_data = {
        "role_id": teacher_role.role_id,
        "first_name": payload["first_name"],
        "last_name": payload["last_name"],
        "email": payload["email"],
        "password_hash": None,
        "google_id": payload["google_id"],
        "is_verified": True
    }

    profile_data = {
        "career_id": request_data.career_id
    }

    try:
        new_user = UserRepository.create_teacher(db, base_user_data, profile_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al guardar el perfil.")

    return _set_session_cookies_and_store_refresh(db, new_user, response)