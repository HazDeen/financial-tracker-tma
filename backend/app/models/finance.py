# backend/app/models/finance.py
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import (
    String, Numeric, DateTime, Date, Index, Boolean, Text, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Уникальный композитный индекс для защиты от дубликатов при импорте
        Index("ix_transactions_user_hash", "user_id", "hash_key", unique=True),
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    mcc_code: Mapped[Optional[str]] = mapped_column(String(4))
    description: Mapped[Optional[str]] = mapped_column(Text)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Хеш транзакции (генерацию напишем на следующем шаге)
    hash_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class RecurringPayment(Base):
    __tablename__ = "recurring_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    
    billing_day: Mapped[int] = mapped_column(nullable=False) # День месяца (1-31)
    is_active: Mapped[Boolean] = mapped_column(Boolean, default=True)
    next_payment_date: Mapped[date] = mapped_column(Date, nullable=False)

class CreditDebt(Base):
    __tablename__ = "credits_debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    is_closed: Mapped[Boolean] = mapped_column(Boolean, default=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)