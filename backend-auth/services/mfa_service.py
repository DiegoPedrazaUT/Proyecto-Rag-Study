from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import cast
from core.security import generate_mfa_secret, get_mfa_uri, verify_mfa_code
from repositories.user_repository import UserRepository

def setup_mfa(db: Session, user_id: str):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user.is_mfa_enabled: # type: ignore
        raise HTTPException(status_code=400, detail="El MFA ya está activo en esta cuenta.")
    
    secret = generate_mfa_secret()
    user.mfa_secret = secret # type: ignore
    UserRepository.update(db)
    
    return {"mfa_uri": get_mfa_uri(cast(str, user.email), secret), "secret_helper": secret}

def confirm_mfa(db: Session, user_id: str, code: str):
    user = UserRepository.get_by_id(db, user_id)
    if not user or not user.mfa_secret: # type: ignore
        raise HTTPException(status_code=400, detail="MFA no está configurado para este usuario")
    
    if verify_mfa_code(cast(str, user.mfa_secret), code):
        user.is_mfa_enabled = True # type: ignore
        UserRepository.update(db)
        return {"message": "MFA activado exitosamente"}
    
    raise HTTPException(status_code=401, detail="Código inválido")