from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    FRONTEND_URL: str
    BREVO_API_KEY: Optional[str] = None # Necesaria para el servicio de invitaciones

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings() # type: ignore