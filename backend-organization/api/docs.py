# backend-org/api/docs.py

CREATE_ORG = {
    "summary": "Crear un nuevo Salón de Clases",
    "description": """
    Permite a un profesor crear una nueva organización/salón. 
    - **Automatización**: El `career_id` se extrae del perfil del profesor.
    - **Rol**: El profesor que lo crea se asigna automáticamente como dueño.
    """,
    "responses": {
        200: {"description": "Salón creado exitosamente. Devuelve el `join_code`."},
        403: {"description": "Acceso denegado. Solo los profesores pueden crear salones."},
        404: {"description": "Perfil de profesor incompleto o no encontrado."}
    }
}

GET_MY_ORGS = {
    "summary": "Listar mis Salones",
    "description": """
    Devuelve los salones a los que pertenece el usuario autenticado.
    - Si es **Profesor**: Muestra los salones que ha creado.
    - Si es **Alumno**: Muestra los salones en los que está oficialmente aceptado.
    """,
    "responses": {
        200: {"description": "Lista de salones obtenida correctamente."}
    }
}

GET_MEMBERS = {
    "summary": "Directorio Público del Salón",
    "description": "Devuelve la lista de todos los usuarios que están **oficialmente aceptados** en el salón. Todos los miembros pueden ver este directorio.",
    "responses": {
        200: {"description": "Lista de miembros aceptados obtenida correctamente."}
    }
}

GET_WAITLIST = {
    "summary": "Lista de Espera (Solo Profesor)",
    "description": """
    Devuelve la lista de alumnos que solicitaron unirse al salón y están en estado `pending`.
    - **Seguridad**: Blindado con Anti-IDOR. Solo el creador del salón puede ver esta lista.
    """,
    "responses": {
        200: {"description": "Lista de espera obtenida correctamente."},
        403: {"description": "Acceso denegado. No eres profesor o no eres el dueño del salón."},
        404: {"description": "Salón no encontrado."}
    }
}

JOIN_ORG = {
    "summary": "Unirse a un Salón (Código Manual/QR/Link)",
    "description": """
    Permite a un estudiante solicitar acceso a un salón utilizando el código de invitación (ej. `CLASS-XYZ1`).
    - **Condición**: El estudiante es colocado en la Lista de Espera (`pending`).
    - **Candado**: El sistema verifica que el alumno pertenezca a la misma carrera que el salón.
    """,
    "responses": {
        200: {"description": "Solicitud enviada. El alumno está en lista de espera."},
        403: {"description": "Acceso denegado. Solo alumnos pueden unirse o candado de carrera no superado."},
        404: {"description": "Código inválido o perfil de estudiante no encontrado."}
    }
}

GET_QR = {
    "summary": "Obtener Código QR de Invitación",
    "description": "Devuelve una URL con la imagen generada de un Código QR para que el profesor la proyecte en clase.",
    "responses": {
        200: {"description": "URL de la imagen del QR y código de unión."},
        404: {"description": "Salón no encontrado."}
    }
}

PATCH_MEMBER_STATUS = {
    "summary": "Aceptar o Rechazar Alumno",
    "description": """
    El profesor dueño del salón cambia el estatus de un alumno en la lista de espera.
    - Se debe enviar `accepted` o `rejected`.
    - Si el alumno fue invitado por correo, su invitación también se marca como aceptada.
    """,
    "responses": {
        200: {"description": "Estatus actualizado correctamente."},
        403: {"description": "Acceso denegado. No eres el dueño del salón."},
        404: {"description": "Alumno no encontrado en la lista de espera."}
    }
}

SEND_INVITE = {
    "summary": "Invitar por Correo Electrónico",
    "description": "Registra una invitación en la bitácora y dispara un correo electrónico usando Brevo con el enlace de unión directo.",
    "responses": {
        200: {"description": "Correo enviado y registrado en la bitácora."},
        404: {"description": "Salón no encontrado."}
    }
}

GET_INVITES = {
    "summary": "Historial de Invitaciones",
    "description": "Muestra todos los correos electrónicos a los que el profesor les ha enviado una invitación.",
    "responses": {
        200: {"description": "Historial obtenido correctamente."},
        403: {"description": "Solo los profesores pueden ver este historial."}
    }
}

UPDATE_ORG = {
    "summary": "Editar Salón de Clases",
    "description": "El profesor creador puede modificar el nombre, descripción o asignatura del salón. Se pueden enviar solo los campos que se desean cambiar (Actualización parcial).",
    "responses": {
        200: {"description": "Salón actualizado exitosamente."},
        403: {"description": "No tienes permiso para editar este salón."},
        404: {"description": "Salón no encontrado."}
    }
}

DELETE_ORG = {
    "summary": "Eliminar Salón de Clases",
    "description": "Elimina permanentemente el salón. Gracias a la base de datos, se borran en cascada todos los miembros e invitaciones asociados.",
    "responses": {
        200: {"description": "Salón eliminado exitosamente."},
        403: {"description": "No tienes permiso para eliminar este salón."},
        404: {"description": "Salón no encontrado."}
    }
}