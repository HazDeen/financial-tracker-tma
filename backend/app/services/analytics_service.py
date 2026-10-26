# backend/app/services/analytics_service.py
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import Transaction, TransactionType
from app.schemas.analytics import MonthlyReportResponse, CategorySummary, TopCategory, TransactionDTO

class AnalyticsService:
    @staticmethod
    def _get_month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
        """
        Рассчитывает строгие временные границы месяца в UTC.
        Использование операторов >= и < исключает баги с микросекундами в последний день месяца.
        """
        start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Определяем первый день следующего месяца
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            
        return start_date, end_date

    @classmethod
    async def get_monthly_report(
        cls, 
        db: AsyncSession, 
        user_id: int, 
        year: int, 
        month: int
    ) -> MonthlyReportResponse:
        start_date, end_date = cls._get_month_bounds(year, month)
        return await cls.get_period_report(db, user_id, start_date, end_date)

    @classmethod
    async def get_period_report(cls, db: AsyncSession, user_id: int,
                                start_date: datetime, end_date: datetime) -> MonthlyReportResponse:
        # Bounds are half-open: include the entire last selected day, never the next day.
        # 1. Запрос общих сумм доходов и расходов за месяц
        totals_query = select(
            Transaction.transaction_type,
            func.coalesce(func.sum(Transaction.amount), Decimal("0.00")).label("total")
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date
        ).group_by(Transaction.transaction_type)

        totals_result = await db.execute(totals_query)
        totals_map: Dict[TransactionType, Decimal] = {
            row.transaction_type: row.total for row in totals_result.all()
        }

        total_income = totals_map.get(TransactionType.INCOME, Decimal("0.00"))
        total_expense = totals_map.get(TransactionType.EXPENSE, Decimal("0.00"))
        net_profit = total_income - total_expense

        # 2. Запрос детализации по категориям (один запрос для доходов и расходов)
        categories_query = select(
            Transaction.transaction_type,
            Transaction.category,
            func.sum(Transaction.amount).label("category_total")
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date
        ).group_by(
            Transaction.transaction_type,
            Transaction.category
        ).order_by(
            Transaction.transaction_type,
            desc("category_total")
        )

        categories_result = await db.execute(categories_query)
        
        income_list: List[CategorySummary] = []
        expense_list: List[CategorySummary] = []
        top_expenses: List[TopCategory] = []

        for row in categories_result.all():
            cat_amount = row.category_total
            
            if row.transaction_type == TransactionType.INCOME:
                # Расчет процентной доли от общего дохода
                pct = float((cat_amount / total_income) * 100) if total_income > 0 else 0.0
                income_list.append(
                    CategorySummary(category=row.category, amount=cat_amount, percentage=round(pct, 1))
                )
            elif row.transaction_type == TransactionType.EXPENSE:
                # Расчет процентной доли от общих расходов
                pct = float((cat_amount / total_expense) * 100) if total_expense > 0 else 0.0
                summary_obj = CategorySummary(category=row.category, amount=cat_amount, percentage=round(pct, 1))
                expense_list.append(summary_obj)
                
                # Формируем Топ-3 расходов (так как SQL уже отсортировал по убыванию, берем первые 3)
                if len(top_expenses) < 3:
                    top_expenses.append(TopCategory(category=row.category, amount=cat_amount))

        tx_query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date < end_date
        ).order_by(desc(Transaction.transaction_date))
        
        tx_result = await db.execute(tx_query)
        raw_txs = tx_result.scalars().all()
        
        transactions_list = [
            TransactionDTO(
                id=tx.id,
                amount=tx.amount,
                currency=tx.currency,
                transaction_type=tx.transaction_type.value,
                category=tx.category,
                description=tx.description,
                transaction_date=tx.transaction_date
            ) for tx in raw_txs
        ]

        return MonthlyReportResponse(
            year=start_date.year,
            month=start_date.month,
            total_income=total_income,
            total_expense=total_expense,
            net_profit=net_profit,
            top_expense_categories=top_expenses,
            income_by_category=income_list,
            expense_by_category=expense_list,
            transactions=transactions_list # ДОБАВЛЕНО СЮДА
        )