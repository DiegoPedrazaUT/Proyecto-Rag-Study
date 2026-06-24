from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
#from jose import jwt, JWTError
from app.core.config import settings

security = HTTPBearer()
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Versión falsa para pruebas locales. 
    NOTA: En el Swagger UI, aún tendrás que darle al botón verde "Authorize" 
    y escribir CUALQUIER texto (ej. "123") para que FastAPI te deje pasar.
    """
    return {
        "user_id": "b93f6db5-27a8-4527-ac9d-4a8a89915f09",
        "role": "student",
        "user_name": "Diego (Pruebas Locales)"
    }

# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     """
#     Esta función se ejecutará antes de que el chatbot responda.
#     Extrae el token, lo valida y devuelve los datos del usuario.
#     """
#     token = credentials.credentials
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
#         user_id: str = payload.get("sub")
#         role: str = payload.get("role")
#         user_name: str = payload.get("user_name", "Estudiante")
        
#         if user_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED, 
#                 detail="El token no contiene un identificador válido"
#             )
            
#         return {"user_id": user_id, "role": role, "user_name": user_name}
        
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Firma del token inválida o token expirado",
#             headers={"WWW-Authenticate": "Bearer"},
#         )