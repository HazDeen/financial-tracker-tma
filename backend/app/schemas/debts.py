# backend/app/schemas/debts.py
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class CreditDebtCreate(BaseModel):
    title: str = Field(..., max_length=128, description="Название кредита или долга (например, 'Ипотека' или 'Долг коллеге')")
    total_amount: Decimal = Field(..., gt=0, description="Изначальная общая сумма долга")
    current_balance: Decimal = Field(..., ge=0, description="Текущий остаток к выплате")
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="Годовая процентная ставка (%)")
    due_date: Optional[date] = Field(None, description="Дата окончательного погашения")

class CreditDebtPayment(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Сумма внесенного платежа в счет погашения")

class CreditDebtResponse(BaseModel):
    id: int
    user_id: int
    title: str
    total_amount: Decimal
    current_balance: Decimal
    interest_rate: Optional[Decimal]
    is_closed: bool
    due_date: Optional[date]

    class Config:
        from_attributes = True