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


class RoutingTests(unittest.TestCase):
    def test_api_root_and_unknown_routes_never_return_frontend(self):
        with TestClient(app) as client:
            for path in ['/api', '/api/', '/api/health']:
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertEqual(response.json()['status'], 'ok')
                self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertEqual(client.head('/api').status_code, 200)
            for method in ['GET', 'HEAD', 'POST', 'PATCH', 'OPTIONS']:
                response = client.request(method, '/api/not-an-endpoint')
                self.assertEqual(response.status_code, 404, method)
                self.assertIn('application/json', response.headers['content-type'])
            schema = client.get('/api/openapi.json')
            self.assertEqual(schema.status_code, 200)
            self.assertIn('/api/v1/auth/login', schema.json()['paths'])
            for path in ['/api/docs', '/api/redoc']:
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('/api/openapi.json', response.text)


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

    def test_company_reports_lifecycle_and_account_isolation(self):
        path = '/api/v1/company-reports'
        data = {'company': 'Тестовая компания', 'period': '2025, год',
                'metrics': '{"marketCap": "1000", "netIncome": "100"}'}
        content = b'%PDF-1.7\nexample report'
        response = self.client.post(path, data=data, files={'file': ('отчёт.pdf', content, 'application/pdf')})
        self.assertEqual(response.status_code, 201, response.text)
        report = response.json()
        self.assertEqual(report['metrics']['marketCap'], '1000')
        self.assertEqual(report['size'], len(content))
        self.assertNotIn('content', report)
        self.assertNotIn('user_id', report)
        report_id = report['id']
        self.assertEqual(self.client.get(path).json()[0]['id'], report_id)
        downloaded = self.client.get(f'{path}/{report_id}/file')
        self.assertEqual(downloaded.content, content)
        self.assertIn('attachment;', downloaded.headers['content-disposition'])
        self.assertEqual(downloaded.headers['x-content-type-options'], 'nosniff')
        self.client.post('/api/v1/auth/register', json={'login': 'report_other_account', 'password': 'Other-password-123'})
        self.assertEqual(self.client.get(path).json(), [])
        self.assertEqual(self.client.get(f'{path}/{report_id}/file').status_code, 404)
        self.assertEqual(self.client.delete(f'{path}/{report_id}').status_code, 404)
        self.client.post('/api/v1/auth/login', json=self.account)
        self.assertEqual(self.client.delete(f'{path}/{report_id}').status_code, 204)
        self.assertEqual(self.client.get(path).json(), [])
        self.assertEqual(self.client.get(f'{path}/{report_id}/file').status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post(path, data=data, files={'file': ('x.pdf', content)}).status_code, 401)

    def test_company_reports_validate_upload_and_figures(self):
        import io
        import zipfile
        from unittest.mock import patch
        path = '/api/v1/company-reports'
        data = {'company': 'Компания', 'period': '2025'}
        cases = [
            ('a.exe', b'hello', {}, 422), ('a.pdf', b'not pdf', {}, 422),
            ('a.csv', b'', {}, 422), ('a.csv', b'a\x00b', {}, 422),
            ('a.xlsx', b'PK invalid', {}, 422),
            ('a.csv', b'name,value\nprofit,10', {'company': ' '}, 422),
            ('a.csv', b'name,value\nprofit,10', {'metrics': '{"cash":-1}'}, 422),
            ('a.csv', b'name,value\nprofit,10', {'metrics': '{"cash":"NaN"}'}, 422),
            ('a.csv', b'name,value\nprofit,10', {'metrics': '{"unknown":1}'}, 422),
            ('a.csv', b'name,value\nprofit,10', {'metrics': '[]'}, 422),
        ]
        for name, content, extra, status in cases:
            response = self.client.post(path, data={**data, **extra}, files={'file': (name, content)})
            self.assertEqual(response.status_code, status, response.text)
        with patch('app.api.v1.endpoints.company_reports.MAX_SIZE', 4):
            response = self.client.post(path, data=data, files={'file': ('a.csv', b'12345')})
            self.assertEqual(response.status_code, 413)
        response = self.client.post(path, data=data, files={'file': ('../report.csv', b'name,value\nprofit,10')})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['filename'], 'report.csv')
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as workbook:
            workbook.writestr('[Content_Types].xml', '<Types/>')
            workbook.writestr('xl/workbook.xml', '<workbook/>')
        response = self.client.post(path, data=data, files={'file': ('report.xlsx', archive.getvalue())})
        self.assertEqual(response.status_code, 201, response.text)
        for _ in range(18):
            self.assertEqual(self.client.post(path, data=data, files={'file': ('a.csv', b'key,value')}).status_code, 201)
        self.assertEqual(self.client.post(path, data=data, files={'file': ('a.csv', b'key,value')}).status_code, 409)

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

    def test_password_change_revokes_other_sessions(self):
        old_token = self.client.cookies.get('finance_session')
        self.client.post('/api/v1/auth/login', json=self.account)
        response = self.client.post('/api/v1/auth/password', json={'current_password': 'wrong', 'new_password': 'New-password-456'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 200)
        response = self.client.post('/api/v1/auth/password', json={'current_password': self.account['password'], 'new_password': 'New-password-456'})
        self.assertEqual(response.status_code, 200, response.text)
        new_token = self.client.cookies.get('finance_session')
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 200)
        self.client.cookies.clear()
        self.client.cookies.set('finance_session', old_token)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=self.account).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={**self.account, 'password': 'New-password-456'}).status_code, 200)
        self.assertNotEqual(new_token, old_token)

    def test_opening_balance_and_account_isolation(self):
        self.assertEqual(self.client.get('/api/v1/analytics/balance').json()['balance'], '0.00')
        response = self.client.put('/api/v1/analytics/balance', json={'opening_balance': '1000.00'})
        self.assertEqual(response.status_code, 200, response.text)
        self.transaction(amount='250.00')
        self.transaction(amount='500.00', transaction_type='income')
        self.transaction(amount='900.00', transaction_type='income', transaction_date='2099-01-01T00:00:00Z')
        self.assertEqual(Decimal(self.client.get('/api/v1/analytics/balance').json()['balance']), Decimal('1250.00'))
        self.client.post('/api/v1/auth/register', json={'login': 'other_balance_user', 'password': 'Other-password-123'})
        self.assertEqual(Decimal(self.client.get('/api/v1/analytics/balance').json()['balance']), 0)

    def test_schedule_confirmation_duplicate_and_month_end(self):
        payload = {'title': 'Интернет', 'amount': '700.00', 'transaction_type': 'expense', 'category': 'Подписки', 'billing_day': 31, 'next_payment_date': '2026-01-31'}
        created = self.client.post('/api/v1/recurring/', json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        row_id = created.json()['id']
        url = f'/api/v1/recurring/{row_id}/confirm'
        confirm = {'due_date': '2026-01-31', 'transaction_date': '2026-10-20'}
        first = self.client.post(url, json=confirm)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['next_payment_date'], '2026-02-28')
        self.assertEqual(self.client.post(url, json=confirm).status_code, 409)
        self.assertEqual(len(self.report().json()['transactions']), 1)
        second = self.client.post(url, json={**confirm, 'due_date': '2026-02-28'})
        self.assertEqual(second.json()['next_payment_date'], '2026-03-31')
        self.client.patch(f'/api/v1/recurring/{row_id}/toggle')
        self.assertEqual(self.client.post(url, json={**confirm, 'due_date': '2026-03-31'}).status_code, 409)
        self.assertEqual(len(self.report().json()['transactions']), 2)

    def test_schedule_edit_and_ownership(self):
        payload = {'title': 'Аванс', 'amount': '20000.00', 'transaction_type': 'income', 'category': 'Зарплата', 'billing_day': 10, 'next_payment_date': '2026-11-10'}
        row_id = self.client.post('/api/v1/recurring/', json=payload).json()['id']
        updated = self.client.put(f'/api/v1/recurring/{row_id}', json={**payload, 'amount': '25000.00'})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['id'], row_id)
        self.assertEqual(Decimal(updated.json()['amount']), Decimal('25000'))
        self.client.post('/api/v1/auth/register', json={'login': 'other_schedule_user', 'password': 'Other-password-123'})
        self.assertEqual(self.client.put(f'/api/v1/recurring/{row_id}', json=payload).status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/recurring/{row_id}/confirm', json={'due_date': '2026-11-10', 'transaction_date': '2026-11-10'}).status_code, 404)

    def test_concurrent_confirmation_is_once(self):
        from concurrent.futures import ThreadPoolExecutor
        payload = {'title': 'Подписка', 'amount': '449', 'transaction_type': 'expense', 'category': 'Подписки', 'billing_day': 22, 'next_payment_date': '2026-10-22'}
        row_id = self.client.post('/api/v1/recurring/', json=payload).json()['id']
        def confirm():
            return self.client.post(f'/api/v1/recurring/{row_id}/confirm', json={'due_date': '2026-10-22', 'transaction_date': '2026-10-22'}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: confirm(), range(2)))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(len(self.report().json()['transactions']), 1)

    def test_recovery_code_resets_password_and_revokes_sessions(self):
        old_session = self.client.cookies.get('finance_session')
        code = self.client.post('/api/v1/auth/recovery-code', json={'current_password': self.account['password']}).json()['recovery_code']
        self.client.cookies.clear()
        payload = {**self.account, 'password': 'Recovered-password-456', 'recovery_code': code}
        bad = self.client.post('/api/v1/auth/reset-password', json={**payload, 'recovery_code': 'wrong'})
        self.assertEqual(bad.status_code, 400)
        response = self.client.post('/api/v1/auth/reset-password', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        new_code = response.json()['recovery_code']
        self.assertNotEqual(new_code, code)
        self.assertEqual(self.client.get('/api/v1/auth/me').json()['id'], self.user_id)
        self.client.cookies.clear()
        self.client.cookies.set('finance_session', old_session)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=self.account).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={**self.account, 'password': payload['password']}).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json={**payload, 'recovery_code': new_code}).status_code, 200)

    def test_recovery_setup_requires_password_and_replaces_code(self):
        self.assertEqual(self.client.post('/api/v1/auth/recovery-code', json={'current_password': 'wrong'}).status_code, 400)
        first = self.client.post('/api/v1/auth/recovery-code', json={'current_password': self.account['password']}).json()['recovery_code']
        second = self.client.post('/api/v1/auth/recovery-code', json={'current_password': self.account['password']}).json()['recovery_code']
        self.assertNotEqual(first, second)
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/v1/auth/recovery-code', json={'current_password': self.account['password']}).status_code, 401)
        payload = {**self.account, 'recovery_code': first}
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json={**payload, 'login': 'unknown_user', 'recovery_code': second}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json={**payload, 'recovery_code': second}).status_code, 200)

    def test_registration_recovery_code_and_reset_rate_limit(self):
        response = self.client.post('/api/v1/auth/register', json={'login': 'recovery_signup', 'password': self.account['password']})
        code = response.json()['recovery_code']
        self.assertEqual(len(code), 40)
        payload = {'login': 'recovery_signup', 'password': 'New-password-123', 'recovery_code': code}
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json=payload).status_code, 200)
        auth_attempts.clear()
        for _ in range(30):
            self.assertEqual(self.client.post('/api/v1/auth/reset-password', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/reset-password', json=payload).status_code, 429)

    def test_salary_month_range_includes_both_boundary_days(self):
        for date, amount, kind in [
            ('2026-09-22T23:59:59.999999Z', '999', 'income'),
            ('2026-09-23T00:00:00Z', '1000', 'income'),
            ('2026-10-23T23:59:59.999999Z', '250', 'expense'),
            ('2026-10-24T00:00:00Z', '888', 'expense'),
        ]:
            self.assertEqual(self.transaction(transaction_date=date, amount=amount, transaction_type=kind).status_code, 201)
        data = self.client.get('/api/v1/analytics/period', params={'start_date': '2026-09-23', 'end_date': '2026-10-23'}).json()
        self.assertEqual(Decimal(data['total_income']), Decimal('1000'))
        self.assertEqual(Decimal(data['total_expense']), Decimal('250'))
        self.assertEqual(Decimal(data['net_profit']), Decimal('750'))
        self.assertEqual(len(data['transactions']), 2)

    def test_day_report_includes_whole_day_only(self):
        self.transaction(amount='10.00', transaction_date='2026-10-21T23:59:59Z')
        self.transaction(amount='20.00', transaction_date='2026-10-22T00:00:00Z')
        self.transaction(amount='30.00', transaction_date='2026-10-22T23:59:59.999999Z')
        self.transaction(amount='40.00', transaction_date='2026-10-23T00:00:00Z')
        response = self.client.get('/api/v1/analytics/period', params={'start_date': '2026-10-22', 'end_date': '2026-10-22'})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(Decimal(data['total_expense']), Decimal('50.00'))
        self.assertEqual(Decimal(data['expense_by_category'][0]['amount']), Decimal('50.00'))
        self.assertEqual(len(data['transactions']), 2)
        self.assertEqual(data['start_date'], '2026-10-22')
        self.assertEqual(data['end_date'], '2026-10-22')

    def test_range_across_months_and_account_isolation(self):
        self.transaction(amount='150.00', transaction_type='income', transaction_date='2026-09-30T12:00:00Z')
        self.transaction(amount='50.00', transaction_date='2026-10-01T12:00:00Z')
        params = {'start_date': '2026-09-30', 'end_date': '2026-10-01'}
        data = self.client.get('/api/v1/analytics/period', params=params).json()
        self.assertEqual(Decimal(data['net_profit']), Decimal('100.00'))
        self.assertEqual(len(data['transactions']), 2)
        self.client.post('/api/v1/auth/register', json={'login': 'other_period_user', 'password': 'Other-password-123'})
        data = self.client.get('/api/v1/analytics/period', params=params).json()
        self.assertEqual(len(data['transactions']), 0)
        self.assertEqual(Decimal(data['net_profit']), 0)

    def test_period_validation_and_leap_day(self):
        for start, end in [('2026-10-23', '2026-10-22'), ('1999-12-31', '2000-01-01'), ('2100-12-31', '2101-01-01'), ('2026-02-30', '2026-03-01')]:
            response = self.client.get('/api/v1/analytics/period', params={'start_date': start, 'end_date': end})
            self.assertEqual(response.status_code, 422, response.text)
        self.transaction(amount='99.99', transaction_date='2024-02-29T23:59:59Z')
        data = self.client.get('/api/v1/analytics/period', params={'start_date': '2024-02-29', 'end_date': '2024-02-29'}).json()
        self.assertEqual(Decimal(data['total_expense']), Decimal('99.99'))
        self.assertEqual(len(data['transactions']), 1)


if __name__ == '__main__':
    unittest.main()
