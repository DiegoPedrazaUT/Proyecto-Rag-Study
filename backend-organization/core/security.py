from fastapi import Request, HTTPException, Security
from jose import jwt, JWTError
from pydantic_settings import BaseSettings

# Configuración básica para este microservicio
class Settings(BaseSettings):
    SECRET_KEY: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings() # type: ignore

def get_current_user(request: Request):
    """
    Extrae el token de las cookies (producción) o del header Authorization (pruebas Swagger).
    Solo verifica que el token sea válido; no hace consultas a la base de datos.
    """
    token = request.cookies.get("access_token")
    
    # Respaldo por si mandan el token por Header en lugar de Cookie
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            raise HTTPException(status_code=401, detail="No estás autenticado")
            
    try:
        # Decodificamos el token usando la misma SECRET_KEY del servicio de Auth
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        user_id: str = payload.get("sub") # type: ignore
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido o corrupto")
            
        # Devolvemos el payload completo (que incluye 'role' y 'sub') para usarlo en los servicios
        return payload
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Tu sesión ha expirado o el token es inválido")