from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError # ¡Librería real activada!
from app.core.config import settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Guardián de Seguridad: Extrae el JWT de Boston, lo valida y devuelve los datos.
    """
    token = credentials.credentials
    try:
        # 1. Desencripta el token usando la misma llave secreta del microservicio de Auth
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # 2. Extraemos los datos basándonos EXACTAMENTE en el payload de Boston
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        user_name: str = payload.get("username", "Estudiante")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="El token no contiene un identificador válido"
            )
        # 3. Devolvemos el formato que tus endpoints de RAG ya esperan
        return {
            "user_id": user_id,
            "role": role,
            "user_name": user_name
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas, token alterado o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )