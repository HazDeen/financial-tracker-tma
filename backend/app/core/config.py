# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Finance TMA"
    DATABASE_URL: str = "sqlite+aiosqlite:///./finance.db"
    COOKIE_SECURE: bool = False
    ENABLE_TELEGRAM_SCHEDULER: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    GEMINI_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""

    # Чтение переменных из .env файла
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()