from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.deposit import Deposit
from app.services.deposit_service import monthly_income, payment_date, sync_deposits, today

router = APIRouter()


class DepositCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=128, pattern=r'.*\S.*')
    principal: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    annual_rate: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)
    months: int = Field(ge=1, le=600)
    opened_on: date = Field(ge=date(2000, 1, 1), le=date(2100, 12, 31))


def summary(row):
    monthly = monthly_income(row)
    return {'id': row.id, 'title': row.title, 'principal': str(row.principal), 'annual_rate': str(row.annual_rate),
            'months': row.months, 'opened_on': row.opened_on, 'is_active': row.is_active,
            'monthly_income': str(monthly), 'accrued_income': str(monthly * row.paid_months),
            'next_payment_date': payment_date(row, row.paid_months + 1) if row.is_active and row.paid_months < row.months else None,
            'ends_on': payment_date(row, row.months)}


@router.get('')
async def list_deposits(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    await sync_deposits(db, user_id)
    db.expire_all()
    rows = (await db.scalars(select(Deposit).where(Deposit.user_id == user_id).order_by(Deposit.id.desc()))).all()
    return [summary(row) for row in rows]


@router.post('', status_code=201)
async def create_deposit(schema: DepositCreate, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    if schema.opened_on > today():
        raise HTTPException(422, 'Дата открытия не может быть в будущем')
    row = Deposit(user_id=user_id, **schema.model_dump())
    if monthly_income(row) <= 0:
        raise HTTPException(422, 'Ежемесячный доход должен быть не меньше 0,01 ₽')
    db.add(row)
    await db.commit()
    await sync_deposits(db, user_id)
    await db.refresh(row)
    return summary(row)


@router.post('/{deposit_id}/close')
async def close_deposit(deposit_id: int, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    await sync_deposits(db, user_id)
    row = await db.scalar(select(Deposit).where(Deposit.id == deposit_id, Deposit.user_id == user_id).with_for_update())
    if row is None:
        raise HTTPException(404, 'Вклад не найден')
    row.is_active = False
    await db.commit()
    await db.refresh(row)
    return summary(row)
