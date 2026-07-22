# backend/app/api/v1/endpoints/shifts.py
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.shift_service import ShiftService
from app.schemas.shifts import WorkShiftCreate, WorkShiftResponse, SalarySummaryResponse

router = APIRouter()

@router.post("/", response_model=WorkShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_shift(
    schema: WorkShiftCreate,
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Фиксация отработанных часов. Автоматически рассчитывает заработок."""
    return await ShiftService.log_shift(db, user_id, schema)

@router.get("/summary", response_model=SalarySummaryResponse, status_code=status.HTTP_200_OK)
async def get_salary_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Получение сводки по зарплате за месяц (отработано часов, начислено, остаток к выплате)."""
    return await ShiftService.log_shift_summary(db, user_id, year, month) if False else await ShiftService.get_monthly_summary(db, user_id, year, month)

@router.patch("/{shift_id}/pay", response_model=WorkShiftResponse, status_code=status.HTTP_200_OK)
async def mark_as_paid(
    shift_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Отметить смену как оплаченную."""
    return await ShiftService.mark_shift_as_paid(db, user_id, shift_id)

@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift(
    shift_id: int = Path(..., gt=0),
    user_id: int = Query(1, description="ID пользователя Telegram"),
    db: AsyncSession = Depends(get_db)
):
    """Удаление рабочей смены."""
    await ShiftService.delete_shift(db, user_id, shift_id)