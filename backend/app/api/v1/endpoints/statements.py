# backend/app/api/v1/endpoints/statements.py
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.statement_service import StatementService
from app.schemas.statements import StatementUploadResponse

router = APIRouter()

@router.post("/upload", response_model=StatementUploadResponse, status_code=status.HTTP_200_OK)
async def upload_statement(
    file: UploadFile = File(...),
    user_id: int = 1, # Временно хардкодим ID пользователя для тестов, позже подключим Telegram InitData
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузка и парсинг выписок (CSV/PDF) со строгой кросс-файловой дедупликацией.
    """
    return await StatementService.process_upload(db=db, user_id=user_id, file=file)