# backend/app/parsers/csv_parser.py
import io
import re
import pandas as pd
from typing import List
from datetime import datetime
from decimal import Decimal
from app.schemas.statements import ParsedTransactionDTO

class CSVParser:
    @staticmethod
    def _determine_category(description: str, mcc: str, tx_type: str, bank_category: str) -> str:
        # 1. Поиск по MCC-коду (Высокий приоритет)
        if mcc and str(mcc).strip() != "nan" and str(mcc).strip() != "0":
            try:
                mcc_str = str(int(float(mcc)))
                mcc_map = {
                    "5411": "Супермаркеты",
                    "5499": "Продукты",
                    "5814": "Фастфуд и Кафе",
                    "5812": "Рестораны",
                    "5813": "Бары",
                    "5921": "Алкоголь",
                    "5992": "Цветы",
                    "5912": "Аптеки",
                    "4111": "Транспорт",
                    "7512": "Каршеринг",
                    "3990": "Сервисы Яндекса",
                }
                if mcc_str in mcc_map:
                    return mcc_map[mcc_str]
            except Exception:
                pass
                
        # 2. Фолбэк-поиск по ключевым словам в тексте
        desc_lower = description.lower()
        
        # Маркетплейсы и Я.Пэй
        if re.search(r'\bwb\b|wildberries|вайлдберриз|ozon|озон', desc_lower):
            return "Маркетплейсы"
        if "яндекс пэй" in desc_lower or "yandex pay" in desc_lower:
            return "Переводы (Яндекс Пэй)"
            
        # Основные категории
        if "систему быстрых платежей" in desc_lower or "перевод" in desc_lower or "сбп" in desc_lower:
            return "Переводы"
        if "cashback" in desc_lower or "программы лояльности" in desc_lower or "выплата" in desc_lower or "кэшбэк" in desc_lower:
            return "Кэшбэк и бонусы"
        if "комиссия" in desc_lower or "уведомления" in desc_lower:
            return "Комиссии банка"
        if "яндекс" in desc_lower or "yandex" in desc_lower:
            return "Сервисы Яндекса"
        if any(kw in desc_lower for kw in ["pyaterochka", "пятерочка", "dixy", "lenta", "лента", "perekrestok", "перекресток", "krasnoe beloe", "gastronom", "magnit", "магнит"]):
            return "Супермаркеты"
        if "delimobil" in desc_lower or "каршеринг" in desc_lower or "делимобиль" in desc_lower:
            return "Каршеринг"
        if "apteka" in desc_lower or "аптека" in desc_lower:
            return "Аптеки"
        if "winelab" in desc_lower or "aroma market" in desc_lower:
            return "Алкоголь"
        if "qr" in desc_lower:
            return "Оплата по QR"
            
        # 3. Если ничего не подошло, но банк дал адекватную категорию
        if bank_category and str(bank_category).strip() not in ["nan", "", "None", "Разное"]:
            return str(bank_category).strip()
            
        return "Пополнения" if tx_type == "income" else "Разное"

    @staticmethod
    def parse(content: bytes) -> List[ParsedTransactionDTO]:
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8')
            if len(df.columns) == 1:
                df = pd.read_csv(io.BytesIO(content), sep=',', encoding='utf-8-sig')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(io.BytesIO(content), sep=';', encoding='cp1251')
                if len(df.columns) == 1:
                    df = pd.read_csv(io.BytesIO(content), sep=',', encoding='cp1251')
            except Exception:
                return []
                
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        col_map = {
            "date": next((c for c in df.columns if "operationdate" in c or "дат" in c or "date" in c), None),
            "amount": next((c for c in df.columns if "сумм" in c or "amount" in c), None),
            "category": next((c for c in df.columns if "катег" in c or "category" in c), None),
            "mcc": next((c for c in df.columns if "mcc" in c), None),
            "merchant": next((c for c in df.columns if "merchant" in c or "контрагент" in c), None),
            "comment": next((c for c in df.columns if "опис" in c or "назван" in c or "comment" in c or "desc" in c), None),
            "type": next((c for c in df.columns if "type" in c or "тип" in c), None),
        }
        
        if not col_map["date"] or not col_map["amount"]:
            return []
            
        results = []
        for _, row in df.iterrows():
            try:
                amount_str = str(row[col_map["amount"]]).replace(",", ".").replace(" ", "").replace("\xa0", "")
                raw_amount = Decimal(amount_str)
                if raw_amount == 0:
                    continue
                
                tx_type = "expense"
                if col_map["type"] and pd.notna(row[col_map["type"]]):
                    type_val = str(row[col_map["type"]]).lower()
                    if "пополнение" in type_val or "income" in type_val or "приход" in type_val:
                        tx_type = "income"
                elif raw_amount > 0:
                    tx_type = "income"
                else:
                    tx_type = "expense"
                    
                abs_amount = abs(raw_amount)
                tx_date = pd.to_datetime(row[col_map["date"]], dayfirst=True).to_pydatetime()
                
                desc_parts = []
                if col_map["merchant"] and pd.notna(row[col_map["merchant"]]):
                    desc_parts.append(str(row[col_map["merchant"]]).strip())
                if col_map["comment"] and pd.notna(row[col_map["comment"]]):
                    desc_parts.append(str(row[col_map["comment"]]).strip())
                
                full_desc = " ".join(desc_parts) if desc_parts else "Описание отсутствует"
                
                mcc_val = str(row[col_map["mcc"]]) if col_map["mcc"] and pd.notna(row[col_map["mcc"]]) else ""
                bank_cat = str(row[col_map["category"]]) if col_map["category"] and pd.notna(row[col_map["category"]]) else ""
                
                category = CSVParser._determine_category(full_desc, mcc_val, tx_type, bank_cat)
                
                mcc_formatted = None
                if mcc_val and mcc_val not in ["nan", "0"]:
                    mcc_formatted = str(int(float(mcc_val)))
                
                results.append(ParsedTransactionDTO(
                    amount=abs_amount,
                    currency="RUB",
                    transaction_type=tx_type,
                    category=category,
                    mcc_code=mcc_formatted,
                    description=full_desc[:150],
                    transaction_date=tx_date
                ))
            except (ValueError, KeyError, TypeError):
                continue
                
        return results