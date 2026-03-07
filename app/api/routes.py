import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.rag.engine import get_rag_chain

router = APIRouter(prefix="/chat", tags=["Chatbot RAG"])

# 1. Formato debe tener la petición de Nata
class ChatRequest(BaseModel):
    pregunta: str

    class Config:
        json_schema_extra = {
            "example": {"pregunta": "¿A qué hora es el taller de ajedrez?"}
        }

@router.get("/test-auth")
def test_authentication(current_user: dict = Depends(get_current_user)):
    return {
        "message": "¡Autenticación exitosa!",
        "datos_del_token": current_user
    }

@router.post("/ask")
def ask_chatbot(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Recibe una pregunta, busca en Supabase (PGVector) y responde usando Gemini.
    """
    try:
        rag_chain = get_rag_chain()

      
        session_id = current_user["user_id"]

        respuesta = rag_chain.invoke(
            {"input": request.pregunta},
            config={"configurable": {"session_id": session_id}}
        )

        return {
            "pregunta": request.pregunta,
            "respuesta": respuesta 
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el motor RAG: {str(e)}")