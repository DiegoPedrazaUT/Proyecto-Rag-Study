import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from uuid import UUID

# ==========================================
# 1. ESQUEMAS DE REGISTRO
# ==========================================

PASSWORD_REGEX = r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$"
PASSWORD_ERROR_MSG = 'La contraseña debe incluir al menos 12 caracteres, una mayúscula, un número y un símbolo especial.'

class UserRegisterBase(BaseModel):
    first_name: str = Field(..., min_length=2, description="Primer nombre del usuario")
    last_name: str = Field(..., min_length=2, description="Apellidos del usuario")
    email: EmailStr = Field(..., description="Correo electronico valido")
    password: str = Field(..., min_length=12, description="Contraseña segura")
    career_id: int = Field(..., gt=0, description="ID de la carrera o departamento")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.match(PASSWORD_REGEX, v):
            raise ValueError(PASSWORD_ERROR_MSG)
        return v

class StudentRegisterRequest(UserRegisterBase):
    matricula: str = Field(..., min_length=8, description="Matrícula escolar única")

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "Diego Angel",
                "last_name": "Ramirez Fernandez",
                "email": "23393190@utcancun.edu.mx",
                "password": "PasswordSegura2026!*",
                "career_id": 1,
                "matricula": "23393190"
            }
        }
    }

class TeacherRegisterRequest(UserRegisterBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "Juan",
                "last_name": "Pérez",
                "email": "jperez@utcancun.edu.mx",
                "password": "PasswordSegura2026!*",
                "career_id": 1
            }
        }
    }

# ==========================================
# 2. ESQUEMAS DE LOGIN Y MFA
# ==========================================

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = Field(None, description="Código de 6 dígitos de Google Authenticator si el MFA está activo")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "23393190@utcancun.edu.mx",
                "password": "PasswordSegura2026!*",
                "mfa_code": "123456"
            }
        }
    }

# ==========================================
# 3. ESQUEMAS DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    
    model_config = {
        "json_schema_extra": {
            "example": {"email": "23393190@utcancun.edu.mx"}
        }
    }

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.match(PASSWORD_REGEX, v):
            raise ValueError(PASSWORD_ERROR_MSG)
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Contraseña actual del usuario")
    new_password: str = Field(..., min_length=12, description="Nueva contraseña segura")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.match(PASSWORD_REGEX, v):
            raise ValueError(PASSWORD_ERROR_MSG)
        return v

class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Correo del usuario que necesita el link")

# ==========================================
# 4. ESQUEMAS DE RESPUESTA (OUTPUTS)
# ==========================================

class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool
    is_mfa_enabled: bool

    model_config = {"from_attributes": True}

class UserResponseBase(BaseModel):
    id: UUID = Field(..., description="ID único del usuario")
    first_name: str = Field(..., description="Primer nombre")
    last_name: str = Field(..., description="Apellidos")
    email: EmailStr = Field(..., description="Correo electrónico")
    role: str = Field(..., description="Rol del usuario (student, teacher, admin)")
    is_verified: bool = Field(..., description="Estado de verificación del correo")
    is_mfa_enabled: bool = Field(..., description="Estado de seguridad MFA")

    class Config:
        from_attributes = True

    @field_validator('role', mode='before')
    @classmethod
    def get_role_name(cls, v):
        if hasattr(v, 'role_name'):
            return v.role_name
        return v

class UserUpdatePartial(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, description="Nuevo nombre")
    last_name: Optional[str] = Field(None, min_length=2, description="Nuevos apellidos")

class AdminUserUpdatePartial(UserUpdatePartial):
    career_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de la carrera/departamento")

class UserUpdateComplete(BaseModel):
    first_name: str = Field(..., min_length=2, description="Nombre completo requerido")
    last_name: str = Field(..., min_length=2, description="Apellidos requeridos")

class AdminUserUpdateComplete(UserUpdateComplete):
    career_id: int = Field(..., gt=0, description="ID de la carrera requerido")
    
class PaginatedUserResponse(BaseModel):
    total_count: int = Field(..., description="Total de usuarios encontrados")
    users: List[UserResponseBase] = Field(..., description="Lista de usuarios")
    
class GoogleCompleteProfileRequest(BaseModel):
    temp_token: str = Field(..., description="Token de seguridad encriptado entregado por el callback de Google")
    career_id: int = Field(..., gt=0, description="ID de la carrera seleccionada")
    matricula: str = Field(..., min_length=8, description="Matrícula escolar única")