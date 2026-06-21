# app/api/rag.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client

from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/rag", tags=["RAG Chat Engine"])

# Inicializar cliente de Supabase (con la service_role key que ya configuraste)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# --- Esquemas de Datos (Pydantic) ---
class SessionCreate(BaseModel):
    title: str = "Nuevo Chat de Estudio"
    document_ids: List[str]  # Lista de los IDs de los PDFs que Nata mandará desde el front

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