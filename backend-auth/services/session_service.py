from datetime import datetime, timedelta, timezone
from typing import cast, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, Response

from api.schemas import UserLoginRequest
from core.security import verify_password, create_access_token, create_refresh_token
from repositories.user_repository import UserRepository

def authenticate_user(db: Session, login_data: UserLoginRequest, response: Response):
    user = UserRepository.get_by_email(db, login_data.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    is_verified = cast(bool, user.is_verified)
    if not is_verified:
        raise HTTPException(status_code=403, detail="Debes verificar tu correo antes de iniciar sesión.")

    lockout = cast(Optional[datetime], user.lockout_until)
    if lockout and lockout > datetime.now(timezone.utc):
        tiempo_restante = (lockout - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(status_code=429, detail=f"Cuenta bloqueada. Intenta en {tiempo_restante} minutos.")

    if not verify_password(login_data.password, cast(str, user.password_hash)):
        current_attempts = cast(int, user.failed_attempts) + 1
        user.failed_attempts = current_attempts # type: ignore
        
        if current_attempts >= 5:
            user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15) # type: ignore
            UserRepository.update(db) 
            raise HTTPException(status_code=429, detail="Demasiados intentos. Bloqueado temporalmente.")
        
        UserRepository.update(db)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    is_mfa = cast(bool, user.is_mfa_enabled)
    if is_mfa:
        if not login_data.mfa_code:
            return {"mfa_required": True, "message": "Credenciales correctas. Ingrese su código MFA."}
        
        from core.security import verify_mfa_code
        if not verify_mfa_code(cast(str, user.mfa_secret), login_data.mfa_code):
            raise HTTPException(status_code=401, detail="Código MFA inválido o expirado.")

    user.failed_attempts = 0 # type: ignore
    user.lockout_until = None # type: ignore
    UserRepository.update(db)

    token_data = {"sub": str(user.id), "role": str(user.role.role_name), "username": f"{user.first_name} {user.last_name}"}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    response.set_cookie(
        key="access_token", value=f"Bearer {access_token}", httponly=True,
        secure=True, samesite="none", max_age=15 * 60
    )
    
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=True, samesite="none", max_age=7 * 24 * 60 * 60
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }