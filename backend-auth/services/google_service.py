import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import jwt
from core.config import settings
from core.security import create_access_token, create_refresh_token
from repositories.user_repository import UserRepository
from database.models import Role
from fastapi import Response

# URLs oficiales de Google OAuth2
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

def get_google_auth_url() -> str:
    return (
        f"{GOOGLE_AUTH_URL}?client_id={settings.GOOGLE_CLIENT_ID}&"
        f"response_type=code&redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"scope=openid%20email%20profile&access_type=offline&prompt=consent"
    )

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
        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error al obtener la información de Google")

        return user_response.json()

def process_google_login(db: Session, google_user: dict, response: Response):
    email = google_user.get("email")
    user = UserRepository.get_by_email(db, email) # type: ignore
    
    if user:
        # ESCENARIO A: El usuario ya existe
        if not user.google_id: # type: ignore
            user.google_id = google_user.get("id") # type: ignore
            user.is_verified = True # type: ignore
            UserRepository.update(db)
            
        token_data = {"sub": str(user.id), "role": str(user.role.role_name)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, secure=True, samesite="none", max_age=15 * 60)
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=7 * 24 * 60 * 60)
        
        return {"status": "success", "message": "Login exitoso con Google", "user_name": f"{user.first_name} {user.last_name}"}
    
    else:
        # ESCENARIO B: Usuario nuevo (Token Temporal de Seguridad)
        temp_payload = {
            "email": email,
            "first_name": google_user.get("given_name", ""),
            "last_name": google_user.get("family_name", ""),
            "google_id": google_user.get("id"),
            "type": "google_temp" # Filtro de seguridad
        }
        # Encriptamos la información
        temp_token = jwt.encode(temp_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "status": "needs_completion",
            "message": "Google enlazado. Envía tu matrícula y carrera para completar el registro.",
            "temp_token": temp_token, # El Front debe guardar este token y mandarlo en el siguiente paso
            "temp_info": {"first_name": temp_payload["first_name"], "email": email}
        }

def complete_google_registration(db: Session, request_data, response: Response):
    # 1. Desencriptamos el token confiable
    try:
        payload = jwt.decode(request_data.temp_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "google_temp":
            raise HTTPException(status_code=400, detail="Token temporal inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="El token temporal expiró o fue alterado")

    # 2. Revisar que nadie más haya tomado el correo en los últimos 5 minutos
    if UserRepository.get_by_email(db, payload["email"]):
        raise HTTPException(status_code=400, detail="El correo ya fue registrado. Intenta iniciar sesión.")

    # 3. Preparar la Inserción
    student_role = db.query(Role).filter(Role.role_name == "student").first()
    if not student_role:
        raise HTTPException(status_code=500, detail="Error en BD: Rol 'student' no existe")

    base_user_data = {
        "role_id": student_role.role_id,
        "first_name": payload["first_name"],
        "last_name": payload["last_name"],
        "email": payload["email"],
        "password_hash": None, # Google users no tienen contraseña en BD
        "google_id": payload["google_id"],
        "is_verified": True # Google ya verificó este correo
    }

    profile_data = {
        "matricula": request_data.matricula,
        "career_id": request_data.career_id
    }

    # 4. Inserción con Transacción Segura
    try:
        new_user = UserRepository.create_student(db, base_user_data, profile_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="La matrícula ya se encuentra registrada por otro alumno.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al guardar el perfil.")

    # 5. Generar Sesión Oficial
    token_data = {"sub": str(new_user.id), "role": "student"}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, secure=True, samesite="none", max_age=15 * 60)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=7 * 24 * 60 * 60)
    
    return {"message": "Registro completado con éxito. Sesión iniciada."}