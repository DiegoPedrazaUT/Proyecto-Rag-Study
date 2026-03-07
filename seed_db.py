import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()
connection_string = os.getenv("DATABASE_URL")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

print("Leyendo el documento PDF...")
loader = PyPDFLoader("Actividades extracurriculares.pdf")
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
splits = text_splitter.split_documents(docs)

print(f"Vectorizando y guardando {len(splits)} fragmentos en Supabase...")
vectorstore = PGVector(
    embeddings=embeddings,
    collection_name="extracurriculares_ut",
    connection=connection_string,
    use_jsonb=True,
)

vectorstore.add_documents(splits)
print("¡Vectores guardados exitosamente! Ya puedes borrar el PDF si quieres.")