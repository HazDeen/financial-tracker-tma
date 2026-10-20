import hashlib
import json
from collections import Counter
from datetime import timezone
from decimal import Decimal
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.models.finance import Transaction
from app.parsers.csv_parser import CSVParser
from app.parsers.pdf_parser import PDFParser
from app.schemas.statements import StatementUploadResponse


class StatementService:
    @staticmethod
    async def parse_upload(file: UploadFile):
        content = await file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Максимальный размер выписки — 10 МБ")
        filename = (file.filename or "").lower()
        if not content:
            raise HTTPException(422, "Файл пуст")
        try:
            if filename.endswith(".csv"):
                parsed = await run_in_threadpool(CSVParser.parse, content)
            elif filename.endswith(".pdf") and content.startswith(b"%PDF-"):
                parsed = await run_in_threadpool(PDFParser.parse, content)
            else:
                raise HTTPException(422, "Выберите CSV или PDF с текстовым слоем")
        except HTTPException:
            raise
        except Exception as exc:
            detail = str(exc) if isinstance(exc, ValueError) else "Не удалось прочитать выписку; проверьте файл или загрузите CSV"
            raise HTTPException(422, detail)
        if not parsed:
            raise HTTPException(422, "Операции не найдены. Скан PDF не поддерживается: загрузите CSV или PDF с текстовым слоем")
        if len(parsed) > 10000:
            raise HTTPException(422, "В файле больше 10 000 операций. Разделите выписку по месяцам")
        return parsed

    @staticmethod
    async def process_upload(db: AsyncSession, user_id: int, file: UploadFile) -> StatementUploadResponse:
        parsed_txs = await StatementService.parse_upload(file)
        # Точное содержимое и номер повторения сохраняют две одинаковые покупки.
        occurrences = Counter()
        payload = []
        for tx in parsed_txs:
            dt = tx.transaction_date
            dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            identity = json.dumps([user_id, dt.isoformat(), str(tx.amount.quantize(Decimal("0.01"))),
                                   tx.currency, tx.transaction_type, tx.description, tx.source_id], ensure_ascii=False)
            occurrences[identity] += 1
            tx_hash = hashlib.sha256(f"{identity}|{occurrences[identity]}".encode()).hexdigest()
            values = tx.model_dump(exclude={"source_id"})
            values.update(user_id=user_id, hash_key=tx_hash, transaction_date=dt)
            payload.append(values)
        if db.bind.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
        else:
            from sqlalchemy.dialects.postgresql import insert
        inserted_count = 0
        # Ограниченный размер батча для SQLite и PostgreSQL.
        for start in range(0, len(payload), 50):
            stmt = insert(Transaction).values(payload[start:start + 50]).on_conflict_do_nothing(index_elements=["user_id", "hash_key"])
            result = await db.execute(stmt)
            inserted_count += result.rowcount
        await db.commit()
        duplicate_count = len(parsed_txs) - inserted_count
        return StatementUploadResponse(status="success", filename=file.filename or "", total_parsed=len(parsed_txs),
            inserted=inserted_count, duplicates_ignored=duplicate_count,
            message=f"Добавлено операций: {inserted_count}. Уже были в учете: {duplicate_count}.")
