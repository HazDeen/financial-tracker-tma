# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Finance TMA"
    DATABASE_URL: str
    GEMINI_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""

    # Чтение переменных из .env файла
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()