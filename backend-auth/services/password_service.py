import secrets
from datetime import datetime, timedelta, timezone
from typing import cast, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from api.schemas import ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from core.security import get_password_hash, verify_password
from core.email import send_reset_password_email, send_verification_email
from repositories.user_repository import UserRepository

def process_forgot_password(db: Session, request: ForgotPasswordRequest, background_tasks):
    user = UserRepository.get_by_email(db, request.email)
    generic_message = "Si el correo está registrado, recibirás instrucciones para recuperar tu contraseña."
    
    if not user:
        return {"message": generic_message}

    token = secrets.token_urlsafe(32)
    user.reset_token = token # type: ignore
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=15) # type: ignore
    UserRepository.update(db)

    background_tasks.add_task(send_reset_password_email, to_email=cast(str, user.email), token=token)
    return {"message": generic_message}

def process_reset_password(db: Session, request: ResetPasswordRequest):
    user = UserRepository.get_by_reset_token(db, request.token)
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o no existe.")

    expires = cast(Optional[datetime], user.reset_token_expires)
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El token ha expirado. Solicita uno nuevo.")

    user.password_hash = get_password_hash(request.new_password) # type: ignore
    user.reset_token = None # type: ignore
    user.reset_token_expires = None # type: ignore
    user.failed_attempts = 0 # type: ignore
    user.lockout_until = None # type: ignore
    UserRepository.update(db)
    
    return {"message": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión."}

def change_user_password(db: Session, user_id: str, request: ChangePasswordRequest):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not verify_password(request.current_password, cast(str, user.password_hash)):
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta")

    user.password_hash = get_password_hash(request.new_password) # type: ignore
    UserRepository.update(db)
    return {"message": "Contraseña actualizada exitosamente"}

def verify_user_email(db: Session, token: str):
    user = UserRepository.get_by_verification_token(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o la cuenta ya fue verificada.")

    expires = cast(Optional[datetime], user.verification_token_expires)
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El enlace ha expirado. Por favor solicita uno nuevo.")

    user.is_verified = True # type: ignore
    user.verification_token = None # type: ignore
    user.verification_token_expires = None # type: ignore
    UserRepository.update(db)
    return "¡Cuenta verificada con éxito! Ya puedes cerrar esta ventana e iniciar sesión en la plataforma."

def resend_verification(db: Session, email: str, background_tasks):
    user = UserRepository.get_by_email(db, email)
    generic_msg = "Si el correo existe y no está verificado, se ha enviado un nuevo enlace."
    
    if not user:
        return {"message": generic_msg}

    is_verified = cast(bool, user.is_verified)
    if is_verified:
        raise HTTPException(status_code=400, detail="Esta cuenta ya está verificada.")

    token = secrets.token_urlsafe(32)
    user.verification_token = token # type: ignore
    user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24) # type: ignore
    UserRepository.update(db)

    background_tasks.add_task(send_verification_email, to_email=cast(str, user.email), token=token)
    return {"message": generic_msg}