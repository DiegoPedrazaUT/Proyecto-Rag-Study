from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from supabase import create_client, Client
from app.core.config import settings

# 1. Inicializamos conexión a Supabase
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# ============================
# 1. CONFIGURACIÓN DE MODELOS 
# ============================
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview", # Conservamos tu modelo elegido
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.3 
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2",
    google_api_key=settings.GOOGLE_API_KEY,
    output_dimensionality=768
)

# ======================
# 2. PROMPT DEL SISTEMA 
# ======================
system_prompt = """Eres un tutor virtual experto de la Universidad Tecnológica (UT).
Tu objetivo es ayudar a los estudiantes a estudiar y comprender sus apuntes.

Estás hablando con el estudiante: {user_name}.
Dirígete a él/ella por su nombre de forma amable y natural.

RESPONDE ÚNICAMENTE BASÁNDOTE EN EL SIGUIENTE CONTEXTO EXTRAÍDO DE LOS APUNTES.
Si la respuesta no está en el contexto, di: "Lo siento, no encuentro esto en tus apuntes de esta sesión."

CONTEXTO DE LOS APUNTES:
{context}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# ===============================
# 3. ALMACÉN DE MEMORIA TEMPORAL 
# ===============================
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# ==========================================
# 4. MOTOR RAG: El Nuevo Retriever Dinámico
# ==========================================
def get_context_for_session(input_data: dict) -> str:
    """Reemplaza a PGVector. Busca solo en los PDFs de la sesión actual."""
    question = input_data["input"]
    session_id = input_data["session_id"]
    
    # A. Saber qué PDFs pertenecen a este chat
    docs_res = supabase.table("rag_session_documents").select("document_id").eq("session_id", session_id).execute()
    if not docs_res.data:
        return "No hay documentos vinculados a esta sesión."
        
    document_ids = [row["document_id"] for row in docs_res.data]
    
    # B. Convertir la pregunta a matemáticas
    query_vector = embeddings.embed_query(question)
    
    # C. Usar la función rápida de Supabase para buscar similitud
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_vector,
            "match_threshold": 0.3,
            "match_count": 3,
            "filter_document_ids": document_ids
        }
    ).execute()
    
    if not response.data:
        return "No se encontró información relevante en los apuntes."
        
    # D. Devolver el texto formateado
    return "\n\n".join([chunk["content"] for chunk in response.data])

# ==========================================
# 5. CONSTRUCCIÓN DE LA CADENA (LCEL)
# ==========================================
def get_rag_chain():
    # Asignamos el contexto usando nuestra nueva función
    qa_chain = (
        RunnablePassthrough.assign(
            context=get_context_for_session
        )
        | prompt
        | llm
        | StrOutputParser() 
    )

    # Le envolvemos tu memoria
    rag_with_history = RunnableWithMessageHistory(
        qa_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        history_factory_config=[
            {"id": "session_id", "annotation": str},
        ]
    )
    
    return rag_with_history