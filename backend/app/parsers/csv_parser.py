# backend/app/parsers/csv_parser.py
import io
import re
from typing import List
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
        import csv
        from decimal import InvalidOperation
        from dateutil.parser import parse as parse_date
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1251")
        lines = text.splitlines()
        header_index = next((i for i, line in enumerate(lines[:40])
                             if any(x in line.lower() for x in ["дата", "date"])
                             and any(x in line.lower() for x in ["сумм", "amount", "приход", "дебет"])), None)
        if header_index is None:
            raise ValueError("Не найдены заголовки с датой и суммой операции")
        delimiter = max([";", ",", "\t"], key=lines[header_index].count)
        reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])), delimiter=delimiter)
        columns = {str(c).strip().lower().replace("ё", "е"): c for c in reader.fieldnames or [] if c}

        def column(*names):
            return next((columns[name] for name in names if name in columns), None)

        date_col = column("дата операции", "дата совершения операции", "дата учета операции по счету", "operationdate", "date", "дата")
        amount_col = column("сумма платежа", "сумма в валюте счета", "сумма операции в валюте счета", "сумма операции", "amount", "сумма")
        income_col = column("приход", "кредит", "зачисление", "поступление")
        expense_col = column("расход", "дебет", "списание")
        if not date_col or not (amount_col or (income_col and expense_col)):
            raise ValueError("Нужны дата операции и сумма либо отдельные колонки прихода и расхода")
        currency_col = column("валюта платежа", "валюта счета", "currency", "валюта")
        if not currency_col and amount_col == column("сумма операции"):
            currency_col = column("валюта операции")
        desc_col = column("описание операции", "описание", "назначение платежа", "description", "comment")
        category_col = column("категория", "category")
        mcc_col = column("mcc", "mcc код", "mcc-код")
        type_col = column("тип", "type", "тип операции")
        status_col = column("статус", "status")
        reference_col = column("референс проводки", "id операции", "код авторизации", "reference")
        account_col = column("номер счета", "номер карты", "account")

        def money(value):
            clean = re.sub(r"[\s\u00a0\u202f₽]", "", value or "0").replace("−", "-").replace(",", ".")
            result = Decimal(clean)
            if not result.is_finite() or abs(result) >= Decimal("10000000000") or result.as_tuple().exponent < -2:
                raise ValueError("некорректная сумма")
            return result

        results = []
        for row_number, row in enumerate(reader, header_index + 2):
            if not any(value and str(value).strip() for value in row.values()):
                continue
            try:
                def val(key):
                    return (row.get(key) or "").strip() if key else ""
                if val(status_col).lower() not in {"", "ok", "выполнено", "исполнено", "успешно", "проведена"}:
                    continue
                # Служебные строки и второй локализованный заголовок Альфа-Бизнес.
                if val(date_col).lower() in {"дата операции", "дата учета операции по счету"}:
                    continue
                if income_col and expense_col:
                    incoming, outgoing = money(val(income_col)), money(val(expense_col))
                    if incoming < 0 or outgoing < 0 or (incoming and outgoing):
                        raise ValueError("неоднозначные приход и расход")
                    raw_amount = incoming - outgoing
                else:
                    raw_amount = money(val(amount_col))
                if not raw_amount:
                    continue
                tx_type = "income" if raw_amount > 0 else "expense"
                type_value = val(type_col).lower()
                if type_value in {"expense", "расход", "списание", "покупка"}:
                    tx_type = "expense"
                elif type_value in {"income", "приход", "пополнение", "зачисление"}:
                    tx_type = "income"
                currency = val(currency_col).upper() or "RUB"
                if currency in {"RUR", "643", "810", "₽", "РУБ", "РУБ."}:
                    currency = "RUB"
                if currency != "RUB":
                    raise ValueError("поддерживаются операции в рублях; выберите сумму в валюте рублевого счета")
                dt = parse_date(val(date_col), dayfirst=not bool(re.match(r"^\d{4}-", val(date_col))))
                desc = val(desc_col) or "Описание отсутствует"
                mcc = val(mcc_col)
                mcc = str(int(float(mcc))) if mcc else None
                if mcc and not re.fullmatch(r"\d{4}", mcc):
                    raise ValueError("некорректный MCC")
                results.append(ParsedTransactionDTO(
                    amount=abs(raw_amount), currency=currency, transaction_type=tx_type,
                    category=CSVParser._determine_category(desc, mcc or "", tx_type, val(category_col)),
                    mcc_code=mcc, description=desc, transaction_date=dt,
                    source_id="|".join([val(account_col), val(reference_col)])))
            except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
                raise ValueError(f"Строка {row_number}: {exc}. Файл не импортирован") from exc
        return results
