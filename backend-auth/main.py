from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from database.database import get_db, engine
from database import models
from api.routers import auth, users, mfa, passwords
from core.config import settings


app = FastAPI(
    title="Auth Microservice - Sistema Universitario",
    description="Microservicio de Identidad y Acceso para el sistema RAG",
    version="1.0.0"
)


if settings.ENVIRONMENT == "development":
    models.Base.metadata.create_all(bind=engine)


def normalize_origin(origin: str | None) -> str | None:
    if not origin:
        return None

    origin = origin.strip().rstrip("/")

    if not origin:
        return None

    return origin


raw_origins = [
    "http://localhost:3000",
    "http://localhost:5173",

    # Frontend actual en Railway
    "https://proyecto-rag-study-front-production.up.railway.app",

    # FRONTEND_URL desde variables de entorno
    settings.FRONTEND_URL,
]

origins = list({
    origin
    for origin in (normalize_origin(item) for item in raw_origins)
    if origin is not None
})


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