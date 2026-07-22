# backend/app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

class UserSync(BaseModel):
    id: int
    # Используем Optional вместо синтаксиса Python 3.10
    username: Optional[str] = None
    first_name: Optional[str] = None

@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_user(user_data: UserSync, db: AsyncSession = Depends(get_db)):
    # Ищем пользователя в базе
    query = select(User).where(User.telegram_id == user_data.id)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    is_new = False
    
    if not existing_user:
        # Пользователь зашел впервые
        is_new = True
        new_user = User(
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            last_active=datetime.now(timezone.utc)
        )
        db.add(new_user)
    else:
        # Пользователь уже существует, обновляем активность
        existing_user.username = user_data.username
        existing_user.first_name = user_data.first_name
        existing_user.last_active = datetime.now(timezone.utc)
        
    await db.commit()
    
    # Считаем общее количество пользователей для красивого приветствия
    count_query = select(func.count(User.telegram_id))
    total_users = (await db.execute(count_query)).scalar()
    
    return {
        "status": "synced",
        "is_new": is_new,
        "total_users": total_users,
        "first_name": user_data.first_name or "Пользователь"
    }