from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import docs
from database.database import get_db
from database.models import User
from services import mfa_service
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth/mfa", tags=["Seguridad MFA"])


@router.post("/setup", **docs.MFA_SETUP)
def mfa_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return mfa_service.setup_mfa(db, str(current_user.id))


@router.post("/verify", **docs.MFA_VERIFY)
def mfa_verify(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return mfa_service.confirm_mfa(db, str(current_user.id), code)