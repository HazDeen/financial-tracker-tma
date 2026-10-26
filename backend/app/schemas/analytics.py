# backend/app/schemas/analytics.py
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date

class CategorySummary(BaseModel):
    category: str = Field(..., description="Название категории")
    amount: Decimal = Field(..., description="Сумма")
    percentage: float = Field(0.0, description="Процент от общего")

class TopCategory(BaseModel):
    category: str
    amount: Decimal

class TransactionDTO(BaseModel):
    id: int
    amount: Decimal
    currency: str
    transaction_type: str
    category: str
    description: Optional[str]
    transaction_date: datetime
    
    class Config:
        from_attributes = True

class MonthlyReportResponse(BaseModel):
    year: int
    month: int
    total_income: Decimal = Field(default=Decimal("0.00"))
    total_expense: Decimal = Field(default=Decimal("0.00"))
    net_profit: Decimal = Field(default=Decimal("0.00"))
    
    top_expense_categories: List[TopCategory] = Field(default_factory=list)
    income_by_category: List[CategorySummary] = Field(default_factory=list)
    expense_by_category: List[CategorySummary] = Field(default_factory=list)
    transactions: List[TransactionDTO] = Field(default_factory=list, description="История всех транзакций за месяц")

class PeriodReportResponse(MonthlyReportResponse):
    start_date: date
    end_date: date
