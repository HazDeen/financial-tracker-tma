# backend/app/bot/scheduler.py
import calendar
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.finance import Transaction
from app.core.config import settings # Импортируем настройки

# Безопасная инициализация бота
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else None

async def check_daily_and_weekly_activity():
    """Ежедневная проверка (например, в 20:00). Напоминает занести расходы."""
    if not bot:
        print("[Scheduler] Бот не настроен (TELEGRAM_BOT_TOKEN пуст). Пропуск рассылки.")
        return

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today_start - timedelta(days=7)
    
    async with AsyncSessionLocal() as db:
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()
        
        for user in users:
            tx_query = select(func.max(Transaction.transaction_date)).where(Transaction.user_id == user.telegram_id)
            tx_result = await db.execute(tx_query)
            last_tx_date = tx_result.scalar()
            
            if not last_tx_date:
                continue
                
            if last_tx_date < week_ago:
                await bot.send_message(
                    user.telegram_id, 
                    "👀 Мы скучаем! Вы уже целую неделю не вносили свои расходы. Зайдите в приложение, чтобы обновить статистику!"
                )
            elif last_tx_date < today_start:
                await bot.send_message(
                    user.telegram_id, 
                    "🌙 Добрый вечер! Не забудьте зафиксировать сегодняшние траты или доходы в трекере."
                )

async def check_end_of_month():
    """Проверка последнего дня месяца. Напоминает сгенерировать ИИ-отчет."""
    if not bot:
        return

    now = datetime.now(timezone.utc)
    _, last_day = calendar.monthrange(now.year, now.month)
    
    if now.day == last_day:
        async with AsyncSessionLocal() as db:
            users_result = await db.execute(select(User))
            for user in users_result.scalars().all():
                await bot.send_message(
                    user.telegram_id, 
                    f"📊 Месяц подходит к концу! Зайдите в приложение, чтобы получить персональный ИИ-анализ ваших финансов за {now.strftime('%B')} и поставить цели на следующий месяц."
                )

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    scheduler.add_job(check_daily_and_weekly_activity, 'cron', hour=20, minute=0)
    scheduler.add_job(check_end_of_month, 'cron', hour=10, minute=0)
    
    scheduler.start()