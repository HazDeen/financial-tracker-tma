import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.company_import import extract_figures


class CompanyImportTests(unittest.TestCase):
    def test_russian_scaled_csv_and_loss(self):
        content = 'Показатель;Значение\nЕдиницы;млн руб.\nВыручка;100,5\nЧистая прибыль;(2,5)\nКапитал;50\n'.encode('cp1251')
        result = extract_figures(content, '.csv')
        self.assertEqual(result['metrics'], {'netIncome': '-2500000.0', 'revenue': '100500000.0', 'equity': '50000000'})

    def test_wide_csv_and_zero(self):
        result = extract_figures(b'cash,netIncome,revenue\n0,-50,1000\n', '.csv')
        self.assertEqual(result['metrics'], {'cash': '0', 'netIncome': '-50', 'revenue': '1000'})

    def test_period_column_and_conflicting_values(self):
        result = extract_figures('Показатель;2025;2024\nВыручка;100;90\nДолг;10;20\nДолг;15;30\n'.encode(), '.csv', 1)
        self.assertEqual(result['metrics'], {'revenue': '90'})
        self.assertTrue(any('№2' in warning for warning in result['warnings']))
        self.assertTrue(any('противоречивые' in warning for warning in result['warnings']))

    def test_missing_column_does_not_shift_period(self):
        result = extract_figures('Показатель;2026;2025\nВыручка;;900\nДолг;10;20\n'.encode(), '.csv')
        self.assertEqual(result['metrics'], {'debt': '10'})

    def test_unknown_invalid_and_foreign_amounts(self):
        for content in ['label;value\nhello;10', 'cash;value\ncash;-1', 'cash;value\ncash;NaN',
                        'USD;value\ncash;100', 'Единицы;млн руб. и тыс руб.\ncash;100']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                extract_figures(content.encode(), '.csv')

    def test_pdf_text_and_tables(self):
        for table in [[], [[['Показатель', '2025', '2024'], ['Выручка', '100', '90']]]]:
            page = MagicMock()
            page.extract_text.return_value = 'Отчёт в млн руб.\nВыручка 100 90\nЧистая прибыль (20)'
            page.extract_tables.return_value = table
            document = MagicMock()
            document.__enter__.return_value.pages = [page]
            with patch('app.services.company_import.pdfplumber.open', return_value=document):
                result = extract_figures(b'%PDF-test', '.pdf')
            self.assertEqual(result['metrics']['revenue'], '100000000')
            self.assertEqual(result['metrics']['netIncome'], '-20000000')

    def test_real_pdf_text_extraction(self):
        # Minimal real PDF exercises pdfplumber, not a mocked extraction result.
        stream = b'BT /F1 12 Tf 50 750 Td (Revenue 1000 900) Tj 0 -20 Td (Net income 100 90) Tj ET'
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
        content = b'%PDF-1.4\n'
        offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(content))
            content += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
        xref = len(content)
        content += b'xref\n0 6\n0000000000 65535 f \n'
        for offset in offsets[1:]:
            content += f'{offset:010d} 00000 n \n'.encode()
        content += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
        self.assertEqual(extract_figures(content, '.pdf')['metrics'], {'revenue': '1000', 'netIncome': '100'})
        self.assertEqual(extract_figures(content, '.pdf', 1)['metrics'], {'revenue': '900', 'netIncome': '90'})

    def test_empty_or_broken_pdf(self):
        with self.assertRaises(ValueError):
            extract_figures(b'%PDF-invalid', '.pdf')
        document = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = ''
        page.extract_tables.return_value = []
        document.__enter__.return_value.pages = [page]
        with patch('app.services.company_import.pdfplumber.open', return_value=document), self.assertRaisesRegex(ValueError, 'текстового слоя'):
            extract_figures(b'%PDF-scan', '.pdf')
