# backend/app/services/debt_service.py
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.finance import CreditDebt
from app.schemas.debts import CreditDebtCreate

class DebtService:
    @staticmethod
    async def create_debt(db: AsyncSession, user_id: int, schema: CreditDebtCreate) -> CreditDebt:
        debt = CreditDebt(
            user_id=user_id,
            title=schema.title,
            total_amount=schema.total_amount,
            current_balance=schema.current_balance,
            interest_rate=schema.interest_rate,
            is_closed=(schema.current_balance <= 0),
            due_date=schema.due_date
        )
        db.add(debt)
        await db.commit()
        await db.refresh(debt)
        return debt

    @staticmethod
    async def get_user_debts(db: AsyncSession, user_id: int, is_closed: Optional[bool] = None) -> List[CreditDebt]:
        query = select(CreditDebt).where(CreditDebt.user_id == user_id)
        if is_closed is not None:
            query = query.where(CreditDebt.is_closed == is_closed)
        query = query.order_by(CreditDebt.is_closed.asc(), CreditDebt.id.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def make_payment(db: AsyncSession, user_id: int, debt_id: int, payment_amount: Decimal) -> CreditDebt:
        query = select(CreditDebt).where(CreditDebt.id == debt_id, CreditDebt.user_id == user_id)
        result = await db.execute(query)
        debt = result.scalar_one_or_none()
        
        if not debt:
            raise HTTPException(status_code=404, detail="Кредит или долг не найден.")
        if debt.is_closed:
            raise HTTPException(status_code=400, detail="Этот долг уже полностью закрыт.")

        # Уменьшаем баланс и проверяем закрытие
        new_balance = debt.current_balance - payment_amount
        if new_balance <= 0:
            debt.current_balance = Decimal("0.00")
            debt.is_closed = True
        else:
            debt.current_balance = new_balance

        await db.commit()
        await db.refresh(debt)
        return debt

    @staticmethod
    async def delete_debt(db: AsyncSession, user_id: int, debt_id: int) -> bool:
        stmt = delete(CreditDebt).where(CreditDebt.id == debt_id, CreditDebt.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Запись не найдена.")
        return True