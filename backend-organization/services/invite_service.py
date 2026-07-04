from sqlalchemy.orm import Session
from fastapi import HTTPException
from repositories.organization_repository import OrganizationRepository
from database.models import Organization 
from core.email import send_invite_email

class InviteService:
    @staticmethod
    def send_invitation(db: Session, org_id: str, email: str, invited_by_id: str):
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="El salón no existe")
            
        invite = OrganizationRepository.create_invite(db, org_id, email, invited_by_id) 
        send_invite_email(to_email=email, org_id=org_id, join_code=org.join_code) # type: ignore
        return invite

    # ¡NUEVO! Listar el historial de invitaciones
    @staticmethod
    def get_organization_invites(db: Session, org_id: str, current_user: dict):
        if current_user.get("role") != "teacher":
            raise HTTPException(status_code=403, detail="Solo el profesor puede ver las invitaciones enviadas")
            
        return OrganizationRepository.get_invites_by_org(db, org_id)