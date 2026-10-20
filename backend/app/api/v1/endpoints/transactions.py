from app.core.auth import get_current_user_id
# backend/app/api/v1/endpoints/transactions.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import uuid4
from decimal import Decimal
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.finance import Transaction, TransactionType
from app.schemas.analytics import TransactionDTO

router = APIRouter()

class TransactionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    transaction_type: TransactionType
    category: str = Field(..., min_length=1, max_length=64, pattern=r".*\S.*")
    transaction_date: datetime = Field(...)
    description: str = Field("Ручной ввод", max_length=2000)

@router.post("/", response_model=TransactionDTO, status_code=status.HTTP_201_CREATED)
async def create_manual_transaction(
    schema: TransactionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    tx_type = TransactionType(schema.transaction_type)
    
    tx_hash = uuid4().hex
    if schema.transaction_date.tzinfo is None:
        schema.transaction_date = schema.transaction_date.replace(tzinfo=timezone.utc)

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

@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(transaction_id: int, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    from sqlalchemy import select
    tx = (await db.execute(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id))).scalar_one_or_none()
    if tx is None:
        raise HTTPException(404, "Операция не найдена")
    await db.delete(tx)
    await db.commit()


@router.put("/{transaction_id}", response_model=TransactionDTO)
async def update_transaction(transaction_id: int, schema: TransactionCreate, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    from sqlalchemy import select
    tx = (await db.execute(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id))).scalar_one_or_none()
    if tx is None:
        raise HTTPException(404, "Операция не найдена")
    if schema.transaction_date.tzinfo is None:
        schema.transaction_date = schema.transaction_date.replace(tzinfo=timezone.utc)
    for field, value in schema.model_dump().items():
        setattr(tx, field, value)
    await db.commit()
    await db.refresh(tx)
    return TransactionDTO.model_validate(tx)
