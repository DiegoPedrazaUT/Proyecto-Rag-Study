import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response, Cookie, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database.database import get_db
from api import schemas, docs
from services import session_service, google_service
from core.config import settings
from core.security import verify_refresh_token, create_access_token, create_refresh_token, hash_token
from repositories.user_repository import RefreshTokenRepository


router = APIRouter(prefix="/auth", tags=["Autenticación y Sesión"])

GOOGLE_STATE_COOKIE_NAME = "google_oauth_state"


@router.post("/login", **docs.LOGIN)
def login(login_data: schemas.UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    return session_service.authenticate_user(db, login_data, response)


@router.post("/logout", **docs.LOGOUT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    if refresh_token:
        RefreshTokenRepository.delete_by_hash(db, hash_token(refresh_token))

    response.delete_cookie(key="access_token", secure=True, httponly=True, samesite="none")
    response.delete_cookie(key="refresh_token", secure=True, httponly=True, samesite="none")

    return {"message": "Sesión cerrada exitosamente"}


@router.post("/refresh", **docs.REFRESH)
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No hay Refresh Token en las cookies")

    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    old_token_hash = hash_token(refresh_token)
    stored_token = RefreshTokenRepository.get_valid_by_hash(db, old_token_hash)

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token revocado o no registrado")

    RefreshTokenRepository.delete_by_hash(db, old_token_hash)

    token_data = {
        "sub": payload.get("sub"),
        "role": payload.get("role")
    }

    if payload.get("username"):
        token_data["username"] = payload.get("username")

    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    RefreshTokenRepository.create(
        db=db,
        user_id=str(payload.get("sub")),
        token_hash=hash_token(new_refresh_token),
        expires_at=refresh_expires_at
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {"message": "Token renovado exitosamente"}


@router.get("/google", **docs.GOOGLE_LOGIN)
def login_with_google():
    state = secrets.token_urlsafe(32)

    google_auth_url = google_service.get_google_auth_url(state)

    redirect = RedirectResponse(google_auth_url)
    redirect.set_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=10 * 60
    )

    return redirect


@router.get("/google/callback", **docs.GOOGLE_CALLBACK)
async def google_callback(
    code: str,
    state: str,
    response: Response,
    google_oauth_state: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    if not google_oauth_state or not secrets.compare_digest(google_oauth_state, state):
        raise HTTPException(status_code=400, detail="State OAuth inválido o expirado")

    response.delete_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        secure=True,
        httponly=True,
        samesite="none"
    )

    google_user = await google_service.get_google_user_info(code)
    result = google_service.process_google_login(db, google_user, response)

    if result.get("status") == "needs_completion":
        response.status_code = status.HTTP_202_ACCEPTED

    return result


@router.post("/google/complete-student", **docs.COMPLETE_STUDENT)
def complete_google_student(
    request: schemas.CompleteStudentProfileRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    return google_service.complete_google_student_registration(db, request, response)


@router.post("/google/complete-teacher", **docs.COMPLETE_TEACHER)
def complete_google_teacher(
    request: schemas.CompleteTeacherProfileRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    return google_service.complete_google_teacher_registration(db, request, response)