from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database.database import get_db
from database.models import User
from core.config import settings
from repositories.user_repository import UserRepository

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="No autenticado. Falla el token en la cookie.")

    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido para esta operación")

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

    user = UserRepository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user