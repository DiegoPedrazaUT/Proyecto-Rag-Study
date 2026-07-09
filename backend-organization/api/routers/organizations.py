from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import List
from sqlalchemy.orm import Session
from core.config import settings
from database.database import get_db
from core.security import get_current_user
from api import schemas, docs # <-- ¡Importamos nuestro nuevo archivo docs!
from repositories.organization_repository import OrganizationRepository
from services.organization_service import create_organization, get_my_organizations, update_organization_details, delete_organization_service
from services.member_service import join_organization, update_member_status, get_organization_members, get_waitlist_members
from services.invite_service import InviteService

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.post("/", response_model=schemas.OrganizationResponse, **docs.CREATE_ORG)
def create_org(org_data: schemas.OrganizationCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return create_organization(db, org_data, current_user)

@router.get("/me", response_model=List[schemas.OrganizationResponse], **docs.GET_MY_ORGS)
def get_my_orgs(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return get_my_organizations(db, current_user)

@router.get("/{org_id}/members", response_model=List[schemas.MemberWithUserResponse], **docs.GET_MEMBERS)
def get_members(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return get_organization_members(db, org_id, current_user)

@router.get("/{org_id}/waitlist", response_model=List[schemas.MemberWithUserResponse], **docs.GET_WAITLIST)
def get_waitlist(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return get_waitlist_members(db, org_id, current_user)

@router.post("/join", **docs.JOIN_ORG)
def join_by_code(join_data: schemas.JoinRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return join_organization(db, join_data.code, current_user)

@router.get("/{org_id}/qr", **docs.GET_QR)
def get_organization_qr(org_id: str, db: Session = Depends(get_db)):
    org = OrganizationRepository.get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
    
    invite_link = f"{settings.FRONTEND_URL}/join?code={org.join_code}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={invite_link}"
    return {"qr_image_url": qr_url, "join_code": org.join_code}

@router.get("/join", include_in_schema=False) 
def join_via_email_link(code: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """(Este endpoint lo ocultamos de Swagger con include_in_schema=False porque devuelve HTML visual)"""
    try:
        join_organization(db, code, current_user)
        return HTMLResponse(content="<h1>¡Solicitud Enviada!</h1><p>Estado: Pending</p>")
    except HTTPException as e:
        return HTMLResponse(content=f"<h1>Error</h1><p>{e.detail}</p>", status_code=e.status_code)

@router.patch("/{org_id}/members/{student_id}", response_model=schemas.MemberResponse, **docs.PATCH_MEMBER_STATUS)
def change_member_status(org_id: str, student_id: str, status_data: schemas.MemberStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return update_member_status(db, org_id, student_id, status_data.status, current_user) # type: ignore

@router.post("/{org_id}/invite", **docs.SEND_INVITE)
def invite_by_email(org_id: str, invite: schemas.InviteCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return InviteService.send_invitation(db, org_id, invite.email, current_user.get("sub"))

@router.get("/{org_id}/invites", response_model=List[schemas.InviteResponse], **docs.GET_INVITES)
def get_invites(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return InviteService.get_organization_invites(db, org_id, current_user)

@router.patch("/{org_id}", response_model=schemas.OrganizationResponse, **docs.UPDATE_ORG)
def update_org(org_id: str, update_data: schemas.OrganizationUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return update_organization_details(db, org_id, update_data, current_user)

@router.delete("/{org_id}", **docs.DELETE_ORG)
def delete_org(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return delete_organization_service(db, org_id, current_user)