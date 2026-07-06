from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 1. Definimos las variables (Pydantic las buscará en Railway en MAYÚSCULAS)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    GOOGLE_API_KEY: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    DATABASE_URL: str

    # 2. LA CONFIGURACIÓN CRÍTICA PARA PRODUCCIÓN:
    model_config = SettingsConfigDict(
        env_file=".env",           # Para tu desarrollo local
        env_file_encoding="utf-8",
        extra="ignore"             # Evita que truene si hay variables extra en Railway
    )

settings = Settings()