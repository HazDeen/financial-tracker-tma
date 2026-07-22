# backend/app/api/v1/endpoints/transactions.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.finance import Transaction, TransactionType
from app.services.hash_service import generate_transaction_hash
from app.schemas.analytics import TransactionDTO

router = APIRouter()

class TransactionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    transaction_type: str = Field(..., description="'income' или 'expense'")
    category: str = Field(...)
    transaction_date: datetime = Field(...)
    description: str = "Ручной ввод"

@router.post("/", response_model=TransactionDTO, status_code=status.HTTP_201_CREATED)
async def create_manual_transaction(
    schema: TransactionCreate,
    user_id: int = Query(1),
    db: AsyncSession = Depends(get_db)
):
    tx_type = TransactionType(schema.transaction_type)
    
    # Генерируем хэш, чтобы система не сломалась при совпадениях
    tx_hash = generate_transaction_hash(
        user_id=user_id,
        dt=schema.transaction_date,
        amount=schema.amount,
        currency="RUB",
        mcc_or_desc=schema.category + schema.description + str(datetime.now().timestamp()) # Соль для уникальности
    )
    
    new_tx = Transaction(
        user_id=user_id,
        amount=schema.amount,
        currency="RUB",
        transaction_type=tx_type,
        category=schema.category,
        description=schema.description,
        transaction_date=schema.transaction_date,
        hash_key=tx_hash
    )
    
    db.add(new_tx)
    await db.commit()
    await db.refresh(new_tx)
    
    return TransactionDTO(
        id=new_tx.id,
        amount=new_tx.amount,
        currency=new_tx.currency,
        transaction_type=new_tx.transaction_type.value,
        category=new_tx.category,
        description=new_tx.description,
        transaction_date=new_tx.transaction_date
    )