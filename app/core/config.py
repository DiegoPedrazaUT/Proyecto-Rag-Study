import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL") or ""
    SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY") or ""

    class Config:
        env_file = ".env"

settings = Settings()