from typing import Optional, Union
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api import schemas
from repositories.user_repository import UserRepository
from database.models import Career


def get_all_users(
    db: Session,
    role: Optional[str] = None,
    career_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
):
    total, users = UserRepository.get_all_filtered(
        db,
        role_name=role,
        career_id=career_id,
        skip=skip,
        limit=limit
    )
    return {"total_count": total, "users": users}


def get_user_by_id(db: Session, user_id: str):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def _validate_career_exists(db: Session, career_id: int):
    career = db.query(Career).filter(Career.career_id == career_id).first()
    if not career:
        raise HTTPException(status_code=400, detail="La carrera/departamento especificado no existe")


def _update_user_career(db: Session, user, career_id: int):
    _validate_career_exists(db, career_id)

    role_name = user.role.role_name

    if role_name == "student":
        if not user.student_profile:
            raise HTTPException(status_code=400, detail="El usuario no tiene perfil de estudiante")
        user.student_profile.career_id = career_id

    elif role_name == "teacher":
        if not user.teacher_profile:
            raise HTTPException(status_code=400, detail="El usuario no tiene perfil de profesor")
        user.teacher_profile.career_id = career_id

    else:
        raise HTTPException(status_code=400, detail="Este rol no tiene carrera/departamento editable")


def update_user_partial(
    db: Session,
    user_id: str,
    update_data: Union[schemas.UserUpdatePartial, schemas.AdminUserUpdatePartial]
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        if key == "career_id":
            _update_user_career(db, user, value)
        else:
            setattr(user, key, value)

    UserRepository.update(db)
    return user


def update_user_complete(
    db: Session,
    user_id: str,
    update_data: Union[schemas.UserUpdateComplete, schemas.AdminUserUpdateComplete]
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.first_name = update_data.first_name # type: ignore
    user.last_name = update_data.last_name # type: ignore

    career_id = getattr(update_data, "career_id", None)

    if career_id is not None:
        _update_user_career(db, user, career_id)

    UserRepository.update(db)
    return user


def delete_user_account(db: Session, user_id: str):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    UserRepository.delete_user(db, user)
    return {"message": "Usuario eliminado exitosamente del sistema"}