import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.routes import router as chat_router 

app = FastAPI(
    title="Chatbot RAG Microservice - UT Cancún",
    description="Microservicio de IA con Gemini y LangChain",
    version="1.0.0"
)

# CORS para que tu Nata te puedas comunicar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

@app.get("/")
async def root():
    return {"message": "Microservicio RAG conectado y listo para usar Gemini 🤖"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run("main:app", host="0.0.0.0", port=port)