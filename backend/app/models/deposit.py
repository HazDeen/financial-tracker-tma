from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Deposit(Base):
    __tablename__ = 'deposits'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(128))
    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    months: Mapped[int]
    opened_on: Mapped[date] = mapped_column(Date)
    paid_months: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
