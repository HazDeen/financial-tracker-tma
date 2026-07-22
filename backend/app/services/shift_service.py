# backend/app/services/shift_service.py
import calendar
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from fastapi import HTTPException

from app.models.work import WorkShift
from app.models.finance import Transaction, TransactionType
from app.schemas.shifts import WorkShiftCreate, SalarySummaryResponse, WorkShiftResponse
from app.services.hash_service import generate_transaction_hash

class ShiftService:
    @staticmethod
    async def log_shift(db: AsyncSession, user_id: int, schema: WorkShiftCreate) -> WorkShiftResponse:
        """Логирует отработанную смену (UPSERT)."""
        total = round(schema.hours_worked * schema.hourly_rate, 2)
        
        stmt = insert(WorkShift).values(
            user_id=user_id,
            shift_date=schema.shift_date,
            hours_worked=schema.hours_worked,
            hourly_rate=schema.hourly_rate,
            total_earned=total,
            is_paid=False
        )
        
        # Если смена в этот день уже есть — обновляем
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "shift_date"],
            set_=dict(
                hours_worked=schema.hours_worked,
                hourly_rate=schema.hourly_rate,
                total_earned=total
            )
        ).returning(WorkShift)
        
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()

    @staticmethod
    async def get_monthly_summary(db: AsyncSession, user_id: int, year: int, month: int) -> SalarySummaryResponse:
        """Возвращает сводку по сменам за месяц."""
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)
        
        query = select(WorkShift).where(
            WorkShift.user_id == user_id,
            WorkShift.shift_date >= start_date,
            WorkShift.shift_date <= end_date
        ).order_by(WorkShift.shift_date.desc())
        
        result = await db.execute(query)
        shifts = result.scalars().all()
        
        total_hours = sum((s.hours_worked for s in shifts), Decimal("0.00"))
        total_earned = sum((s.total_earned for s in shifts), Decimal("0.00"))
        total_paid = sum((s.total_earned for s in shifts if s.is_paid), Decimal("0.00"))
        unpaid_balance = total_earned - total_paid
        
        return SalarySummaryResponse(
            year=year,
            month=month,
            total_shifts=len(shifts),
            total_hours=total_hours,
            total_earned=total_earned,
            total_paid=total_paid,
            unpaid_balance=unpaid_balance,
            shifts=[WorkShiftResponse.model_validate(s) for s in shifts]
        )

    @staticmethod
    async def mark_shift_as_paid(db: AsyncSession, user_id: int, shift_id: int) -> WorkShiftResponse:
        """Отмечает смену как оплаченную и автоматически закидывает деньги на баланс."""
        query = select(WorkShift).where(
            WorkShift.id == shift_id,
            WorkShift.user_id == user_id
        )
        result = await db.execute(query)
        shift = result.scalar_one_or_none()
        
        if not shift:
            raise HTTPException(status_code=404, detail="Смена не найдена")
            
        if shift.is_paid:
            return shift # Если уже оплачена — игнорируем
            
        # 1. Отмечаем смену как оплаченную
        shift.is_paid = True
        
        # 2. Формируем транзакцию дохода
        tx_date = datetime.now()
        tx_hash = generate_transaction_hash(
            user_id=user_id,
            dt=tx_date,
            amount=shift.total_earned,
            currency="RUB",
            mcc_or_desc=f"Зарплата смена {shift.shift_date}"
        )
        
        new_tx = Transaction(
            user_id=user_id,
            amount=shift.total_earned,
            currency="RUB",
            transaction_type=TransactionType.INCOME,
            category="Зарплата",
            description=f"Оплата за рабочую смену ({shift.shift_date.strftime('%d.%m.%Y')})",
            transaction_date=tx_date,
            hash_key=tx_hash
        )
        
        # Записываем изменения в БД одним коммитом
        db.add(new_tx)
        await db.commit()
        await db.refresh(shift)
        
        return shift

    @staticmethod
    async def delete_shift(db: AsyncSession, user_id: int, shift_id: int) -> bool:
        """Удаляет смену."""
        stmt = delete(WorkShift).where(
            WorkShift.id == shift_id,
            WorkShift.user_id == user_id
        )
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Смена не найдена")
        return True