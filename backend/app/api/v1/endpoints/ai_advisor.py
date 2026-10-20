from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/ai_advisor.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai_service import AIAdvisorService
from app.schemas.ai import AIAdvisorResponse

router = APIRouter()

@router.get("/analyze", response_model=AIAdvisorResponse, status_code=status.HTTP_200_OK)
async def analyze_monthly_finances(
    year: int = Query(..., ge=2000, le=2100, description="Год анализа"),
    month: int = Query(..., ge=1, le=12, description="Номер месяца (1-12)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Запускает гибридный анализ месячного бюджета через ИИ Gemini 2.5 Pro.
    Возвращает Markdown-инсайты и валидный JSON с параметрами виджетов для Telegram Mini App.
    """
    return await AIAdvisorService.get_monthly_advice(db, user_id, year, month)