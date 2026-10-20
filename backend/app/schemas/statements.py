# backend/app/schemas/statements.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ParsedTransactionDTO(BaseModel):
    amount: Decimal = Field(..., description="Абсолютная сумма транзакции")
    currency: str = Field(default="RUB", max_length=3)
    transaction_type: str = Field(..., description="'income' или 'expense'")
    category: str = Field(default="Разное")
    mcc_code: Optional[str] = Field(default=None, max_length=4)
    description: Optional[str] = None
    source_id: str = ""
    transaction_date: datetime

class StatementUploadResponse(BaseModel):
    status: str
    filename: str
    total_parsed: int
    inserted: int
    duplicates_ignored: int
    message: str