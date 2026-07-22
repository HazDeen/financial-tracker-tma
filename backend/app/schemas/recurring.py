# backend/app/schemas/recurring.py
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.finance import TransactionType

class RecurringCreate(BaseModel):
    title: str = Field(..., max_length=128, description="Название подписки или регулярного дохода (например, 'Telegram Premium' или 'Аренда квартиры')")
    amount: Decimal = Field(..., gt=0, description="Сумма регулярной операции")
    transaction_type: TransactionType = Field(..., description="'income' для регулярного дохода, 'expense' для подписок и списаний")
    category: str = Field(..., max_length=64, description="Категория (например, 'Подписки' или 'Инвестиции')")
    billing_day: int = Field(..., ge=1, le=31, description="День месяца, когда происходит списание/начисление (1-31)")
    next_payment_date: date = Field(..., description="Ожидаемая дата следующего платежа")

class RecurringResponse(BaseModel):
    id: int
    user_id: int
    title: str
    amount: Decimal
    transaction_type: TransactionType
    category: str
    billing_day: int
    is_active: bool
    next_payment_date: date

    class Config:
        from_attributes = True