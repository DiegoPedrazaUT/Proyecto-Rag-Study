from typing import Optional
from fastapi import APIRouter, Depends, status, BackgroundTasks, Query, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User
from api import schemas, docs
from services import registration_service, user_management_service

# Importamos la dependencia de seguridad
from api.dependencies import get_current_user

router = APIRouter(tags=["Gestión de Usuarios"])

# ==========================================
# 1. REGISTRO DE USUARIOS
# ==========================================
@router.post("/auth/register/student", status_code=status.HTTP_201_CREATED, **docs.REGISTER_STUDENT)
def register_student(data: schemas.StudentRegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return registration_service.register_student(db, data, background_tasks)

@router.post("/auth/register/teacher", status_code=status.HTTP_201_CREATED, **docs.REGISTER_TEACHER)
def register_teacher(data: schemas.TeacherRegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return registration_service.register_teacher(db, data, background_tasks)

# ==========================================
# 2. DIRECTORIO GENERAL
# ==========================================
@router.get("/users", response_model=schemas.PaginatedUserResponse, **docs.GET_USERS)
def get_users(
    role: Optional[str] = Query(None, description="Filtrar por rol (ej. student, teacher)"),
    career_id: Optional[int] = Query(None, description="Filtrar por ID de carrera"),
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(100, le=100, description="Límite de registros a devolver"),
    db: Session = Depends(get_db)
):
    return user_management_service.get_all_users(db, role=role, career_id=career_id, skip=skip, limit=limit)

# ==========================================
# 3. RUTAS ESTÁTICAS (DEL PROPIO USUARIO) -> ¡SIEMPRE ARRIBA!
# ==========================================
@router.get("/users/me", response_model=schemas.UserResponseBase, **docs.GET_ME)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/users/me", response_model=schemas.UserResponseBase, **docs.PATCH_ME)
def update_my_profile_partial(
    update_data: schemas.UserUpdatePartial, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return user_management_service.update_user_partial(db, str(current_user.id), update_data)

@router.put("/users/me", response_model=schemas.UserResponseBase, **docs.PUT_ME)
def update_my_profile_complete(
    update_data: schemas.UserUpdateComplete, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return user_management_service.update_user_complete(db, str(current_user.id), update_data)

# ==========================================
# 4. RUTAS DINÁMICAS (/{user_id}) -> EXCLUSIVAS DE ADMIN
# ==========================================
@router.get("/users/{user_id}", response_model=schemas.UserResponseBase, **docs.GET_USER_ID)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return user_management_service.get_user_by_id(db, user_id)

@router.patch("/users/{user_id}", response_model=schemas.UserResponseBase, **docs.PATCH_USER_ADMIN)
def admin_update_user_partial(
    user_id: str, 
    update_data: schemas.AdminUserUpdatePartial, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requieren permisos de administrador.")
    return user_management_service.update_user_partial(db, user_id, update_data)

@router.put("/users/{user_id}", response_model=schemas.UserResponseBase)
def admin_update_user_complete(
    user_id: str, 
    update_data: schemas.AdminUserUpdateComplete, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requieren permisos de administrador.")
    return user_management_service.update_user_complete(db, user_id, update_data)

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requieren permisos de administrador.")
    return user_management_service.delete_user_account(db, user_id)