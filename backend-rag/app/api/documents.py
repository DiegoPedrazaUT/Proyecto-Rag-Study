import os
import io
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from supabase import create_client, Client
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from fastapi import Response
from pydantic import BaseModel
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.engine import llm 
from langchain_core.messages import SystemMessage, HumanMessage

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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

class DocumentUpdate(BaseModel):
    title: str

class ChunkRequest(BaseModel):
    texto: str
    chunk_size: int = 1000
    chunk_overlap: int = 200

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
    

@router.get("/")
async def get_documents(current_user: dict = Depends(get_current_user)):
    """Devuelve la lista de todos los PDFs subidos por el alumno actual."""
    user_id = current_user["user_id"]
    
    try:
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

        return {"message": "Documento y vectores eliminados correctamente."}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error al eliminar documento: {str(e)}")
    
@router.post("/{document_id}/summary")
async def generate_document_summary(
    document_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Lee todos los vectores de un PDF específico y genera un resumen académico estructurado."""
    user_id = current_user["user_id"]

    try:
        # 1. Validar propiedad del documento
        doc_check = supabase.table("documents").select("title").eq("id", document_id).eq("user_id", user_id).execute()
        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Documento no encontrado o sin permisos.")
        
        doc_title = doc_check.data[0]["title"]

        # 2. Extraer todo el texto limpio desde la base de datos (sin volver a leer el PDF físico)
        chunks_res = supabase.table("document_chunks").select("content").eq("document_id", document_id).execute()
        
        if not chunks_res.data:
            raise HTTPException(status_code=400, detail="El documento no tiene contenido procesado.")

        # Unimos todos los fragmentos en un solo texto gigante
        full_text = "\n\n".join([row["content"] for row in chunks_res.data])

        # 3. Construir el Prompt Estricto para el Resumen
        prompt = [
            SystemMessage(content="""Eres un asistente académico experto de la UT. 
Tu tarea es leer el documento proporcionado y generar un resumen estructurado y fácil de digerir.
REGLAS:
- Usa formato Markdown (títulos, viñetas, negritas).
- Destaca los conceptos más importantes.
- Si hay fórmulas, fechas clave o definiciones, ponlas en una sección especial.
- Sé conciso pero no omitas información vital."""),
            HumanMessage(content=f"Documento: {doc_title}\n\nContenido a resumir:\n{full_text}")
        ]

        # 4. Invocar a Gemini (Aprovechando su enorme ventana de contexto)
        respuesta = llm.invoke(prompt)

        return {
            "document_id": document_id,
            "title": doc_title,
            "summary": respuesta.content
        }

    except Exception as e:
        if isinstance(e, HTTPException): 
            raise e
        raise HTTPException(status_code=500, detail=f"Error al generar el resumen: {str(e)}")
    
@router.patch("/{document_id}")
async def update_document_metadata(
    document_id: str, 
    req: DocumentUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Permite al alumno cambiar el nombre de su documento."""
    user_id = current_user["user_id"]
    try:
        res = supabase.table("documents").update({"title": req.title}).eq("id", document_id).eq("user_id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Documento no encontrado o sin permisos.")
        return {"message": "Documento actualizado", "document": res.data[0]}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")


@router.get("/{document_id}/download")
async def download_document_as_pdf(
    document_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """
    Reconstruye el texto del documento desde la base de datos 
    y genera dinámicamente un archivo PDF limpio y formateado para su descarga.
    """
    user_id = current_user["user_id"]
    try:
        # 1. Validar propiedad del documento en Supabase
        doc_check = supabase.table("documents").select("title").eq("id", document_id).eq("user_id", user_id).execute()
        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Documento no encontrado.")
        
        doc_title = doc_check.data[0]["title"]
        
        # 2. Traer todos los chunks de texto ordenados por su página original
        chunks_res = supabase.table("document_chunks").select("content").eq("document_id", document_id).order("page_number", desc=False).execute()
        
        if not chunks_res.data:
            raise HTTPException(status_code=400, detail="El documento no contiene texto procesado.")

        # 3. Crear un buffer de bytes en memoria RAM
        pdf_buffer = io.BytesIO()
        
        # 4. Configurar el lienzo y estructura del PDF usando ReportLab
        doc = SimpleDocTemplate(
            pdf_buffer, 
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
        )
        
        # Estilos de tipografía personalizados
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'PDFTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor='#1a365d', # Azul institucional
            spaceAfter=20
        )
        body_style = ParagraphStyle(
            'PDFBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=15,
            spaceAfter=10
        )

        story = []
        story.append(Paragraph(f"Documento Extraído: {doc_title}", title_style))
        story.append(Spacer(1, 15))

        # --- ALGORITMO DE AUTO-SANACIÓN DE FORMATO ---
        for row in chunks_res.data:
            text_raw = row["content"]
            
            # Reemplazamos los saltos de línea dobles por un marcador temporal único
            text_sanitized = text_raw.replace("\n\n", "[[PARRAFO_BREAK]]")
            
            # Los saltos de línea simples (los culpables del formato raro) los volvemos espacios
            text_sanitized = text_sanitized.replace("\n", " ")
            
            # Limpiamos espacios dobles acumulados
            while "  " in text_sanitized:
                text_sanitized = text_sanitized.replace("  ", " ")
                
            # Restauramos los verdaderos saltos de párrafo usando la etiqueta HTML de ReportLab (<br/>)
            text_sanitized = text_sanitized.replace("[[PARRAFO_BREAK]]", "<br/><br/>")

            if text_sanitized.strip():
                story.append(Paragraph(text_sanitized, body_style))
                story.append(Spacer(1, 8))
        # ----------------------------------------------

        # --- ¡ESTAS ERAN LAS LÍNEAS QUE HACÍAN FALTA! ---
        # Compilar el árbol de elementos dentro del buffer en memoria
        doc.build(story)
        
        # Mover el puntero del buffer al inicio del archivo binario generado
        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.getvalue() # <-- Aquí se define 'pdf_data' con éxito
        pdf_buffer.close()
        # ------------------------------------------------

        # 5. Retornar la respuesta forzando las cabeceras binarias de PDF
        filename_sanitized = doc_title.replace(" ", "_")
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_sanitized}_extraido.pdf"'
            }
        )
        
    except Exception as e:
        if isinstance(e, HTTPException): 
            raise e
        raise HTTPException(status_code=500, detail=f"Error al generar la descarga PDF: {str(e)}")
        

@router.post("/v1/chunk")
async def chunk_text_utility(
    req: ChunkRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Endpoint de utilidad: Recibe un texto largo y devuelve cómo LangChain lo dividiría."""
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=req.chunk_size, 
            chunk_overlap=req.chunk_overlap
        )
        chunks = text_splitter.split_text(req.texto)
        
        return {
            "total_chunks": len(chunks),
            "chunks": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar chunks: {str(e)}")


@router.get("/{document_id}/reindex")
async def get_document_index(
    document_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Devuelve un mapeo de las páginas vectorizadas para que el front sepa el índice del PDF."""
    user_id = current_user["user_id"]
    try:
        chunks_res = supabase.table("document_chunks").select("page_number").eq("document_id", document_id).execute()
        
        if not chunks_res.data:
            return {"document_id": document_id, "total_paginas": 0, "paginas_indexadas": []}
            
        paginas = sorted(list(set([row["page_number"] for row in chunks_res.data])))
        
        return {
            "document_id": document_id,
            "total_paginas_procesadas": len(paginas),
            "ultima_pagina_leida": paginas[-1] if paginas else 0, # Simulamos la última página leída
            "paginas_indexadas": paginas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reindexar: {str(e)}")