from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from app.core.config import settings

# ==========================================
# 1. CONFIGURACIÓN DE MODELOS
# ==========================================
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.3 
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.GOOGLE_API_KEY
)

# ==========================================
# 2. PROMPT DEL SISTEMA (¡Ahora con Memoria!)
# ==========================================
system_prompt = """Eres el asistente virtual oficial de actividades extracurriculares de la UT Cancún.
Tu objetivo es ayudar a los estudiantes a encontrar información sobre talleres, deportes y eventos.

Usa ÚNICAMENTE el siguiente contexto para responder a la pregunta. 
Si la respuesta no está en el contexto, di: "Lo siento, no tengo esa información sobre las actividades extracurriculares." No inventes respuestas.

Contexto:
{context}"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# ==========================================
# 3. ALMACÉN DE MEMORIA TEMPORAL
# ==========================================
# Este diccionario guardará el historial. La "llave" será el user_id del alumno.
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# ==========================================
# 4. MOTOR RAG (Enuelto en memoria)
# ==========================================
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_rag_chain():
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="extracurriculares_ut",
        connection=settings.DATABASE_URL,
        use_jsonb=True,
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    qa_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: x["input"]) | retriever | format_docs
        )
        | prompt
        | llm
        | StrOutputParser() 
    )

    conversational_rag_chain = RunnableWithMessageHistory(
        qa_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    return conversational_rag_chain