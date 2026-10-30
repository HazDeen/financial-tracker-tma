from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/analytics.py
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import MonthlyReportResponse, PeriodReportResponse

router = APIRouter()

@router.get("/monthly", response_model=MonthlyReportResponse, status_code=status.HTTP_200_OK)
async def get_monthly_analytics(
    year: int = Query(..., ge=2000, le=2100, description="Год (например, 2026)"),
    month: int = Query(..., ge=1, le=12, description="Номер месяца (1-12)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает агрегированный финансовый отчет за указанный месяц:
    - Общие суммы доходов, расходов и чистая прибыль.
    - Топ-3 самых затратных категорий.
    - Готовые срезы для независимой отрисовки графиков доходов и расходов.
    """
    return await AnalyticsService.get_monthly_report(
        db=db, 
        user_id=user_id, 
        year=year, 
        month=month
    )

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from app.models.finance import Transaction, TransactionType
from app.models.profile import FinanceProfile


class BalanceSettings(BaseModel):
    opening_balance: Decimal = Field(max_digits=12, decimal_places=2)


@router.get('/balance')
async def get_balance(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from app.services.deposit_service import sync_deposits
    await sync_deposits(db, user_id)
    profile = await db.get(FinanceProfile, user_id)
    opening = profile.opening_balance if profile else Decimal('0.00')
    rows = (await db.execute(select(Transaction.transaction_type, func.sum(Transaction.amount)).where(
        Transaction.user_id == user_id, Transaction.transaction_date <= datetime.now(timezone.utc)
    ).group_by(Transaction.transaction_type))).all()
    totals = dict(rows)
    balance = opening + totals.get(TransactionType.INCOME, Decimal('0')) - totals.get(TransactionType.EXPENSE, Decimal('0'))
    return {'opening_balance': str(opening), 'balance': str(balance)}


@router.put('/balance')
async def set_opening_balance(schema: BalanceSettings, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    profile = await db.get(FinanceProfile, user_id)
    if profile is None:
        profile = FinanceProfile(user_id=user_id)
        db.add(profile)
    profile.opening_balance = schema.opening_balance
    await db.commit()
    return await get_balance(user_id, db)


from datetime import date, time, timedelta


@router.get('/period', response_model=PeriodReportResponse)
async def get_period_analytics(start_date: date = Query(...), end_date: date = Query(...),
                               user_id: int = Depends(get_current_user_id),
                               db: AsyncSession = Depends(get_db)):
    if not (date(2000, 1, 1) <= start_date <= end_date <= date(2100, 12, 31)):
        raise HTTPException(422, 'Выберите период с 2000 по 2100 год. Дата окончания должна быть не раньше даты начала.')
    report = await AnalyticsService.get_period_report(
        db, user_id, datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc))
    return PeriodReportResponse(**report.model_dump(), start_date=start_date, end_date=end_date)
