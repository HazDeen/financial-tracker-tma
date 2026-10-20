"""Text-based card statements. Ambiguous/unsupported layouts are rejected."""
import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from typing import List
import pdfplumber
from app.parsers.csv_parser import CSVParser
from app.schemas.statements import ParsedTransactionDTO

DATE = r"\d{2}\.\d{2}\.\d{4}"
MONEY = r"[+−-]?\s*\d+(?:[ \xa0\u202f]\d{3})*[.,]\d{2}"


class PDFParser:
    @staticmethod
    def parse(content: bytes) -> List[ParsedTransactionDTO]:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > 100:
                raise ValueError("Максимум 100 страниц в одной выписке")
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            # Таблицы с явными колонками прихода/расхода или подписанными суммами.
            table_results = []
            for page in pdf.pages:
                for table in page.extract_tables():
                    header = next((i for i, row in enumerate(table[:6])
                                   if any("дата" in (cell or "").lower() for cell in row)
                                   and any(any(word in (cell or "").lower() for word in ["сумма", "приход", "дебет"]) for cell in row)), None)
                    if header is None:
                        continue
                    rows = [[re.sub(r"\s+", " ", cell or "").strip() for cell in row] for row in table[header:]]
                    # Для беззнаковых карточных PDF нужно учитывать отдельные правила банка.
                    has_direction = any(any(word in cell.lower() for word in ["приход", "кредит", "расход", "дебет"]) for cell in rows[0])
                    if not has_direction:
                        continue
                    output = io.StringIO()
                    csv.writer(output, delimiter=";").writerows(rows)
                    table_results.extend(CSVParser.parse(output.getvalue().encode()))
            if table_results:
                return table_results
        return PDFParser.parse_text(full_text)

    @staticmethod
    def parse_text(text: str) -> List[ParsedTransactionDTO]:
        is_sber = bool(re.search(r"сбер|sber|www\.sberbank\.ru", text, re.I))
        is_tbank = bool(re.search(r"т[\s-]*банк|тинькофф|tinkoff|t[\s-]*bank|t[\s-]*банк", text, re.I))
        is_alfa = bool(re.search(r"альфа|alfa", text, re.I))
        if not (is_sber or is_tbank or is_alfa):
            raise ValueError("Банк или формат PDF не распознан. Загрузите CSV с колонками даты и суммы")
        # Не склеиваем все даты документа: шапки и итоги не являются операциями.
        records = []
        for line in text.splitlines():
            line = re.sub(r"[ \t]+", " ", line).strip()
            if re.match(rf"^{DATE}\b", line) and re.search(MONEY, line):
                records.append(line)
            elif records and line and not re.search(r"остаток|итого|оборот|лицензи|страниц|www\.|выписка|подпись", line, re.I):
                records[-1] += " " + line
        results = []
        for record in records:
            if re.search(r"остаток|оборот|итого|за период|дата открытия|задолженность", record, re.I):
                continue
            date_match = re.match(rf"^({DATE})(?:\s+(\d{{2}}:\d{{2}}(?::\d{{2}})?))?", record)
            if not date_match:
                continue
            body = record[date_match.end():].strip()
            amounts = list(re.finditer(MONEY, body))
            if not amounts:
                continue
            if is_sber:
                selected = amounts[0]  # Вторая сумма — остаток, не сумма операции.
                raw = selected.group().strip()
                tx_type = "income" if raw.startswith("+") else "expense"
            else:
                currency_amounts = list(re.finditer(rf"({MONEY})\s*(RUR|RUB|₽|USD|EUR)(?:\b|(?=\s|$))", body, re.I))
                if not currency_amounts:
                    raise ValueError("Не удалось распознать денежные колонки PDF. Загрузите CSV")
                selected = currency_amounts[-1]
                if selected.group(2).upper() not in {"RUB", "RUR", "₽"}:
                    raise ValueError("PDF содержит операции в другой валюте. Загрузите рублевую выписку")
                raw = selected.group(1).strip()
                if not raw.startswith(("+", "-", "−")):
                    raise ValueError("В PDF не определено направление операции. Загрузите CSV с приходом и расходом")
                tx_type = "expense" if raw.startswith(("-", "−")) else "income"
            amount = abs(Decimal(re.sub(r"\s", "", raw).replace("−", "-").replace(",", ".")))
            if not amount:
                continue
            if amount >= Decimal("10000000000"):
                raise ValueError("Слишком большая сумма операции")
            desc = body
            for match in reversed(amounts):
                desc = desc[:match.start()] + desc[match.end():]
            desc = re.sub(rf"\b{DATE}\b|\b(?:RUB|RUR)\b", "", desc).strip()
            mcc_match = re.search(r"MCC\s*[: ]?\s*(\d{4})", desc, re.I)
            mcc = mcc_match.group(1) if mcc_match else None
            dt = datetime.strptime(date_match.group(1), "%d.%m.%Y")
            if date_match.group(2):
                time_parts = [int(part) for part in date_match.group(2).split(":")]
                dt = dt.replace(hour=time_parts[0], minute=time_parts[1], second=time_parts[2] if len(time_parts) > 2 else 0)
            results.append(ParsedTransactionDTO(amount=amount, currency="RUB", transaction_type=tx_type,
                category=CSVParser._determine_category(desc, mcc or "", tx_type, ""),
                mcc_code=mcc, description=desc or "Операция по карте", transaction_date=dt))
        return results
