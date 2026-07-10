from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
# Importes de la carpeta compartida 'database'
from database.database import get_db, engine
from database import models
# Importe del enrutador de autenticación
from api.routers import auth, users, mfa, passwords
from core.config import settings


app = FastAPI(
    title="Auth Microservice - Sistema Universitario",
    description="Microservicio de Identidad y Acceso para el sistema RAG",
    version="1.0.0"
)


if settings.ENVIRONMENT == "development":
    models.Base.metadata.create_all(bind=engine)


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


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(mfa.router)
app.include_router(passwords.router)


@app.get("/")
def health_check(db: Session = Depends(get_db)):
    roles_count = db.query(models.Role).count()
    return {
        "status": "online",
        "message": "Microservicio de Auth conectado correctamente a Supabase 🚀",
        "roles_in_db": roles_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)