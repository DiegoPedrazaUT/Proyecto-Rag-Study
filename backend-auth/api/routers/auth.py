from fastapi import APIRouter, Depends, Response, Cookie, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from api import schemas
from services import session_service
from core.security import verify_refresh_token, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación y Sesión"])

@router.post("/login")
def login(login_data: schemas.UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    return session_service.authenticate_user(db, login_data, response)

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", secure=True, httponly=True, samesite="none")
    response.delete_cookie(key="refresh_token", secure=True, httponly=True, samesite="none")
    return {"message": "Sesión cerrada exitosamente"}

@router.post("/refresh")
def refresh_token(response: Response, refresh_token: str | None = Cookie(None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No hay Refresh Token en las cookies")
        
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
    new_access_token = create_access_token({"sub": payload.get("sub"), "role": payload.get("role")})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True, secure=True, samesite="none", max_age=15 * 60
    )
    return {"message": "Token renovado exitosamente"}