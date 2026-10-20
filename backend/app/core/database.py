# backend/app/core/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Инициализация асинхронного движка (echo=True полезен для дебага SQL-запросов в разработке)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Фабрика асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость (Dependency) для получения сессии БД в роутах FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()