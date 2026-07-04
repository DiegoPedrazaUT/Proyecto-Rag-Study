import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Forzar la carga desde el directorio actual (el microservicio que lo llame)
load_dotenv(os.path.join(os.getcwd(), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("ERROR: La variable DATABASE_URL no fue encontrada o está vacía en el archivo .env")

# ==========================================
# MAGIA AQUÍ: pool_pre_ping y pool_recycle para Supabase
# ==========================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verifica si Supabase cerró la conexión y la reabre si es necesario
    pool_recycle=1800    # Renueva las conexiones cada 30 minutos automáticamente
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()