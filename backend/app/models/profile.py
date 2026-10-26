from decimal import Decimal
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FinanceProfile(Base):
    __tablename__ = 'finance_profiles'
    user_id: Mapped[int] = mapped_column(primary_key=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal('0.00'))
