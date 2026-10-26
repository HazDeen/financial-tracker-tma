from app.core.auth import get_current_user_id
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
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Создать ежемесячную подписку или регулярное начисление."""
    return await RecurringService.create_recurring(db, user_id, schema)

@router.get("/", response_model=List[RecurringResponse], status_code=status.HTTP_200_OK)
async def get_recurring(
    is_active: Optional[bool] = Query(None, description="Фильтр по активным/пассивным"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех рекуррентных платежей."""
    return await RecurringService.get_user_recurring(db, user_id, is_active)

@router.patch("/{recurring_id}/toggle", response_model=RecurringResponse, status_code=status.HTTP_200_OK)
async def toggle_recurring(
    recurring_id: int = Path(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Поставить подписку на паузу или возобновить её."""
    return await RecurringService.toggle_status(db, user_id, recurring_id)

@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: int = Path(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить рекуррентный платеж."""
    await RecurringService.delete_recurring(db, user_id, recurring_id)

from datetime import date, datetime, time, timezone
import calendar
from decimal import Decimal
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from app.models.finance import RecurringPayment, Transaction


@router.put('/{recurring_id}', response_model=RecurringResponse)
async def edit_recurring(recurring_id: int, schema: RecurringCreate,
                         user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(RecurringPayment).where(
        RecurringPayment.id == recurring_id, RecurringPayment.user_id == user_id).with_for_update())).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, 'Запись расписания не найдена')
    for key, value in schema.model_dump().items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return row


class ConfirmOccurrence(BaseModel):
    due_date: date
    transaction_date: date


@router.post('/{recurring_id}/confirm')
async def confirm_recurring(recurring_id: int, schema: ConfirmOccurrence,
                            user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(RecurringPayment).where(
        RecurringPayment.id == recurring_id, RecurringPayment.user_id == user_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, 'Запись расписания не найдена')
    if not row.is_active or row.next_payment_date != schema.due_date:
        raise HTTPException(409, 'Этот платёж уже подтверждён или расписание изменилось. Обновите страницу.')
    next_month = schema.due_date.month % 12 + 1
    next_year = schema.due_date.year + (schema.due_date.month == 12)
    next_date = date(next_year, next_month, min(row.billing_day, calendar.monthrange(next_year, next_month)[1]))
    changed = await db.execute(update(RecurringPayment).where(
        RecurringPayment.id == recurring_id, RecurringPayment.user_id == user_id,
        RecurringPayment.next_payment_date == schema.due_date, RecurringPayment.is_active.is_(True)
    ).values(next_payment_date=next_date))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, 'Этот платёж уже подтверждён. Обновите страницу.')
    tx = Transaction(user_id=user_id, amount=row.amount, currency='RUB', transaction_type=row.transaction_type,
                     category=row.category, description=row.title,
                     transaction_date=datetime.combine(schema.transaction_date, time(0), tzinfo=timezone.utc),
                     hash_key=f'recurring:{recurring_id}:{schema.due_date.isoformat()}')
    db.add(tx)
    await db.commit()
    return {'message': 'Операция добавлена', 'next_payment_date': next_date.isoformat()}
