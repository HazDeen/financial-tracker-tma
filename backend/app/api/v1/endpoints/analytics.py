from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/analytics.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import MonthlyReportResponse

router = APIRouter()

@router.get("/monthly", response_model=MonthlyReportResponse, status_code=status.HTTP_200_OK)
async def get_monthly_analytics(
    year: int = Query(..., ge=2000, le=2100, description="Год (например, 2026)"),
    month: int = Query(..., ge=1, le=12, description="Номер месяца (1-12)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает агрегированный финансовый отчет за указанный месяц:
    - Общие суммы доходов, расходов и чистая прибыль.
    - Топ-3 самых затратных категорий.
    - Готовые срезы для независимой отрисовки графиков доходов и расходов.
    """
    return await AnalyticsService.get_monthly_report(
        db=db, 
        user_id=user_id, 
        year=year, 
        month=month
    )