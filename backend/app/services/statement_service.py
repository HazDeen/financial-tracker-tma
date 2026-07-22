# backend/app/services/statement_service.py
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from fastapi import UploadFile, HTTPException
from app.models.finance import Transaction
from app.services.hash_service import generate_transaction_hash
from app.parsers.csv_parser import CSVParser
from app.parsers.pdf_parser import PDFParser
from app.schemas.statements import StatementUploadResponse

class StatementService:
    @staticmethod
    async def process_upload(db: AsyncSession, user_id: int, file: UploadFile) -> StatementUploadResponse:
        content = await file.read()
        filename = file.filename.lower() if file.filename else "unknown"
        
        # 1. Роутинг парсера
        if filename.endswith(".csv"):
            parsed_txs = CSVParser.parse(content)
        elif filename.endswith(".pdf"):
            parsed_txs = PDFParser.parse(content)
        else:
            raise HTTPException(status_code=400, detail="Поддерживаются только форматы .csv и .pdf")

        total_parsed = len(parsed_txs)
        if total_parsed == 0:
            return StatementUploadResponse(
                status="warning",
                filename=file.filename or "",
                total_parsed=0,
                inserted=0,
                duplicates_ignored=0,
                message="Не удалось найти валидные транзакции в файле."
            )

        # 2. Подготовка батч-пейлоада с генерацией хешей
        insert_payload: List[Dict[str, Any]] = []
        for tx in parsed_txs:
            tx_hash = generate_transaction_hash(
                user_id=user_id,
                dt=tx.transaction_date,
                amount=tx.amount,
                currency=tx.currency,
                mcc_or_desc=tx.mcc_code or tx.description or tx.category
            )
            insert_payload.append({
                "user_id": user_id,
                "amount": tx.amount,
                "currency": tx.currency,
                "transaction_type": tx.transaction_type,
                "category": tx.category,
                "mcc_code": tx.mcc_code,
                "description": tx.description,
                "transaction_date": tx.transaction_date,
                "hash_key": tx_hash
            })

        # 3. PostgreSQL INSERT ... ON CONFLICT (user_id, hash_key) DO NOTHING
        stmt = insert(Transaction).values(insert_payload)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "hash_key"])
        
        result = await db.execute(stmt)
        await db.commit()
        
        inserted_count = result.rowcount
        duplicates_count = total_parsed - inserted_count
        
        return StatementUploadResponse(
            status="success",
            filename=file.filename or "",
            total_parsed=total_parsed,
            inserted=inserted_count,
            duplicates_ignored=duplicates_count,
            message=f"Успешно импортировано {inserted_count} транзакций. Пропущено дубликатов: {duplicates_count}."
        )