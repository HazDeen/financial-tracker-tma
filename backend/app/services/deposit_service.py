"""Accrue monthly payouts once. Principal is an asset, never an income transaction."""
import calendar
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from app.models.deposit import Deposit
from app.models.finance import Transaction, TransactionType


def today():
    return datetime.now(ZoneInfo('Europe/Moscow')).date()


def payment_date(row, month):
    offset = row.opened_on.year * 12 + row.opened_on.month - 1 + month
    year, zero_month = divmod(offset, 12)
    return date(year, zero_month + 1, min(row.opened_on.day, calendar.monthrange(year, zero_month + 1)[1]))


def monthly_income(row):
    return (row.principal * row.annual_rate / Decimal(1200)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


async def sync_deposits(db, user_id):
    rows = (await db.scalars(select(Deposit).where(Deposit.user_id == user_id, Deposit.is_active.is_(True))
                             .order_by(Deposit.id).with_for_update())).all()
    for row in rows:
        cursor = row.paid_months
        while cursor < row.months and payment_date(row, cursor + 1) <= today():
            changed = await db.execute(update(Deposit).where(Deposit.id == row.id, Deposit.paid_months == cursor,
                                                            Deposit.is_active.is_(True))
                                       .values(paid_months=cursor + 1).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                break
            due = payment_date(row, cursor + 1)
            db.add(Transaction(user_id=user_id, amount=monthly_income(row), currency='RUB',
                               transaction_type=TransactionType.INCOME, category='Проценты по вкладам',
                               description=f'Проценты по вкладу «{row.title}»',
                               transaction_date=datetime.combine(due, time.min, tzinfo=timezone.utc),
                               hash_key=f'deposit:{row.id}:{cursor + 1}'))
            cursor += 1
    await db.commit()
