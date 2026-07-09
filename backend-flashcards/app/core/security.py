import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass
class CurrentUser:
    """Identidad del request, resuelta directamente desde el token JWT."""

    id: uuid.UUID
    role: str
    username: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"

    @property
    def is_teacher(self) -> bool:
        return self.role.lower() == "teacher"

    @property
    def is_student(self) -> bool:
        return self.role.lower() == "student"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Decodifica el JWT y construye la identidad desde su contenido.

    El token (emitido por el servicio de Auth) trae el user_id en `sub`,
    el rol en `role` y el nombre en `username`. No se consulta la base de
    datos: se confía en la información firmada del token.
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise cred_exc

    subject = payload.get("sub")
    role = payload.get("role")
    if subject is None or role is None:
        raise cred_exc

    try:
        user_id = uuid.UUID(str(subject))
    except ValueError:
        raise cred_exc

    return CurrentUser(
        id=user_id,
        role=role,
        username=payload.get("username"),
    )