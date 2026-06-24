from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database.database import get_db
from database.models import User
from core.config import settings
from repositories.user_repository import UserRepository

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # 1. Extraer el token de la cookie
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado. Falla el token en la cookie.")
    
    # Limpiamos el prefijo 'Bearer ' si existe
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    # 2. Decodificar el token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

    # 3. Buscar al usuario en la BD
    user = UserRepository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    return user