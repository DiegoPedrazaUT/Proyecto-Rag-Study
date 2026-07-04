import json
import urllib.request
import urllib.parse
from core.config import settings

def _get_qr_code_html(link: str):
    """Genera un link a un QR dinámico basado en el enlace de invitación"""
    # Codificamos el enlace para que sea seguro en la URL
    encoded_link = urllib.parse.quote(link)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={encoded_link}"
    return f'<img src="{qr_url}" alt="Código QR de invitación" style="display:block; margin: 10px auto; border: 1px solid #ddd; padding: 5px;">'

def send_invite_email(to_email: str, join_code: str):
    """Envío de invitación a organización solo con Link (sin QR incrustado)"""
    
    # Enlace dinámico que apunta a tu Frontend (o al nuevo GET /join que creamos para pruebas)
    invite_link = f"{settings.FRONTEND_URL}/join?code={join_code}"
    
    data = {
        "sender": {"name": "Sistema Universitario RAG", "email": "invites@utextracurricular.com"},
        "to": [{"email": to_email}],
        "subject": "¡Has sido invitado a una nueva clase!",
        "htmlContent": f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
            <h2 style="color: #2c3e50;">¡Hola!</h2>
            <p>Has sido invitado a unirte a una organización/clase en nuestra plataforma.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid #3498db; margin: 20px 0;">
                <p><strong>Código de invitación:</strong> <span style="font-size: 1.2em; color: #3498db;">{join_code}</span></p>
            </div>
            <p style="text-align: center;">Puedes unirte haciendo clic en el siguiente enlace:</p>
            <p style="text-align: center;"><a href="{invite_link}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Aceptar Invitación</a></p>
            <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
            <p style="font-size: 0.8em; color: #888; text-align: center;">Si no esperabas esta invitación, puedes ignorar este correo.</p>
        </div>
        """
    }
    _send_brevo_request(data, to_email, "invitación")


def _send_brevo_request(data: dict, to_email: str, tipo_correo: str):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY, # type: ignore
        "content-type": "application/json"
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ ¡Éxito! Correo de {tipo_correo} enviado a {to_email}")
    except Exception as e:
        print(f"❌ Error al enviar correo de {tipo_correo}: {e}")