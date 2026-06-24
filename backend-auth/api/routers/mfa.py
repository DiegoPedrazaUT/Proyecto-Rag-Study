from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from services import mfa_service

router = APIRouter(prefix="/auth/mfa", tags=["Seguridad MFA"])

@router.post("/setup")
def mfa_setup(user_id: str, db: Session = Depends(get_db)):
    return mfa_service.setup_mfa(db, user_id)

@router.post("/verify")
def mfa_verify(user_id: str, code: str, db: Session = Depends(get_db)):
    return mfa_service.confirm_mfa(db, user_id, code)