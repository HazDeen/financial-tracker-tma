# backend/app/api/v1/endpoints/debts.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.debt_service import DebtService
from app.schemas.debts import CreditDebtCreate, CreditDebtPayment, CreditDebtResponse

router = APIRouter()

@router.post("/", response_model=CreditDebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
    schema: CreditDebtCreate,
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую запись о кредите, ипотеке или долге."""
    return await DebtService.create_debt(db, user_id, schema)

@router.get("/", response_model=List[CreditDebtResponse], status_code=status.HTTP_200_OK)
async def get_debts(
    is_closed: Optional[bool] = Query(None, description="Фильтр: true - закрытые, false - активные"),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех кредитов и долгов пользователя."""
    return await DebtService.get_user_debts(db, user_id, is_closed)

@router.patch("/{debt_id}/pay", response_model=CreditDebtResponse, status_code=status.HTTP_200_OK)
async def pay_debt(
    schema: CreditDebtPayment,
    debt_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Внести платеж по кредиту. При достижении нулевого баланса долг автоматически закрывается."""
    return await DebtService.make_payment(db, user_id, debt_id, schema.amount)

@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(
    debt_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Удалить запись о долге."""
    await DebtService.delete_debt(db, user_id, debt_id)