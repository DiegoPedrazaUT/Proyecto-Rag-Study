from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from repositories.organization_repository import OrganizationRepository
from database.models import TeacherProfile
from api import schemas

def create_organization(db: Session, org_data: schemas.OrganizationCreate, teacher_payload: dict):
    if teacher_payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden crear salones")
    
    teacher_id = UUID(teacher_payload.get("sub"))
    
    teacher_profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == teacher_id).first()
    if not teacher_profile:
        raise HTTPException(status_code=404, detail="Perfil de profesor no encontrado o incompleto")
    
    # El repositorio se encarga de generar el código y guardar en BD
    return OrganizationRepository.create_organization(db, org_data, teacher_id, teacher_profile.career_id) # type: ignore

def get_my_organizations(db: Session, current_user: dict):
    user_id = current_user.get("sub")
    role = current_user.get("role")
    
    if role == "teacher":
        return OrganizationRepository.get_teacher_organizations(db, user_id) # type: ignore
    elif role == "student":
        return OrganizationRepository.get_student_organizations(db, user_id) # type: ignore
    return []

def update_organization_details(db: Session, org_id: str, update_data: schemas.OrganizationUpdate, current_user: dict):
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden editar salones")
    
    org = OrganizationRepository.get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
        
    # Candado Anti-IDOR: ¿Es dueño de este salón?
    if str(org.created_by) != str(current_user.get("sub")):
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este salón")
        
    return OrganizationRepository.update_organization(db, org, update_data) # type: ignore


def delete_organization_service(db: Session, org_id: str, current_user: dict):
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden eliminar salones")
    
    org = OrganizationRepository.get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
        
    # Candado Anti-IDOR: ¿Es dueño de este salón?
    if str(org.created_by) != str(current_user.get("sub")):
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este salón")
        
    OrganizationRepository.delete_organization(db, org) # type: ignore
    return {"detail": "Salón eliminado exitosamente"}