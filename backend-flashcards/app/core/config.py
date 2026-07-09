from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada del microservicio de flashcards."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Conexión a Supabase/Postgres. Debe usar el driver async (asyncpg).
    # Ej: postgresql+asyncpg://user:pass@host:5432/postgres
    DATABASE_URL: str

    # JWT — debe ser el MISMO secreto y algoritmo que usa el servicio de Auth (Boston).
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Logs SQL en consola (útil en dev, apágalo en prod).
    SQL_ECHO: bool = False
    
    # Gemini / LLM
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-flash-preview"



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
