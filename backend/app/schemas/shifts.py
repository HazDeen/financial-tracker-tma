# backend/app/schemas/shifts.py
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List

class WorkShiftCreate(BaseModel):
    shift_date: date = Field(..., description="Дата рабочей смены")
    hours_worked: Decimal = Field(..., gt=0, le=24, description="Количество отработанных часов")
    hourly_rate: Decimal = Field(..., gt=0, description="Часовая ставка в рублях")

class WorkShiftResponse(BaseModel):
    id: int
    user_id: int
    shift_date: date
    hours_worked: Decimal
    hourly_rate: Decimal
    total_earned: Decimal
    is_paid: bool

    class Config:
        from_attributes = True

class SalarySummaryResponse(BaseModel):
    """Сводный отчет по зарплате за месяц."""
    year: int
    month: int
    total_shifts: int = Field(0, description="Всего отработано смен")
    total_hours: Decimal = Field(Decimal("0.00"), description="Общие отработанные часы")
    total_earned: Decimal = Field(Decimal("0.00"), description="Всего начислено")
    total_paid: Decimal = Field(Decimal("0.00"), description="Уже выплачено")
    unpaid_balance: Decimal = Field(Decimal("0.00"), description="Остаток к выплате")
    shifts: List[WorkShiftResponse] = []