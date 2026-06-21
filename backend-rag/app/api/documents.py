# app/api/documents.py
import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from supabase import create_client, Client
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/documents", tags=["Documents Engine"])

# Inicializar cliente de Supabase y Modelo de Embeddings
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2",
    google_api_key=settings.GOOGLE_API_KEY,
    output_dimensionality=768
)

@router.post("/")
async def upload_and_process_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Sube un PDF, lo divide en chunks y lo vectoriza en Supabase."""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    user_id = current_user["user_id"]

    try:
        # 1. Registrar el documento vacío en Supabase
        doc_data = {"user_id": user_id, "title": file.filename, "status": "procesando"}
        doc_response = supabase.table("documents").insert(doc_data).execute()
        document_id = doc_response.data[0]["id"]

        # 2. Guardar el PDF temporalmente para que LangChain lo pueda leer
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # 3. Extraer el texto del PDF
        loader = PyPDFLoader(temp_path)
        pages = loader.load()

        # 4. Dividir en Chunks (1000 caracteres por pedazo con un traslape de 200)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(pages)

        # 5. Convertir a Vectores (Embeddings) y guardarlos
        for chunk in chunks:
            page_num = chunk.metadata.get("page", 0) + 1 # PyPDF usa índice 0
            
            # Pide a Gemini que convierta el texto a matemáticas
            vector = embeddings_model.embed_query(chunk.page_content)
            
            # Inserta el chunk amarrado al ID del documento
            chunk_data = {
                "document_id": document_id,
                "page_number": page_num,
                "content": chunk.page_content,
                "embedding": vector
            }
            supabase.table("document_chunks").insert(chunk_data).execute()

        # 6. Actualizar el estado a 'listo'
        supabase.table("documents").update({"status": "listo"}).eq("id", document_id).execute()

        # Limpiar la basura
        os.remove(temp_path)

        return {
            "message": "Documento procesado y vectorizado exitosamente",
            "document_id": document_id,
            "chunks_creados": len(chunks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el motor de ingesta: {str(e)}")
    
    # Agrega esto al final de app/api/documents.py

@router.get("/")
async def get_documents(current_user: dict = Depends(get_current_user)):
    """Devuelve la lista de todos los PDFs subidos por el alumno actual."""
    user_id = current_user["user_id"]
    
    try:
        # Consultamos a Supabase todos los documentos de este usuario
        response = supabase.table("documents").select("*").eq("user_id", user_id).execute()
        
        return {
            "total": len(response.data),
            "documentos": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener documentos: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """Elimina un documento y todos sus vectores asociados (gracias al CASCADE)."""
    user_id = current_user["user_id"]
    
    try:
        # 1. Por seguridad, verificamos que el documento exista y pertenezca a este usuario
        check = supabase.table("documents").select("id").eq("id", document_id).eq("user_id", user_id).execute()
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Documento no encontrado o no tienes permisos para borrarlo.")
            
        # 2. Procedemos a eliminarlo
        supabase.table("documents").delete().eq("id", document_id).execute()
        
        # ¡Magia! No necesitamos hacer un delete en "document_chunks" ni en "flashcards"
        # porque le pusimos ON DELETE CASCADE en el script SQL. La base de datos limpia la basura sola.

        return {"message": "Documento y vectores eliminados correctamente."}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error al eliminar documento: {str(e)}")