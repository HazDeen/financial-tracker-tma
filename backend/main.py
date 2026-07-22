# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import router as api_router
from app.bot.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Запуск планировщика задач при старте приложения."""
    start_scheduler()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api")

# Настройка CORS для локальной разработки (React Vite по умолчанию на порту 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", tags=["System"])
async def health_check():
    """Проверка работоспособности сервиса."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "database_configured": bool(settings.DATABASE_URL)
    }