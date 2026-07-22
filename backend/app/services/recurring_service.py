# backend/app/services/recurring_service.py
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.finance import RecurringPayment
from app.schemas.recurring import RecurringCreate

class RecurringService:
    @staticmethod
    async def create_recurring(db: AsyncSession, user_id: int, schema: RecurringCreate) -> RecurringPayment:
        payment = RecurringPayment(
            user_id=user_id,
            title=schema.title,
            amount=schema.amount,
            transaction_type=schema.transaction_type,
            category=schema.category,
            billing_day=schema.billing_day,
            is_active=True,
            next_payment_date=schema.next_payment_date
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def get_user_recurring(db: AsyncSession, user_id: int, is_active: Optional[bool] = None) -> List[RecurringPayment]:
        query = select(RecurringPayment).where(RecurringPayment.user_id == user_id)
        if is_active is not None:
            query = query.where(RecurringPayment.is_active == is_active)
        query = query.order_by(RecurringPayment.next_payment_date.asc())
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def toggle_status(db: AsyncSession, user_id: int, recurring_id: int) -> RecurringPayment:
        """Включает или выключает (на паузу) регулярный платеж."""
        query = select(RecurringPayment).where(RecurringPayment.id == recurring_id, RecurringPayment.user_id == user_id)
        result = await db.execute(query)
        payment = result.scalar_one_or_none()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Рекуррентный платеж не найден.")

        payment.is_active = not payment.is_active
        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def delete_recurring(db: AsyncSession, user_id: int, recurring_id: int) -> bool:
        stmt = delete(RecurringPayment).where(RecurringPayment.id == recurring_id, RecurringPayment.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Запись не найдена.")
        return True