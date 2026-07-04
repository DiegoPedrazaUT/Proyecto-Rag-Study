from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import List
from core.config import settings
from sqlalchemy.orm import Session
from database.database import get_db
from core.security import get_current_user
from repositories.organization_repository import OrganizationRepository
from services.organization_service import create_organization, get_my_organizations, update_organization_details, delete_organization_service
from services.member_service import join_organization, update_member_status, get_organization_members
from services.invite_service import InviteService
from api import schemas

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.post("/createOrg", response_model=schemas.OrganizationResponse)
def create_org(org_data: schemas.OrganizationCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return create_organization(db, org_data, current_user)

@router.get("/me", response_model=List[schemas.OrganizationResponse])
def get_my_orgs(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return get_my_organizations(db, current_user)

@router.get("/{org_id}/members", response_model=List[schemas.MemberWithUserResponse])
def get_members(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return get_organization_members(db, org_id, current_user)

@router.post("/join")
def join_by_code(join_data: schemas.JoinRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return join_organization(db, join_data.code, current_user)

@router.get("/{org_id}/qr")
def get_organization_qr(org_id: str, db: Session = Depends(get_db)):
    """Devuelve la URL directa de la imagen del QR para que el front la renderice"""
    # 1. Buscamos el salón para sacar su código
    org = OrganizationRepository.get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
    
    # 2. Armamos el link del front y pedimos la imagen a la API de QR
    invite_link = f"{settings.FRONTEND_URL}/join?code={org.join_code}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={invite_link}"
    
    return {"qr_image_url": qr_url, "join_code": org.join_code}

@router.get("/join")
def join_via_email_link(code: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Ruta GET visual para probar los clics desde el correo"""
    try:
        # Reutilizamos tu lógica exacta del servicio
        join_organization(db, code, current_user)
        
        # Si todo sale bien, devolvemos esta vista verde
        return HTMLResponse(content="""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f4f6f9; height: 100vh;">
                <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: auto;">
                    <h1 style="color: #2ecc71;">¡Solicitud Enviada! 🚀</h1>
                    <p style="font-size: 1.2em; color: #333;">Te has unido a la clase exitosamente.</p>
                    <div style="background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; margin-top: 20px;">
                        <strong>Estado: En Lista de Espera (Pending)</strong>
                    </div>
                    <p style="color: #666; margin-top: 20px;">El profesor debe aceptar tu solicitud para que ingreses oficialmente.</p>
                </div>
            </div>
        """)
    except HTTPException as e:
        # Si algo falla (ej. el alumno ya estaba en la clase o es de otra carrera), mostramos esta vista roja
        return HTMLResponse(content=f"""
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f4f6f9; height: 100vh;">
                <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: auto;">
                    <h1 style="color: #e74c3c;">Oops... Algo salió mal 🛑</h1>
                    <p style="font-size: 1.2em; color: #333;">{e.detail}</p>
                </div>
            </div>
        """, status_code=e.status_code)

@router.patch("/{org_id}/members/{student_id}", response_model=schemas.MemberResponse)
def change_member_status(org_id: str, student_id: str, status_data: schemas.MemberStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return update_member_status(db, org_id, student_id, status_data.status, current_user) # type: ignore

@router.post("/{org_id}/invite")
def invite_by_email(org_id: str, invite: schemas.InviteCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return InviteService.send_invitation(db, org_id, invite.email, current_user.get("sub"))

# ¡NUEVO! Ruta para ver el historial de correos enviados
@router.get("/{org_id}/invites", response_model=List[schemas.InviteResponse])
def get_invites(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """El profe usa este endpoint para ver a qué correos ha enviado invitaciones"""
    return InviteService.get_organization_invites(db, org_id, current_user)

@router.patch("/{org_id}", response_model=schemas.OrganizationResponse)
def update_org(org_id: str, update_data: schemas.OrganizationUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """El profesor edita los detalles de su salón (nombre, descripción o asignatura)"""
    return update_organization_details(db, org_id, update_data, current_user)

@router.delete("/{org_id}")
def delete_org(org_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """El profesor elimina su salón de clases (esto borra a los miembros en cascada)"""
    return delete_organization_service(db, org_id, current_user)