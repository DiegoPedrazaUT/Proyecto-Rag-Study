from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client

from app.core.security import get_current_user
from app.core.config import settings
from app.rag.engine import get_rag_chain

router = APIRouter(prefix="/rag", tags=["RAG Chat Engine"])

# Inicializar cliente de Supabase (con la service_role key que ya configuraste)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# --- Esquemas de Datos (Pydantic) ---
class SessionCreate(BaseModel):
    title: str = "Nuevo Chat de Estudio"
    document_ids: List[str]  # Lista de los IDs de los PDFs que Nata mandará desde el front

class SessionUpdate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    mensaje: str

# --- Endpoints ---
@router.post("/sessions")
async def create_chat_session(
    session_req: SessionCreate, 
    current_user: dict = Depends(get_current_user)
):
    """Crea una nueva sesión de chat y la asocia a uno o varios documentos."""
    user_id = current_user["user_id"]

    try:
        # 1. Crear la sesión principal
        session_data = {"user_id": user_id, "title": session_req.title}
        session_res = supabase.table("rag_sessions").insert(session_data).execute()
        session_id = session_res.data[0]["id"]

        # 2. Vincular los documentos a esta sesión en la tabla puente
        if session_req.document_ids:
            puente_data = [
                {"session_id": session_id, "document_id": doc_id} 
                for doc_id in session_req.document_ids
            ]
            supabase.table("rag_session_documents").insert(puente_data).execute()

        return {
            "message": "Sesión creada exitosamente",
            "session_id": session_id,
            "documentos_vinculados": len(session_req.document_ids)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear sesión: {str(e)}")


@router.get("/sessions")
async def get_user_sessions(current_user: dict = Depends(get_current_user)):
    """Devuelve todas las sesiones de chat del alumno para pintar la barra lateral."""
    user_id = current_user["user_id"]
    
    try:
        # Traemos los chats ordenados del más reciente al más antiguo
        response = supabase.table("rag_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return {
            "total": len(response.data),
            "sesiones": response.data
        }
    
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener sesiones: {str(e)}")
    
@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    """Devuelve todo el historial de la plática para que el Frontend lo pinte."""
    try:
        # Traemos los mensajes ordenados por fecha de creación (del más viejo al más nuevo)
        response = supabase.table("rag_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
        return {"mensajes": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar historial: {str(e)}")


@router.post("/sessions/{session_id}/messages")
async def send_message_to_rag(
    session_id: str, 
    req: MessageCreate, 
    current_user: dict = Depends(get_current_user)
):
    """Recibe la pregunta, consulta a Gemini/PGVector y guarda la respuesta."""
    user_name = current_user.get("user_name", "Estudiante")

    try:
        # 1. Guardar la pregunta del Humano en la base de datos
        supabase.table("rag_messages").insert({
            "session_id": session_id,
            "role": "human",
            "content": req.mensaje
        }).execute()

        # 2. Despertar a LangChain y Gemini
        chain = get_rag_chain()
        
        # Le pasamos la pregunta, el ID de sesión (para el contexto) y el nombre del usuario
        ia_response = chain.invoke(
            {
                "input": req.mensaje, 
                "session_id": session_id,
                "user_name": user_name
            },
            config={"configurable": {"session_id": session_id}} # Clave para que funcione la memoria
        )

        # 3. Guardar la respuesta de la IA en la base de datos
        supabase.table("rag_messages").insert({
            "session_id": session_id,
            "role": "ai",
            "content": ia_response
        }).execute()

        # 4. Devolver la respuesta al frontend
        return {
            "pregunta": req.mensaje,
            "respuesta": ia_response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el motor RAG: {str(e)}")
    
@router.patch("/sessions/{session_id}")
async def update_session_title(
    session_id: str, 
    req: SessionUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Cambia el nombre de la sesión (ej. 'Nuevo Chat' -> 'Repaso de Física')."""
    user_id = current_user["user_id"]
    try:
        res = supabase.table("rag_sessions").update({"title": req.title}).eq("id", session_id).eq("user_id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o sin permisos.")
        return {"message": "Título actualizado", "session": res.data[0]}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Elimina un chat por completo. (Elimina mensajes en cascada automáticamente)."""
    user_id = current_user["user_id"]
    try:
        res = supabase.table("rag_sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o sin permisos.")
        return {"message": "Sesión y todos sus mensajes eliminados correctamente."}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error al eliminar sesión: {str(e)}")
    
@router.delete("/messages/{message_id}")
async def delete_single_message(message_id: str, current_user: dict = Depends(get_current_user)):
    """Borra un solo mensaje (burbuja de chat) de la base de datos."""
    try:
        res = supabase.table("rag_messages").delete().eq("id", message_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
        return {"message": "Mensaje eliminado del historial."}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error al eliminar mensaje: {str(e)}")
    
@router.post("/sessions/{session_id}/regenerate")
async def regenerate_last_response(session_id: str, current_user: dict = Depends(get_current_user)):
    """Borra la última respuesta de la IA y genera una nueva basándose en la última pregunta."""
    user_name = current_user.get("user_name", "Estudiante")
    user_id = current_user["user_id"]

    try:
        # 1. Validar que la sesión es del usuario
        session_check = supabase.table("rag_sessions").select("id").eq("id", session_id).eq("user_id", user_id).execute()
        if not session_check.data:
            raise HTTPException(status_code=404, detail="Sesión no encontrada.")

        # 2. Traer los últimos 2 mensajes del chat
        messages_res = supabase.table("rag_messages").select("*").eq("session_id", session_id).order("created_at", desc=True).limit(2).execute()
        messages = messages_res.data

        # Validamos que el último mensaje sea de la IA y el penúltimo del humano
        if len(messages) < 2 or messages[0]["role"] != "ai" or messages[1]["role"] != "human":
            raise HTTPException(status_code=400, detail="No hay una respuesta reciente de IA para regenerar.")

        ai_msg_id = messages[0]["id"]
        last_human_msg = messages[1]["content"]

        # 3. Borrar la respuesta anterior de la IA
        supabase.table("rag_messages").delete().eq("id", ai_msg_id).execute()

        # 4. Volver a llamar al motor RAG con la misma pregunta
        chain = get_rag_chain()
        ia_response = chain.invoke(
            {
                "input": last_human_msg,
                "session_id": session_id,
                "user_name": user_name
            },
            config={"configurable": {"session_id": session_id}}
        )

        # 5. Guardar la nueva respuesta en la base de datos
        supabase.table("rag_messages").insert({
            "session_id": session_id,
            "role": "ai",
            "content": ia_response
        }).execute()

        return {
            "pregunta_original": last_human_msg,
            "respuesta_regenerada": ia_response
        }

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error al regenerar respuesta: {str(e)}")