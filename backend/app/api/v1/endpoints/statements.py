from app.core.auth import get_current_user_id
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
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузка и парсинг выписок (CSV/PDF) со строгой кросс-файловой дедупликацией.
    """
    return await StatementService.process_upload(db=db, user_id=user_id, file=file)

@router.post("/preview")
async def preview_statement(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    transactions = await StatementService.parse_upload(file)
    from decimal import Decimal
    return {"total": len(transactions),
            "income": str(sum((tx.amount for tx in transactions if tx.transaction_type == "income"), Decimal(0))),
            "expense": str(sum((tx.amount for tx in transactions if tx.transaction_type == "expense"), Decimal(0))),
            "transactions": [tx.model_dump(exclude={"source_id"}) for tx in transactions[:20]]}
