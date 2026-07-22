# backend/app/models/work.py
from datetime import date
from decimal import Decimal
from sqlalchemy import Numeric, Date, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class WorkShift(Base):
    __tablename__ = "work_shifts"
    __table_args__ = (
        Index("ix_work_shifts_user_date", "user_id", "shift_date", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours_worked: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_paid: Mapped[bool] = mapped_column(default=False)