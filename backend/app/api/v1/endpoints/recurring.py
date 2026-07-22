# backend/app/api/v1/endpoints/recurring.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.recurring_service import RecurringService
from app.schemas.recurring import RecurringCreate, RecurringResponse

router = APIRouter()

@router.post("/", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    schema: RecurringCreate,
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Создать ежемесячную подписку или регулярное начисление."""
    return await RecurringService.create_recurring(db, user_id, schema)

@router.get("/", response_model=List[RecurringResponse], status_code=status.HTTP_200_OK)
async def get_recurring(
    is_active: Optional[bool] = Query(None, description="Фильтр по активным/пассивным"),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех рекуррентных платежей."""
    return await RecurringService.get_user_recurring(db, user_id, is_active)

@router.patch("/{recurring_id}/toggle", response_model=RecurringResponse, status_code=status.HTTP_200_OK)
async def toggle_recurring(
    recurring_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Поставить подписку на паузу или возобновить её."""
    return await RecurringService.toggle_status(db, user_id, recurring_id)

@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Удалить рекуррентный платеж."""
    await RecurringService.delete_recurring(db, user_id, recurring_id)