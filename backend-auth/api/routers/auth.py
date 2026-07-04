from fastapi import APIRouter, Depends, Response, Cookie, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database.database import get_db
from api import schemas
from services import session_service, google_service, registration_service
from core.security import verify_refresh_token, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación y Sesión"])

@router.post("/login")
def login(login_data: schemas.UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    return session_service.authenticate_user(db, login_data, response)

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token", secure=True, httponly=True, samesite="none")
    response.delete_cookie(key="refresh_token", secure=True, httponly=True, samesite="none")
    return {"message": "Sesión cerrada exitosamente"}

@router.post("/refresh")
def refresh_token(response: Response, refresh_token: str | None = Cookie(None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No hay Refresh Token en las cookies")
        
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
        
    new_access_token = create_access_token({"sub": payload.get("sub"), "role": payload.get("role")})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True, secure=True, samesite="none", max_age=15 * 60
    )
    return {"message": "Token renovado exitosamente"}

@router.get("/google")
def login_with_google():
    """Redirige al usuario a la pantalla de consentimiento de Google."""
    url = google_service.get_google_auth_url()
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str, response: Response, db: Session = Depends(get_db)):
    """Recibe el código de Google y devuelve JWT o un 202 con Token Temporal."""
    try:
        google_user = await google_service.get_google_user_info(code)
        result = google_service.process_google_login(db, google_user, response)
        
        if result.get("status") == "needs_completion":
            response.status_code = status.HTTP_202_ACCEPTED
            
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/complete-student")
def complete_student(request: schemas.CompleteStudentProfileRequest, db: Session = Depends(get_db)):
    return registration_service.complete_student_profile(db, request)

@router.post("/auth/complete-teacher")
def complete_teacher(request: schemas.CompleteTeacherProfileRequest, db: Session = Depends(get_db)):
    return registration_service.complete_teacher_profile(db, request)