from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/ai_advisor.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai_service import AIAdvisorService
from app.schemas.ai import AIAdvisorResponse, AdvisorChatRequest

router = APIRouter()

@router.get("/analyze", response_model=AIAdvisorResponse, status_code=status.HTTP_200_OK)
async def analyze_monthly_finances(
    year: int = Query(..., ge=2000, le=2100, description="Год анализа"),
    month: int = Query(..., ge=1, le=12, description="Номер месяца (1-12)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Совместимый месячный разбор: проверенные карточки и пояснение."""
    return await AIAdvisorService.get_monthly_advice(db, user_id, year, month)


@router.post("/chat", response_model=AIAdvisorResponse)
async def chat_about_finances(
    request: AdvisorChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await AIAdvisorService.chat(db, user_id, request)
