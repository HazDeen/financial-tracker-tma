# backend/app/parsers/pdf_parser.py
import io
import re
import pdfplumber
from datetime import datetime
from decimal import Decimal
from typing import List

from app.schemas.statements import ParsedTransactionDTO


class PDFParser:
    
    @staticmethod
    def _determine_category(description: str, mcc: str, amount: Decimal, tx_type: str) -> str:
        # 1. Поиск по MCC-коду (Высокий приоритет)
        if mcc:
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
            if mcc in mcc_map:
                return mcc_map[mcc]
                
        # 2. Фолбэк-поиск по ключевым словам в тексте
        desc_lower = description.lower()
        
        # --- НОВЫЕ КАТЕГОРИИ: Маркетплейсы и Я.Пэй ---
        if re.search(r'\bwb\b|wildberries|вайлдберриз|ozon|озон', desc_lower):
            return "Маркетплейсы"
        if "яндекс пэй" in desc_lower or "yandex pay" in desc_lower:
            return "Переводы (Яндекс Пэй)"
            
        # Остальные проверки
        if "систему быстрых платежей" in desc_lower or "перевод" in desc_lower:
            return "Переводы"
        if "cashback" in desc_lower or "программы лояльности" in desc_lower or "выплата" in desc_lower:
            return "Кэшбэк и бонусы"
        if "комиссия" in desc_lower or "уведомления" in desc_lower:
            return "Комиссии банка"
        if "яндекс" in desc_lower or "yandex" in desc_lower:
            return "Сервисы Яндекса"
        if any(kw in desc_lower for kw in ["pyaterochka", "пятерочка", "dixy", "lenta", "лента", "perekrestok", "перекресток", "krasnoe beloe", "gastronom", "magnit"]):
            return "Супермаркеты"
        if "delimobil" in desc_lower or "каршеринг" in desc_lower:
            return "Каршеринг"
        if "apteka" in desc_lower or "аптека" in desc_lower:
            return "Аптеки"
        if "winelab" in desc_lower or "aroma market" in desc_lower:
            return "Алкоголь"
        if "qr" in desc_lower:
            return "Оплата по QR"
            
        return "Пополнения" if tx_type == "income" else "Разное"
    
    @staticmethod
    def parse(content: bytes) -> List[ParsedTransactionDTO]:
        results = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                # Читаем текст "как видит человек"
                text = page.extract_text()
                if text:
                    full_text += text + " \n "
                    
        # Схлопываем переносы строк для защиты от разорванных ячеек
        clean_text = full_text.replace('\n', ' ')
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Рубим весь текст документа строго перед каждой датой (DD.MM.YYYY)
        chunks = re.split(r'(?=\b\d{2}\.\d{2}\.\d{4}\b)', clean_text)
        
        # Стоп-слова: всё, что является шапкой, подвалом или зависшим холдом
        skip_kws = [
            "входящий остаток", "исходящий остаток", "поступления", "расходы", 
            "текущий баланс", "платежный лимит", "неподтвержденные", "hold", 
            "за период", "выписка по счету", "дата открытия"
        ]
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
                
            # 1. Защита: чанк обязан начинаться с даты
            date_match = re.match(r'^(\d{2}\.\d{2}\.\d{4})', chunk)
            if not date_match:
                continue
                
            # 2. Фильтр мусора
            if any(kw in chunk.lower() for kw in skip_kws):
                continue
                
            # 3. Ищем сумму. В Альфе она идет в формате "X XXX,XX RUR" в конце блока
            amounts = re.findall(r'([-+]?\s*\d{1,3}(?:[ \xa0]\d{3})*(?:[.,]\d{2}))\s*(?:RUR|RUB)', chunk, re.IGNORECASE)
            
            if not amounts:
                continue
            
            # Берем самую последнюю найденную сумму (вдруг в описании попались цифры)
            raw_amount = amounts[-1].replace(" ", "").replace("\xa0", "").replace(",", ".")
            
            try:
                amount_val = Decimal(raw_amount)
                if amount_val == 0:
                    continue
                    
                tx_type = "income" if amount_val > 0 else "expense"
                abs_amount = abs(amount_val)
                
                tx_date = datetime.strptime(date_match.group(1), "%d.%m.%Y")
                
                # 4. Высчитываем описание (вырезаем из чанка дату и саму сумму)
                desc = chunk.replace(date_match.group(1), "", 1)
                desc = desc.replace(amounts[-1], "", 1)
                desc = re.sub(r'\b(RUR|RUB)\b', '', desc, flags=re.IGNORECASE).strip()
                
                # Парсим MCC код
                mcc_match = re.search(r'MCC\s*(\d{4})', desc, re.IGNORECASE)
                mcc_code = mcc_match.group(1) if mcc_match else None
                desc = re.sub(r'MCC\s*\d{4}', '', desc, flags=re.IGNORECASE).strip()
                
                if not desc:
                    desc = "Описание отсутствует"
                    
                category = PDFParser._determine_category(desc, mcc_code, abs_amount, tx_type)
                
                results.append(ParsedTransactionDTO(
                    amount=abs_amount,
                    currency="RUB",
                    transaction_type=tx_type,
                    category=category,
                    mcc_code=mcc_code,
                    description=desc[:150], # Обрезка под лимит БД
                    transaction_date=tx_date
                ))
            except Exception:
                continue
                
        return results