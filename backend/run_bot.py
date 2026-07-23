# backend/run_bot.py
import asyncio
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не задан!")
        return

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        # 1. Синхронизация пользователя с БД
        async with AsyncSessionLocal() as db:
            query = select(User).where(User.telegram_id == message.from_user.id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                # Если пользователя нет — создаем
                new_user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_active=datetime.now(timezone.utc)
                )
                db.add(new_user)
                await db.commit()
            else:
                # Если есть — обновляем данные и время последней активности
                user.username = message.from_user.username
                user.first_name = message.from_user.first_name
                user.last_active = datetime.now(timezone.utc)
                await db.commit()

        # 2. Формирование и отправка приветственного сообщения
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Открыть Smart Finance", 
                web_app=WebAppInfo(url="https://app.hazdeen.xyz")
            )]
        ])
        
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\n"
            "Это твой умный финансовый трекер.\n\n"
            "Нажми на кнопку ниже, чтобы запустить приложение.",
            reply_markup=kb
        )

    print("Бот запущен и слушает сообщения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())