"""Conservative extraction of labelled financial figures; amounts are normalized to RUB."""
import csv
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import pdfplumber

ALIASES = {
    'marketCap': ['marketcap', 'market capitalization', 'рыночная капитализация', 'капитализация'],
    'netIncome': ['netincome', 'net income', 'net profit', 'profit', 'чистая прибыль', 'чистая прибыль за год', 'чистая прибыль (убыток)', 'прибыль (убыток) за год'],
    'revenue': ['revenue', 'выручка', 'выручка за год'],
    'equity': ['equity', 'total equity', 'капитал', 'капитал на конец периода', 'итого капитал', 'капитал и резервы'],
    'averageEquity': ['averageequity', 'average equity', 'средний капитал', 'средний капитал за год'],
    'debt': ['debt', 'total debt', 'процентный долг', 'долг'],
    'cash': ['cash', 'cash and cash equivalents', 'денежные средства', 'денежные средства и их эквиваленты'],
    'ebitda': ['ebitda', 'ebitda за год'],
}

def normalize(value):
    return re.sub(r'\s+', ' ', value.strip().lower().replace('ё', 'е'))

LOOKUP = {normalize(alias): key for key, aliases in ALIASES.items() for alias in aliases}
LINE_CODES = {'revenue': '2110', 'netIncome': '2400', 'equity': '1300', 'cash': '1250'}


def amount(raw):
    raw = raw.strip().replace('\u2212', '-').replace('\u00a0', '').replace(' ', '')
    raw = re.sub(r'(₽|руб\.?|rub)$', '', raw, flags=re.I)
    if raw.startswith('(') and raw.endswith(')'):
        raw = '-' + raw[1:-1]
    if ',' in raw and '.' in raw:
        raw = raw.replace(',', '') if raw.rfind('.') > raw.rfind(',') else raw.replace('.', '').replace(',', '.')
    else:
        raw = raw.replace(',', '.')
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def extract_figures(content: bytes, suffix: str, value_column: int = 0):
    warnings = []
    if suffix == '.csv':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('cp1251')
        if '\x00' in text:
            raise ValueError('Выберите текстовый CSV')
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=';,\t')
            rows = list(csv.reader(StringIO(text), dialect))
        except csv.Error:
            raise ValueError('Не удалось прочитать CSV. Используйте разделитель ; или запятую.')
    elif suffix == '.pdf':
        try:
            with pdfplumber.open(BytesIO(content)) as document:
                if len(document.pages) > 150:
                    raise ValueError('Для распознавания выберите PDF не длиннее 150 страниц')
                text_parts = []
                table_rows = []
                for page in document.pages:
                    text_parts.append(page.extract_text(x_tolerance=2) or '')
                    for table in page.extract_tables():
                        table_rows.extend([[str(cell or '').replace('\n', ' ') for cell in row] for row in table])
                text = '\n'.join(text_parts)
        except ValueError:
            raise
        except Exception:
            raise ValueError('Не удалось прочитать PDF. Проверьте, что он не повреждён и не защищён паролем.')
        if not text.strip():
            raise ValueError('В PDF нет текстового слоя. Загрузите текстовый PDF или CSV.')
        rows = [row for row in table_rows if row and normalize(row[0]) in LOOKUP]
        table_labels = {normalize(row[0]) for row in rows}
        aliases = sorted(LOOKUP, key=len, reverse=True)
        for line in text.splitlines():
            line = normalize(line)
            for alias in aliases:
                if line.startswith(alias) and len(line) > len(alias) and line[len(alias)] in ' :;\t|':
                    if alias in table_labels:
                        break
                    tail = line[len(alias):].strip(' :;\t|')
                    # Ignore an accounting line code, such as 2110 or 2400.
                    code = LINE_CODES.get(LOOKUP[alias])
                    if code:
                        tail = re.sub(r'^' + code + r'\s+(?=[(\-\d])', '', tail)
                    values = re.findall(r'\(?[−\-+]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,]\d+)?\)?', tail)
                    rows.append([alias, *values])
                    break
    else:
        raise ValueError('Автозаполнение поддерживает PDF и CSV. Для XLSX введите показатели вручную.')

    lowered = normalize(text)
    if re.search(r'\b(usd|eur|доллар\w*|евро)\b', lowered):
        raise ValueError('Автозаполнение поддерживает суммы в рублях. Пересчитайте валютную отчётность в рубли.')
    scales = {Decimal(multiplier) for pattern, multiplier in [
        (r'\b(?:тыс\.?\s*(?:руб|₽)|thousand\s*rub)', '1000'),
        (r'\b(?:млн\.?\s*(?:руб|₽)|million\s*rub)', '1000000'),
        (r'\b(?:млрд\.?\s*(?:руб|₽)|billion\s*rub)', '1000000000'),
    ] if re.search(pattern, lowered)}
    if len(scales) > 1:
        raise ValueError('В файле несколько масштабов сумм. Подготовьте таблицу с единым масштабом в рублях.')
    scale = next(iter(scales), Decimal(1))
    candidates = {key: set() for key in ALIASES}
    def add(label, raw):
        key = LOOKUP.get(normalize(label))
        value = amount(raw)
        if key and value is not None:
            value *= scale
            if abs(value) <= 10**15 and (key not in {'marketCap', 'revenue', 'debt', 'cash'} or value >= 0):
                candidates[key].add(value)
    # Wide CSV: marketCap;netIncome;revenue / 1000;100;500.
    if suffix == '.csv' and rows and sum(normalize(cell) in LOOKUP for cell in rows[0]) >= 2:
        for row in rows[1:]:
            for label, raw in zip(rows[0], row):
                add(label, raw)
    else:
        for row in rows:
            if len(row) >= 2 and normalize(row[0]) in LOOKUP:
                numeric = row[1:]
                if suffix == '.pdf' and len(numeric) > 1 and numeric[0].strip() == LINE_CODES.get(LOOKUP[normalize(row[0])]):
                    numeric = numeric[1:]
                if len(numeric) > value_column and amount(numeric[value_column]) is not None:
                    add(row[0], numeric[value_column])
                    if len(numeric) > 1:
                        warnings.append(f'Несколько колонок сумм: использована колонка №{value_column + 1}. Проверьте, что она соответствует нужному периоду.')
                elif numeric:
                    warnings.append(f'«{row[0]}»: колонка №{value_column + 1} отсутствует — показатель не заполнен.')
    figures = {}
    for key, values in candidates.items():
        if len(values) == 1:
            figures[key] = str(next(iter(values)))
        elif len(values) > 1:
            warnings.append(f'«{ALIASES[key][0]}»: противоречивые значения — показатель не заполнен.')
    if not figures:
        raise ValueError('Не найдены однозначные показатели. Используйте CSV «Показатель;Значение» с одной колонкой сумм за нужный период.')
    warnings.append('Проверьте период и распознанные суммы перед сохранением. Ненайденные поля оставлены пустыми.')
    return {'metrics': figures, 'warnings': list(dict.fromkeys(warnings)), 'scale': str(scale)}
