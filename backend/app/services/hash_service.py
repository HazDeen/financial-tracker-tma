# backend/app/services/hash_service.py
import hashlib
import re
from datetime import datetime
from decimal import Decimal

def generate_transaction_hash(
    user_id: int, 
    dt: datetime, 
    amount: Decimal, 
    currency: str, 
    mcc_or_desc: str
) -> str:
    """
    Генерирует SHA-256 хеш транзакции для защиты от дубликатов (Идемпотентность).
    Специально сделан "мягким" (только дата, сумма и первые 2 слова описания),
    чтобы не плодить дубли, если банк поменяет точное время или концовку описания
    при переходе статуса из "В обработке" в "Выполнено".
    """
    # 1. Берем только дату (игнорируем часы и минуты)
    normalized_date = dt.strftime("%Y-%m-%d")
    
    # 2. Нормализуем сумму до копеек (например, 150.0 -> "150.00")
    normalized_amount = f"{Decimal(str(amount)):.2f}"
    
    # 3. Очищаем описание от спецсимволов и берем только первые 2 слова
    # Если передается MCC, это будет просто 4 цифры
    clean_desc = re.sub(r'[^\w\s]', '', mcc_or_desc.lower())
    words = clean_desc.split()
    short_desc = "".join(words[:2]) if words else "unknown"
    
    # 4. Формируем сырую строку и хешируем
    raw_payload = f"{user_id}_{normalized_date}_{normalized_amount}_{currency}_{short_desc}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()