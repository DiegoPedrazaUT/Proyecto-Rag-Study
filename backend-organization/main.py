# backend-org/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importes directos de la carpeta 'database' que ya vive dentro de backend-org
from database.database import engine
from database import models
from api.routers import organizations

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Org Microservice - Sistema Universitario",
    description="Microservicio de Organizaciones (Salones) para el sistema RAG",
    version="1.0.0"
)

# Configuración de CORS exacta a la que ya te funcionó en Auth
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://front-ut-extracurricular-production.up.railway.app",
    "https://api-getway-utextracurricular-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectamos las rutas
app.include_router(organizations.router)

# Endpoint base (Health Check)
@app.get("/")
def health_check():
    return {
        "status": "online", 
        "message": "Microservicio de Organizaciones conectado 🚀"
    }

if __name__ == "__main__":
    import uvicorn
    # Usamos el puerto 8002 para no chocar con el 8080 de Auth si corres ambos localmente
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)