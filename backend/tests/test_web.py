"""Run: .venv/bin/python -m unittest discover -s backend/tests -v"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal

TEMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///' + str(Path(TEMP.name) / 'test.db')
os.environ['GEMINI_API_KEY'] = ''
os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['ENABLE_TELEGRAM_SCHEDULER'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from main import app, auth_attempts
from app.parsers.csv_parser import CSVParser
from app.parsers.pdf_parser import PDFParser

EXAMPLES = Path(__file__).resolve().parents[2] / 'frontend/public/examples'


class ParserTests(unittest.TestCase):
    def test_three_bank_formats(self):
        expected = {'alfabank': ('50000.00', '1700.50'), 'tbank': ('30000.00', '1850.50'), 'sberbank': ('40000.00', '1165.25')}
        for bank, (income, expense) in expected.items():
            with self.subTest(bank=bank):
                txs = CSVParser.parse((EXAMPLES / (bank + '.csv')).read_bytes())
                self.assertEqual(len(txs), 3)
                self.assertEqual(sum((tx.amount for tx in txs if tx.transaction_type == 'income'), Decimal(0)), Decimal(income))
                self.assertEqual(sum((tx.amount for tx in txs if tx.transaction_type == 'expense'), Decimal(0)), Decimal(expense))

    def test_cp1251_and_invalid_amount(self):
        raw = 'Дата операции;Сумма;Описание\n01.10.2026;-1 234,56;Магазин\n'
        self.assertEqual(CSVParser.parse(raw.encode('cp1251'))[0].amount, Decimal('1234.56'))
        for value in ['NaN', 'Infinity', 'oops', '1.001']:
            with self.assertRaises(ValueError):
                CSVParser.parse(f'date;amount\n2026-10-01;{value}\n'.encode())

    def test_csv_quoting_and_foreign_currency(self):
        txs = CSVParser.parse(b'date,amount,description\n2026-10-01,-10.25,"shop, cafe"\n')
        self.assertEqual(txs[0].description, 'shop, cafe')
        with self.assertRaises(ValueError):
            CSVParser.parse(b'date;amount;currency\n2026-10-01;10;USD\n')

    def test_pdf_files_with_text_layer(self):
        for bank in ['alfabank', 'tbank', 'sberbank']:
            with self.subTest(bank=bank):
                rows = PDFParser.parse((Path(__file__).parent / 'fixtures' / (bank + '.pdf')).read_bytes())
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0].amount, Decimal('1250.50'))
                self.assertEqual(rows[0].transaction_type, 'expense')
                self.assertEqual(rows[1].amount, Decimal('50000.00'))
                self.assertEqual(rows[1].transaction_type, 'income')

    def test_pdf_text_bank_rules(self):
        samples = {
            'СберБанк': '01.10.2026 10:20 123456 Магазин 1 250,50 9 000,00\n02.10.2026 11:00 654321 Зарплата +50 000,00 59 000,00',
            'Т-Банк': '01.10.2026 10:20:00 02.10.2026 -1 250,50 RUB -1 250,50 RUB Магазин\n02.10.2026 11:00:00 02.10.2026 +50 000,00 RUB +50 000,00 RUB Зарплата',
            'Альфа-Банк': '01.10.2026 Магазин -1 250,50 RUR\n02.10.2026 Зарплата +50 000,00 RUR',
        }
        for bank, lines in samples.items():
            with self.subTest(bank=bank):
                txs = PDFParser.parse_text(bank + '\n' + lines)
                self.assertEqual(len(txs), 2)
                self.assertEqual((txs[0].amount, txs[0].transaction_type), (Decimal('1250.50'), 'expense'))
                self.assertEqual((txs[1].amount, txs[1].transaction_type), (Decimal('50000.00'), 'income'))
        with self.assertRaises(ValueError):
            PDFParser.parse_text('Альфа-Банк\n01.10.2026 Магазин 250,00 RUR')


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        TEMP.cleanup()

    def setUp(self):
        self.client.cookies.clear()
        auth_attempts.clear()
        self.account = {'login': 'user_' + self._testMethodName.lower(), 'password': 'Strong-password-123'}
        response = self.client.post('/api/v1/auth/register', json=self.account)
        self.assertEqual(response.status_code, 201, response.text)
        self.user_id = response.json()['id']

    def report(self, **params):
        return self.client.get('/api/v1/analytics/monthly', params={'year': 2026, 'month': 10, **params})

    def transaction(self, **overrides):
        return self.client.post('/api/v1/transactions/', json={
            'amount': '123.45', 'transaction_type': 'expense', 'category': 'Продукты',
            'transaction_date': '2026-10-02T12:00:00Z', **overrides})

    def test_auth_cookie_login_logout(self):
        token = self.client.cookies.get('finance_session')
        cookie = self.client.post('/api/v1/auth/login', json=self.account).headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('Max-Age=2592000', cookie)
        self.assertIn('SameSite=lax', cookie)
        self.client.cookies.clear()
        self.client.cookies.set('finance_session', token)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/auth/logout').status_code, 204)
        self.client.cookies.set('finance_session', token)
        self.assertEqual(self.report().status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={**self.account, 'password': 'wrong-password'}).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/register', json=self.account).status_code, 409)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=self.account).status_code, 200)

    def test_manual_operations_and_isolation(self):
        first = self.transaction()
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(self.transaction().status_code, 201)  # identical real purchases survive
        self.assertEqual(self.transaction(amount='1000', transaction_type='income', category='Зарплата').status_code, 201)
        report = self.report().json()
        self.assertEqual(Decimal(report['total_expense']), Decimal('246.90'))
        self.assertEqual(Decimal(report['net_profit']), Decimal('753.10'))
        self.assertEqual(self.report(user_id=1).json()['total_expense'], report['total_expense'])
        self.client.post('/api/v1/auth/logout')
        self.client.post('/api/v1/auth/register', json={'login': 'second_isolation', 'password': 'Strong-password-123'})
        self.assertEqual(self.report(user_id=self.user_id).json()['transactions'], [])
        self.assertEqual(self.client.delete('/api/v1/transactions/' + str(first.json()['id'])).status_code, 404)

    def test_validation_and_delete(self):
        for payload in [{'amount': 0}, {'amount': -1}, {'amount': '1.001'}, {'category': ' '}, {'transaction_type': 'unknown'}]:
            self.assertEqual(self.transaction(**payload).status_code, 422)
        tx = self.transaction().json()
        self.assertEqual(self.client.delete('/api/v1/transactions/' + str(tx['id'])).status_code, 204)
        self.assertEqual(self.report().json()['transactions'], [])

    def test_preview_import_dedup_and_totals(self):
        for bank in ['alfabank', 'tbank', 'sberbank']:
            content = (EXAMPLES / f'{bank}.csv').read_bytes()
            preview = self.client.post('/api/v1/statements/preview', files={'file': (f'{bank}.csv', content)})
            self.assertEqual(preview.status_code, 200, preview.text)
            self.assertEqual(preview.json()['total'], 3)
            self.assertEqual(len(self.report().json()['transactions']), ['alfabank', 'tbank', 'sberbank'].index(bank) * 3)
            first = self.client.post('/api/v1/statements/upload', files={'file': (f'{bank}.csv', content)})
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()['inserted'], 3)
            second = self.client.post('/api/v1/statements/upload', files={'file': ('renamed.csv', content)})
            self.assertEqual(second.json()['inserted'], 0)
            self.assertEqual(second.json()['duplicates_ignored'], 3)
        report = self.report().json()
        self.assertEqual(len(report['transactions']), 9)
        self.assertEqual(Decimal(report['total_income']), Decimal('120000'))
        self.assertEqual(Decimal(report['total_expense']), Decimal('4716.25'))

    def test_import_identical_rows_and_opposite_direction(self):
        content = b'date;amount;description\n2026-10-02;-100;shop\n2026-10-02;-100;shop\n2026-10-02;100;shop\n'
        for expected in [3, 0]:
            response = self.client.post('/api/v1/statements/upload', files={'file': ('duplicates.csv', content)})
            self.assertEqual(response.json()['inserted'], expected)
        self.assertEqual(len(self.report().json()['transactions']), 3)

    def test_pdf_preview_and_import(self):
        for bank in ['alfabank', 'tbank', 'sberbank']:
            content = (Path(__file__).parent / 'fixtures' / (bank + '.pdf')).read_bytes()
            response = self.client.post('/api/v1/statements/preview', files={'file': (bank + '.pdf', content)})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['total'], 2)
            response = self.client.post('/api/v1/statements/upload', files={'file': (bank + '.pdf', content)})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['inserted'], 2)

    def test_update_transaction_keeps_identity(self):
        tx = self.transaction().json()
        payload = {'amount': '200.50', 'transaction_type': 'income', 'category': 'Возврат', 'description': 'Исправление', 'transaction_date': '2026-10-03T12:00:00Z'}
        response = self.client.put('/api/v1/transactions/' + str(tx['id']), json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['id'], tx['id'])
        self.assertEqual(len(self.report().json()['transactions']), 1)
        self.assertEqual(Decimal(self.report().json()['total_income']), Decimal('200.50'))
        self.assertEqual(Decimal(self.report().json()['total_expense']), Decimal(0))
        self.client.post('/api/v1/auth/register', json={'login': 'update_other', 'password': 'Strong-password-123'})
        self.assertEqual(self.client.put('/api/v1/transactions/' + str(tx['id']), json=payload).status_code, 404)

    def test_bad_import_is_atomic(self):
        content = b'date;amount;description\n2026-10-02;-100;shop\n2026-10-02;bad;shop\n'
        response = self.client.post('/api/v1/statements/upload', files={'file': ('broken.csv', content)})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.report().json()['transactions'], [])
        self.assertEqual(self.client.post('/api/v1/statements/upload', files={'file': ('scan.pdf', b'%PDF-invalid')}).status_code, 422)
        self.assertEqual(self.client.post('/api/v1/statements/upload', files={'file': ('empty.csv', b'')}).status_code, 422)

    def test_all_finance_routes_require_session(self):
        self.client.cookies.clear()
        for url in ['/analytics/monthly?year=2026&month=10', '/debts/', '/recurring/', '/shifts/summary?year=2026&month=10', '/ai-advisor/analyze?year=2026&month=10']:
            self.assertEqual(self.client.get('/api/v1' + url).status_code, 401, url)
        self.assertEqual(self.transaction().status_code, 401)
        self.assertEqual(self.client.post('/api/v1/users/sync', json={'id': 1}).status_code, 404)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.client.post('/api/v1/auth/login', json=self.account, headers={'Origin': 'https://evil.example'}).status_code, 403)

    def test_expired_session_and_rate_limit(self):
        import asyncio
        from datetime import datetime, timedelta
        from app.core.database import AsyncSessionLocal
        from app.models.auth import WebSession
        from app.core.auth import token_digest
        async def expire():
            async with AsyncSessionLocal() as db:
                session = await db.get(WebSession, token_digest(self.client.cookies.get('finance_session')))
                session.expires_at = datetime.utcnow() - timedelta(seconds=1)
                await db.commit()
        asyncio.run(expire())
        self.assertEqual(self.report().status_code, 401)
        from time import monotonic
        auth_attempts['testclient'].extend([monotonic()] * 30)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=self.account).status_code, 429)


if __name__ == '__main__':
    unittest.main()
