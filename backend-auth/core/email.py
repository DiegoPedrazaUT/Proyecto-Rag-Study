import json
import urllib.request
from core.config import settings 

def send_reset_password_email(to_email: str, token: str):
    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    
    data = {
        "sender": {"name": "Soporte UT Cancún", "email": "support@utextracurricular.com"},
        "to": [{"email": to_email}],
        "subject": "Recuperación de Contraseña - Sistema RAG",
        "htmlContent": f"""
        <h3>Hola,</h3>
        <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
        <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>Este enlace expirará en 15 minutos.</p>
        """
    }
    _send_brevo_request(data, to_email, "recuperación")

def send_verification_email(to_email: str, token: str):
    verify_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    
    data = {
        "sender": {"name": "Soporte UT Cancún", "email": "support@utextracurricular.com"},
        "to": [{"email": to_email}],
        "subject": "Verifica tu cuenta - Sistema RAG",
        "htmlContent": f"""
        <h3>¡Bienvenido a la plataforma!</h3>
        <p>Para poder iniciar sesión y unirte a tus clases, necesitamos verificar tu correo.</p>
        <p>Haz clic en el siguiente enlace para activar tu cuenta:</p>
        <p><a href="{verify_link}">{verify_link}</a></p>
        <p>Este enlace expirará en 24 horas.</p>
        """
    }
    _send_brevo_request(data, to_email, "verificación")

def _send_brevo_request(data: dict, to_email: str, tipo_correo: str):
    url = "https://api.brevo.com/v3/smtp/email"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"))
    req.add_header("accept", "application/json")
    req.add_header("api-key", settings.BREVO_API_KEY) 
    req.add_header("content-type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ ¡Éxito! Correo de {tipo_correo} enviado a {to_email}")
    except Exception as e:
        print(f"❌ Error al enviar correo de {tipo_correo}: {e}")