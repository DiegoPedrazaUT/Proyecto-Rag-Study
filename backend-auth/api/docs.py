# backend-auth/api/docs.py

# ==========================================
# 1. AUTH & SESIONES LOCALES
# ==========================================
LOGIN = {
    "summary": "Iniciar Sesión",
    "description": """
    Inicia sesión con correo y contraseña.
    - **Cookies**: Inyecta `access_token` y `refresh_token` en cookies HttpOnly automáticamente.
    - **MFA**: Si el usuario tiene MFA activo, devolverá código 202 y requerirá enviar el `mfa_code`.
    - **Seguridad**: Bloquea la cuenta por 15 minutos tras 5 intentos fallidos (Anti Fuerza-Bruta).
    """,
    "responses": {
        200: {"description": "Login exitoso. Cookies HttpOnly inyectadas. Devuelve datos mínimos del usuario."},
        202: {"description": "MFA requerido. Credenciales correctas, ingrese su código de 6 dígitos."},
        400: {"description": "Petición mal formada (ej. correo inválido)."},
        401: {"description": "Correo o contraseña incorrectos, o código MFA inválido/expirado."},
        403: {"description": "Debes verificar tu correo antes de iniciar sesión."},
        429: {"description": "Demasiados intentos fallidos. Cuenta bloqueada temporalmente."}
    }
}

LOGOUT = {
    "summary": "Cerrar Sesión (Local)",
    "description": "Limpia las cookies `access_token` y `refresh_token` del navegador. Cierra la sesión únicamente de la aplicación universitaria (No cierra la cuenta global de Google del usuario).",
    "responses": {
        200: {"description": "Borra cookies y revoca el refresh token registrado si existe."}
    }
}

REFRESH = {
    "summary": "Refrescar Token de Acceso",
    "description": "Lee el refresh_token de la cookie, valida que esté registrado en BD, lo rota y genera nuevas cookies de sesión.",
    "responses": {
        200: {"description": "Access token y refresh token renovados correctamente."},
        401: {"description": "Refresh token faltante, inválido, expirado, revocado o no registrado."}
    }
}

# ==========================================
# 2. GOOGLE OAUTH2 (SINGLE SIGN-ON)
# ==========================================
GOOGLE_LOGIN = {
    "summary": "Login con Google (Redirección)",
    "description": "Redirige al usuario a la pantalla de consentimiento oficial de Google. **NOTA FRONTEND**: Usar con un enlace directo (`<a href=...>`), no mediante fetch/axios.",
    "responses": {
        307: {"description": "Redirección a accounts.google.com"}
    }
}

GOOGLE_CALLBACK = {
    "summary": "Callback de Google (Interno)",
    "description": """
    Ruta que recibe los datos desde Google.
    - Si el usuario **ya existe**: Inyecta las cookies y hace login automático.
    - Si el usuario **es nuevo**: Devuelve un `temp_token` seguro y un código 202 para que el Frontend lo redirija a la pantalla de "Completar Perfil".
    """,
    "responses": {
        200: {"description": "Usuario existente. Login exitoso y cookies inyectadas."},
        202: {"description": "Usuario nuevo detectado. Se devuelve `temp_token` y `temp_info` para completar perfil."},
        400: {"description": "Error al comunicarse con los servidores de Google."}
    }
}

COMPLETE_STUDENT = {
    "summary": "Completar Perfil Google (Estudiante)",
    "description": "Recibe el `temp_token` de seguridad, la **Matrícula** y la **Carrera**. Finaliza el registro del alumno y le inyecta sus cookies de sesión.",
    "responses": {
        200: {"description": "Perfil completado con éxito. Sesión iniciada."},
        400: {"description": "El correo ya está registrado, la cuenta de Google ya existe o la carrera/departamento no existe."},
        401: {"description": "El token temporal expiró o fue alterado."},
        500: {"description": "Error interno o roles base no configurados en BD."}
    }
}

COMPLETE_TEACHER = {
    "summary": "Completar Perfil Google (Profesor)",
    "description": "Recibe el `temp_token` de seguridad y el **Departamento/Carrera** para finalizar el registro del profesor.",
    "responses": {
        200: {"description": "Perfil completado con éxito. Sesión iniciada."},
        400: {"description": "El correo ya está registrado, la cuenta de Google ya existe o la carrera/departamento no existe."},
        401: {"description": "El token temporal expiró o fue alterado."},
        500: {"description": "Error interno del servidor o rol base no configurado en BD."}
    }
}

# ==========================================
# 3. REGISTRO Y VERIFICACIÓN (MANUAL)
# ==========================================
REGISTER_STUDENT = {
    "summary": "Registrar Estudiante Manual",
    "description": "Crea una cuenta de alumno con contraseña. Genera token de verificación y despacha correo vía Brevo.",
    "responses": {
        201: {"description": "Usuario creado exitosamente. Correo enviado."},
        400: {"description": "El correo o la matrícula ya están en uso, o contraseña débil."},
        500: {"description": "Error interno del servidor."}
    }
}

REGISTER_TEACHER = {
    "summary": "Registrar Profesor Manual",
    "description": "Crea una cuenta de profesor. Genera token de verificación y despacha correo de bienvenida.",
    "responses": {
        201: {"description": "Profesor creado exitosamente. Correo enviado."},
        400: {"description": "El correo ya está en uso o contraseña débil."}
    }
}

VERIFY_EMAIL = {
    "summary": "Verificar Cuenta de Correo",
    "description": "Endpoint tipo GET diseñado para recibir el clic directamente desde el correo del usuario. Valida el token y activa la cuenta.",
    "responses": {
        200: {"description": "HTML de éxito. Cuenta verificada correctamente."},
        400: {"description": "HTML de error. Token inválido, expirado o cuenta ya verificada."}
    }
}

RESEND_VERIFICATION = {
    "summary": "Reenviar Correo de Verificación",
    "description": "Genera un nuevo token de 24hrs y dispara otro correo vía Brevo si la cuenta no está verificada.",
    "responses": {
        200: {"description": "Si el correo existe y no está verificado, se envió un nuevo enlace."},
        400: {"description": "Esta cuenta ya está verificada."}
    }
}

# ==========================================
# 4. GESTIÓN DEL PROPIO PERFIL (/users/me)
# ==========================================
GET_ME = {
    "summary": "Obtener Mi Perfil",
    "description": "Lee el JWT de la cookie e intercepta los datos exactos del usuario logueado. Ideal para cargar el Dashboard.",
    "responses": {
        200: {"description": "Datos del perfil devueltos correctamente."},
        401: {"description": "No estás autenticado (Cookie faltante o expirada)."}
    }
}

PATCH_ME = {
    "summary": "Actualizar Mis Datos (Parcial)",
    "description": "El usuario actualiza sus datos básicos (nombre, apellido). **Seguridad:** El esquema prohíbe que alteren su carrera (`career_id`) o rol.",
    "responses": {
        200: {"description": "Perfil actualizado exitosamente."},
        400: {"description": "Datos de actualización inválidos."},
        401: {"description": "No estás autenticado."}
    }
}

PUT_ME = {
    "summary": "Sobrescribir Mis Datos",
    "description": "El usuario sobrescribe todos sus campos permitidos de un solo golpe.",
    "responses": {
        200: {"description": "Perfil sobrescrito exitosamente."},
        400: {"description": "Datos incompletos o inválidos."},
        401: {"description": "No estás autenticado."}
    }
}

# ==========================================
# 5. GESTIÓN ADMINISTRATIVA (/users)
# ==========================================
GET_USERS = {
    "summary": "Directorio Maestro de Usuarios (Solo Admin)",
    "description": """
    Obtiene la lista paginada de usuarios.
    - **Admin**: Puede ver, buscar y filtrar usuarios por rol o carrera/departamento.
    - **Usuarios normales**: No tienen acceso. Deben usar `/users/me`.
    """,
    "responses": {
        200: {"description": "Lista de usuarios obtenida correctamente."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requiere rol de administrador."}
    }
}

GET_USER_ID = {
    "summary": "Ver Detalle de un Usuario (Solo Admin)",
    "description": "Trae la información detallada de una persona por UUID. Exclusivo para administradores.",
    "responses": {
        200: {"description": "Detalle del usuario obtenido correctamente."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requiere rol de administrador."},
        404: {"description": "Usuario no encontrado."}
    }
}

PATCH_USER_ADMIN = {
    "summary": "Editar Usuario (Solo Admin)",
    "description": "Permite al administrador modificar cualquier dato de un usuario de manera parcial, **incluyendo traslados de carrera** (`career_id`).",
    "responses": {
        200: {"description": "Usuario actualizado exitosamente."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requiere Rol de Administrador."},
        404: {"description": "Usuario a editar no encontrado."}
    }
}

PUT_USER_ADMIN = {
    "summary": "Sobrescribir Usuario (Solo Admin)",
    "description": "Permite al administrador sobrescribir todo el perfil de un usuario, incluyendo su carrera.",
    "responses": {
        200: {"description": "Usuario sobrescrito exitosamente."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requiere Rol de Administrador."},
        404: {"description": "Usuario a editar no encontrado."}
    }
}

DELETE_USER_ADMIN = {
    "summary": "Eliminar Usuario (Solo Admin)",
    "description": "Borrado en cascada de un usuario. Elimina su perfil, historial, organizaciones y documentos ligados.",
    "responses": {
        200: {"description": "Usuario eliminado exitosamente del sistema."},
        401: {"description": "No estás autenticado."},
        403: {"description": "Acceso denegado. Se requiere Rol de Administrador."},
        404: {"description": "Usuario a eliminar no encontrado."}
    }
}

# ==========================================
# 6. MFA Y SEGURIDAD (CONTRASEÑAS)
# ==========================================
MFA_SETUP = {
    "summary": "Configurar Google Authenticator",
    "description": "Genera el secreto MFA para el usuario autenticado. No acepta user_id externo.",
    "responses": {
        200: {"description": "URI del QR y semilla generadas exitosamente."},
        400: {"description": "El MFA ya está activo en esta cuenta (Evita sobrescritura)."},
        401: {"description": "No estás autenticado."}
    }
}

MFA_VERIFY = {
    "summary": "Verificar y Activar MFA",
    "description": "Verifica el código temporal de 6 dígitos para el usuario autenticado y activa MFA.",
    "responses": {
        200: {"description": "MFA activado exitosamente."},
        400: {"description": "MFA no está en proceso de configuración."},
        401: {"description": "Código de 6 dígitos inválido o expirado."}
    }
}

FORGOT_PASSWORD = {
    "summary": "Olvidé mi Contraseña",
    "description": "Genera token y envía el enlace. **Seguridad**: Devuelve 200 exista o no el correo para prevenir ataques de enumeración (adivinación de correos).",
    "responses": {
        200: {"description": "Si el correo existe, se han enviado las instrucciones."}
    }
}

RESET_PASSWORD = {
    "summary": "Restablecer Contraseña",
    "description": "Recibe el token del enlace del correo y la nueva contraseña.",
    "responses": {
        200: {"description": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión."},
        400: {"description": "El token es inválido o ha expirado (15 mins)."}
    }
}

CHANGE_PASSWORD = {
    "summary": "Cambiar Contraseña (Sesión Activa)",
    "description": "Requiere que el usuario esté logueado. Pide la contraseña actual y genera el nuevo hash Argon2 para la nueva.",
    "responses": {
        200: {"description": "Contraseña cambiada exitosamente."},
        401: {"description": "La contraseña actual es incorrecta o sesión inválida."}
    }
}