# backend-auth/api/docs.py

# ==========================================
# 1. AUTH & SESIONES (auth.py)
# ==========================================
LOGIN = {
    "summary": "Iniciar Sesión",
    "description": """
    Inicia sesión con correo y contraseña.
    - **Cookies**: Inyecta `access_token` y `refresh_token` en cookies HttpOnly de forma automática.
    - **MFA**: Si el usuario tiene MFA activo, devolverá código 202 y requerirá enviar el `mfa_code`.
    - **Seguridad**: Bloquea la cuenta por 15 minutos tras 5 intentos fallidos.
    """,
    "responses": {
        200: {"description": "Login exitoso. Cookies inyectadas."},
        202: {"description": "MFA requerido. Enviar de nuevo con `mfa_code`."},
        400: {"description": "Petición mal formada (ej. correo inválido)."},
        401: {"description": "Credenciales inválidas o cuenta bloqueada."}
    }
}

LOGOUT = {
    "summary": "Cerrar Sesión",
    "description": "Limpia las cookies `access_token` y `refresh_token` del navegador del usuario.",
    "responses": {
        200: {"description": "Sesión cerrada correctamente."}
    }
}

REFRESH = {
    "summary": "Refrescar Token de Acceso",
    "description": "Lee el `refresh_token` de la cookie y genera un nuevo `access_token` sin pedir credenciales.",
    "responses": {
        200: {"description": "Nuevo token de acceso inyectado en cookie."},
        401: {"description": "Refresh token inválido, no encontrado o expirado."}
    }
}

# ==========================================
# 2. GOOGLE OAUTH2 (auth.py)
# ==========================================
GOOGLE_LOGIN = {
    "summary": "Login con Google (Redirección)",
    "description": "Redirige al usuario a la pantalla de consentimiento oficial de Google. **NOTA**: No usar mediante Swagger, abrir directamente en el navegador.",
    "responses": {
        307: {"description": "Redirección a accounts.google.com"}
    }
}

GOOGLE_CALLBACK = {
    "summary": "Callback de Google",
    "description": """
    Ruta que recibe los datos desde Google.
    - Si el usuario **ya existe**: Le inyecta las cookies y hace login.
    - Si el usuario **es nuevo**: Devuelve un `temp_token` y un código 202 para que el Frontend lo mande a "Completar Perfil".
    """,
    "responses": {
        200: {"description": "Login exitoso. Cookies inyectadas."},
        202: {"description": "Usuario nuevo. Se devuelve un `temp_token` para completar perfil."},
        400: {"description": "Error al comunicarse con Google o procesar los datos."}
    }
}

COMPLETE_STUDENT = {
    "summary": "Completar Perfil Google (Estudiante)",
    "description": "Recibe el `temp_token` de Google junto con la Matrícula y la Carrera para finalizar el registro del alumno y darle acceso.",
    "responses": {
        200: {"description": "Registro exitoso. Cookies inyectadas."},
        400: {"description": "Matrícula ya registrada o datos inválidos."},
        401: {"description": "Token temporal inválido o expirado."}
    }
}

COMPLETE_TEACHER = {
    "summary": "Completar Perfil Google (Profesor)",
    "description": "Recibe el `temp_token` de Google y la Carrera para finalizar el registro del profesor.",
    "responses": {
        200: {"description": "Registro exitoso. Cookies inyectadas."},
        401: {"description": "Token temporal inválido o expirado."}
    }
}

# ==========================================
# 3. GESTIÓN DE USUARIOS (users.py)
# ==========================================
REGISTER_STUDENT = {
    "summary": "Registrar Estudiante Nuevo",
    "description": "Crea una cuenta de alumno. Genera un token de verificación y envía el correo por Brevo automáticamente.",
    "responses": {
        201: {"description": "Usuario creado exitosamente. Correo enviado."},
        400: {"description": "El correo o la matrícula ya están registrados en el sistema."}
    }
}

REGISTER_TEACHER = {
    "summary": "Registrar Profesor Nuevo",
    "description": "Crea una cuenta de profesor. Genera token de verificación y envía correo de bienvenida.",
    "responses": {
        201: {"description": "Profesor creado exitosamente. Correo enviado."},
        400: {"description": "El correo ya está registrado en el sistema."}
    }
}

GET_ME = {
    "summary": "Obtener Mi Perfil",
    "description": "Lee el JWT de la cookie y devuelve la información del usuario autenticado.",
    "responses": {
        200: {"description": "Perfil obtenido exitosamente."},
        401: {"description": "No estás autenticado (Token faltante o expirado)."}
    }
}

PATCH_ME = {
    "summary": "Actualizar Mi Perfil (Parcial)",
    "description": "El usuario actualiza sus datos básicos (nombre, apellido). **No puede cambiar su carrera ni su rol.**",
    "responses": {
        200: {"description": "Perfil actualizado exitosamente."},
        400: {"description": "Datos de actualización inválidos."},
        401: {"description": "No estás autenticado."}
    }
}

PUT_ME = {
    "summary": "Sobrescribir Mi Perfil",
    "description": "El usuario actualiza toda su información básica de golpe.",
    "responses": {
        200: {"description": "Perfil sobrescrito exitosamente."},
        400: {"description": "Datos incompletos o inválidos."},
        401: {"description": "No estás autenticado."}
    }
}

GET_USERS = {
    "summary": "Directorio de Usuarios",
    "description": """
    Obtiene la lista paginada de usuarios. 
    - **Admin**: Puede ver a todos sin filtro.
    - **Profesor**: Puede filtrar por `role=student` y `career_id=X` para ver solo a los alumnos de su departamento.
    """,
    "responses": {
        200: {"description": "Lista de usuarios obtenida correctamente."},
        401: {"description": "No estás autenticado."}
    }
}

GET_USER_ID = {
    "summary": "Ver Detalle de Usuario",
    "description": "Trae la información detallada de un usuario por su UUID.",
    "responses": {
        200: {"description": "Detalle del usuario obtenido correctamente."},
        401: {"description": "No estás autenticado."},
        404: {"description": "Usuario no encontrado en la base de datos."}
    }
}

PATCH_USER_ADMIN = {
    "summary": "Editar Usuario (Solo Admin)",
    "description": "Permite al administrador modificar cualquier dato de un usuario, **incluyendo la carrera** (`career_id`).",
    "responses": {
        200: {"description": "Usuario actualizado exitosamente."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requieren permisos de administrador."},
        404: {"description": "Usuario a editar no encontrado."}
    }
}

# ==========================================
# 4. MFA - MULTIFACTOR (mfa.py)
# ==========================================
MFA_SETUP = {
    "summary": "Configurar Google Authenticator",
    "description": "Genera el Secreto (semilla) y la URI para que el Frontend genere el Código QR que el usuario escaneará.",
    "responses": {
        200: {"description": "URI del QR y semilla generadas exitosamente."},
        400: {"description": "El usuario ya tiene el MFA activado."},
        401: {"description": "No estás autenticado."},
        404: {"description": "Usuario no encontrado."}
    }
}

MFA_VERIFY = {
    "summary": "Verificar y Activar MFA",
    "description": "Recibe el código de 6 dígitos de la app. Si es correcto, activa permanentemente el 2FA en la cuenta del usuario.",
    "responses": {
        200: {"description": "MFA activado exitosamente."},
        400: {"description": "El código de 6 dígitos es incorrecto o inválido."},
        401: {"description": "No estás autenticado."},
        404: {"description": "Usuario no encontrado."}
    }
}

# ==========================================
# 5. RECUPERACIÓN Y CORREOS (passwords.py)
# ==========================================
FORGOT_PASSWORD = {
    "summary": "Olvidé mi Contraseña",
    "description": "Genera un token de recuperación y envía el enlace por correo (Expira en 15 minutos). **Seguridad**: Siempre devuelve 200 exista o no el correo para prevenir ataques de enumeración.",
    "responses": {
        200: {"description": "Si el correo existe, el enlace de recuperación ha sido enviado."}
    }
}

RESET_PASSWORD = {
    "summary": "Restablecer Contraseña",
    "description": "Recibe el token del enlace del correo y la nueva contraseña para cambiarla de forma segura.",
    "responses": {
        200: {"description": "Contraseña restablecida correctamente."},
        400: {"description": "El token de recuperación es inválido o ha expirado."}
    }
}

CHANGE_PASSWORD = {
    "summary": "Cambiar Contraseña (Sesión Activa)",
    "description": "Requiere que el usuario esté logueado. Pide la contraseña actual y la nueva.",
    "responses": {
        200: {"description": "Contraseña cambiada exitosamente."},
        400: {"description": "La contraseña actual es incorrecta o la nueva contraseña no cumple con la seguridad."},
        401: {"description": "No estás autenticado."}
    }
}

RESEND_VERIFICATION = {
    "summary": "Reenviar Correo de Verificación",
    "description": "Si el usuario no verificó su cuenta en 24 horas o no le llegó, este endpoint le genera un token nuevo y dispara otro correo.",
    "responses": {
        200: {"description": "Correo de verificación reenviado exitosamente."},
        400: {"description": "El usuario ya está verificado."},
        404: {"description": "Correo electrónico no encontrado en el sistema."}
    }
}