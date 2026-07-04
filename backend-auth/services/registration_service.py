import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, BackgroundTasks
from api import schemas
from core.security import get_password_hash, verify_token
from core.email import send_verification_email
from repositories.user_repository import UserRepository
from database.models import Role, Career, User, StudentProfile, TeacherProfile

def register_student(db: Session, user_data: schemas.StudentRegisterRequest, background_tasks: BackgroundTasks):
    if UserRepository.get_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    student_role = db.query(Role).filter(Role.role_name == "student").first()
    career = db.query(Career).filter(Career.career_id == user_data.career_id).first()
    
    if not student_role:
        raise HTTPException(status_code=500, detail="El rol 'student' no existe en la BD")
    if not career:
        raise HTTPException(status_code=400, detail="La carrera especificada no existe")

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    base_user_data = {
        "role_id": student_role.role_id,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "is_verified": False,
        "verification_token": token,
        "verification_token_expires": expires
    }

    profile_data = {
        "matricula": user_data.matricula,
        "career_id": user_data.career_id
    }

    try:
        new_user = UserRepository.create_student(db, base_user_data, profile_data)
        background_tasks.add_task(send_verification_email, to_email=new_user.email, token=token) # type: ignore
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo o la matrícula ya se encuentran registrados.")
    except Exception as e:
        db.rollback()
        # Nunca devolver str(e) al cliente en producción
        raise HTTPException(status_code=500, detail="Error interno del servidor al crear el usuario.")

def register_teacher(db: Session, user_data: schemas.TeacherRegisterRequest, background_tasks: BackgroundTasks):
    if UserRepository.get_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    teacher_role = db.query(Role).filter(Role.role_name == "teacher").first()
    career = db.query(Career).filter(Career.career_id == user_data.career_id).first()
    
    if not teacher_role:
        raise HTTPException(status_code=500, detail="El rol 'teacher' no existe en la BD")
    if not career:
        raise HTTPException(status_code=400, detail="La carrera/departamento especificado no existe")

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    base_user_data = {
        "role_id": teacher_role.role_id,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "is_verified": False,
        "verification_token": token,
        "verification_token_expires": expires
    }

    profile_data = {
        "career_id": user_data.career_id
    }

    try:
        new_user = UserRepository.create_student(db, base_user_data, profile_data)
        background_tasks.add_task(send_verification_email, to_email=new_user.email, token=token) # type: ignore
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo o la matrícula ya se encuentran registrados.")
    except Exception as e:
        db.rollback()
        # Nunca devolver str(e) al cliente en producción
        raise HTTPException(status_code=500, detail="Error interno del servidor al crear el usuario.")
    
def complete_student_profile(db: Session, request: schemas.CompleteStudentProfileRequest):
    email = verify_token(request.temp_token)
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # 1. Verificar si el rol existe antes de acceder a .role_id
    role = db.query(Role).filter(Role.role_name == "student").first()
    if not role:
        raise HTTPException(status_code=500, detail="El rol 'student' no está configurado en la BD")
        
    # 2. Crear perfil
    new_profile = StudentProfile(
        user_id=user.id,
        matricula=request.matricula,
        career_id=request.career_id
    )
    db.add(new_profile)
    
    # 3. Asignar rol
    user.role_id = role.role_id
    db.commit()
    return {"message": "Perfil de estudiante completado exitosamente"}

def complete_teacher_profile(db: Session, request: schemas.CompleteTeacherProfileRequest):
    email = verify_token(request.temp_token)
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    role = db.query(Role).filter(Role.role_name == "teacher").first()
    if not role:
        raise HTTPException(status_code=500, detail="El rol 'teacher' no está configurado en la BD")
        
    new_profile = TeacherProfile(
        user_id=user.id,
        career_id=request.career_id
    )
    db.add(new_profile)
    
    user.role_id = role.role_id
    db.commit()
    return {"message": "Perfil de profesor completado exitosamente"}