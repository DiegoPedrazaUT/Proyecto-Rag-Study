import random
import string
from sqlalchemy.orm import Session
from database.models import Organization, OrganizationMember, OrganizationInvite, User
from api import schemas
from uuid import UUID

def generate_join_code(length=8):
    prefix = "CLASS-"
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}{chars}"

class OrganizationRepository:
    @staticmethod
    def create_organization(db: Session, org_data: schemas.OrganizationCreate, teacher_id: UUID, career_id: int):
        # 1. Crear la Organización
        code = generate_join_code()
        new_org = Organization(
            name=org_data.name,
            subject=org_data.subject,
            description=org_data.description,
            career_id=career_id,
            created_by=teacher_id,
            join_code=code
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        
        # 2. ¡NUEVO! Agregar al profesor como administrador de su propia clase
        new_member = OrganizationMember(
            organization_id=new_org.id,
            user_id=teacher_id,
            role="teacher",
            status="accepted" # Entra directamente sin esperar
        )
        db.add(new_member)
        db.commit()
        
        return new_org
    
    @staticmethod
    def update_organization(db: Session, org: Organization, update_data: schemas.OrganizationUpdate):
        # Convertimos el esquema a diccionario, ignorando los campos que el usuario no envió
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(org, key, value)
        
        db.commit()
        db.refresh(org)
        return org

    @staticmethod
    def delete_organization(db: Session, org: Organization):
        db.delete(org)
        db.commit()
        return True

    @staticmethod
    def get_teacher_organizations(db: Session, teacher_id: str):
        return db.query(Organization).filter(Organization.created_by == teacher_id).all()

    @staticmethod
    def get_student_organizations(db: Session, student_id: str):
        return db.query(Organization).join(OrganizationMember).filter(
            OrganizationMember.user_id == student_id,
            OrganizationMember.status == "accepted"
        ).all()

    @staticmethod
    def get_org_by_code(db: Session, join_code: str):
        return db.query(Organization).filter(Organization.join_code == join_code).first()

    @staticmethod
    def create_invite(db: Session, org_id: str, email: str, invited_by_id: str):
        new_invite = OrganizationInvite(
            organization_id=org_id,
            email=email,
            invited_by=invited_by_id
        )
        db.add(new_invite)
        db.commit()
        db.refresh(new_invite)
        return new_invite

    # ¡NUEVO! Función para que el profe vea a quién ha invitado por correo
    @staticmethod
    def get_invites_by_org(db: Session, org_id: str):
        return db.query(OrganizationInvite).filter(OrganizationInvite.organization_id == org_id).all()
    
    @staticmethod
    def get_org_by_id(db: Session, org_id: str):
        """Busca una organización por su UUID"""
        return db.query(Organization).filter(Organization.id == org_id).first()

class MemberRepository:
    @staticmethod
    def add_to_waitlist(db: Session, org_id: str, student_id: str):
        new_member = OrganizationMember(organization_id=org_id, user_id=student_id)
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        return new_member

    @staticmethod
    def update_status(db: Session, org_id: str, student_id: str, new_status: str):
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == student_id
        ).first()
        if member:
            member.status = new_status # type: ignore
            db.commit()
            db.refresh(member)
        return member

    @staticmethod
    def get_members_with_users(db: Session, org_id: str):
        return db.query(
            OrganizationMember.organization_id,
            OrganizationMember.user_id,
            OrganizationMember.role,
            OrganizationMember.status,
            OrganizationMember.joined_at,
            User.first_name,
            User.last_name,
            User.email
        ).join(User, User.id == OrganizationMember.user_id)\
        .filter(OrganizationMember.organization_id == org_id).all()