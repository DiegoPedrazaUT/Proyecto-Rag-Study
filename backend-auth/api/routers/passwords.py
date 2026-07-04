from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User
from api import schemas
from services import password_service
from api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Contraseñas y Correos"])

@router.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return password_service.process_forgot_password(db, request, background_tasks)

@router.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    return password_service.process_reset_password(db, request)

@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    mensaje = password_service.verify_user_email(db, token)
    html_content = f"""
    <html>
        <head><title>Verificación Exitosa</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
            <h2 style="color: #4CAF50;">✅ ¡Verificación Completada!</h2>
            <p>{mensaje}</p>
        </body>
    </html>
    """
    return html_content

@router.post("/resend-verification")
def resend_verification_email(request: schemas.ResendVerificationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return password_service.resend_verification(db, request.email, background_tasks)

@router.post("/change-password")
def change_password(
    request: schemas.ChangePasswordRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    return password_service.change_user_password(db, str(current_user.id), request)