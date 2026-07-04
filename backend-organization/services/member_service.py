# backend-org/services/member_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from repositories.organization_repository import OrganizationRepository, MemberRepository
from database.models import Organization, StudentProfile, User  # <-- ¡Asegúrate de importar Organization aquí!
from uuid import UUID

def join_organization(db: Session, join_code: str, student_payload: dict):
    if student_payload.get("role") != "student":
        raise HTTPException(status_code=403, detail="Solo los estudiantes pueden unirse a salones usando código")
        
    student_id = UUID(student_payload.get("sub"))
    
    org = OrganizationRepository.get_org_by_code(db, join_code)
    if not org:
        raise HTTPException(status_code=404, detail="Código de invitación inválido o el salón ya no existe")
        
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == student_id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Perfil de estudiante no encontrado")
        
    if student_profile.career_id != org.career_id: # type: ignore
        raise HTTPException(status_code=403, detail="No perteneces al departamento/carrera de este salón de clases")
        
    return MemberRepository.add_to_waitlist(db, str(org.id), str(student_id))


# =====================================================================
# ¡NUEVA FUNCIÓN COMPLETAMENTE ACTUALIZADA Y BLINDADA!
# =====================================================================
def update_member_status(db: Session, org_id: str, student_id: str, new_status: str, current_user: dict):
    """
    Cambia el estatus de un alumno (accepted/rejected) en la lista de espera.
    Incluye parche de seguridad contra IDOR y validaciones robustas de existencia.
    """
    # 1. Candado de Rol: Validar que quien ejecuta la acción sea profesor según su JWT
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden aceptar o rechazar alumnos")
    
    # 2. Candado de Existencia de Clase: Buscamos si el salón realmente existe
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="El salón de clases especificado no existe")
    
    # 3. PARCHE CRÍTICO (Anti-IDOR): Validar que el profesor que ejecuta sea el DUEÑO real de este salón
    teacher_id = current_user.get("sub")
    if str(org.created_by) != str(teacher_id):
        raise HTTPException(status_code=403, detail="Acceso denegado. No eres el creador/dueño de este salón de clases")
    
    # 4. Acción en Base de Datos: Intentamos hacer el UPDATE del estatus del alumno
    updated_member = MemberRepository.update_status(db, org_id, student_id, new_status)
    if not updated_member:
        raise HTTPException(status_code=404, detail="Alumno no encontrado en lista de espera")
        
    # ¡NUEVO! Actualizar la tabla de historial de invitaciones
    user = db.query(User).filter(User.id == student_id).first()
    if user:
        MemberRepository.update_invite_status_by_email(db, org_id, user.email, new_status) # type: ignore
    
    # 5. Candado de Alumno: Si el repositorio devuelve None, significa que ese alumno no está en la lista de espera de esta clase
    if not updated_member:
        raise HTTPException(status_code=404, detail="Alumno no encontrado en la lista de espera de este salón")
        
    return updated_member


def get_organization_members(db: Session, org_id: str, current_user: dict):
    """Retorna SOLO a los miembros aceptados (El Directorio del Salón)"""
    members = MemberRepository.get_members_by_status(db, org_id, "accepted")
    
    return [{
        "organization_id": m.organization_id,
        "user_id": m.user_id,
        "role": m.role,
        "status": m.status,
        "joined_at": m.joined_at,
        "first_name": m.first_name,
        "last_name": m.last_name,
        "email": m.email
    } for m in members]

def get_waitlist_members(db: Session, org_id: str, current_user: dict):
    """Retorna SOLO a los miembros pendientes (Blindado Anti-IDOR para el Profe)"""
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Solo los profesores ven la lista de espera")
        
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or str(org.created_by) != str(current_user.get("sub")):
        raise HTTPException(status_code=403, detail="Acceso denegado. No eres el dueño del salón")

    members = MemberRepository.get_members_by_status(db, org_id, "pending")
    return [{
        "organization_id": m.organization_id,
        "user_id": m.user_id,
        "role": m.role,
        "status": m.status,
        "joined_at": m.joined_at,
        "first_name": m.first_name,
        "last_name": m.last_name,
        "email": m.email
    } for m in members]