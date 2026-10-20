from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/actions.py
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.services.shift_service import ShiftService
from app.services.debt_service import DebtService
from app.schemas.shifts import WorkShiftResponse
from app.schemas.debts import CreditDebtResponse
from pydantic import BaseModel, Field

router = APIRouter()

class PayDebtRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма платежа")

# --- Реальная оплата смены ---
@router.post("/shifts/{shift_id}/pay", response_model=WorkShiftResponse, status_code=status.HTTP_200_OK)
async def mark_shift_as_paid(
    shift_id: int = Path(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Отмечает смену как оплаченную в реальной БД и пересчитывает баланс."""
    return await ShiftService.mark_shift_as_paid(db, user_id, shift_id)

# --- Реальный платеж по долгу/кредиту ---
@router.post("/debts/{debt_id}/pay", response_model=CreditDebtResponse, status_code=status.HTTP_200_OK)
async def pay_debt_installment(
    payload: PayDebtRequest,
    debt_id: int = Path(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Вносит платеж по долгу в реальную БД."""
    from decimal import Decimal
    return await DebtService.make_payment(db, user_id, debt_id, Decimal(str(payload.amount)))