"""Regression checks for updating one site inside a shared Caddyfile."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('configure_caddy', ROOT / 'scripts/configure-caddy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CaddyConfigTests(unittest.TestCase):
    def test_preserves_other_sites_and_global_configuration(self):
        before = '{\n admin localhost:2019\n}\nother.example {\n reverse_proxy localhost:9000\n}\n'
        old = 'finance.hazdeen.xyz {\n # ignored closing brace }\n handle {\n  header Test "text }"\n  try_files {path} /index.html\n }\n}\n'
        after = '\nlast.example {\n respond "unchanged"\n}\n'
        replacement = (ROOT / 'deploy/finance.Caddyfile').read_text().strip()
        result = module.replace_finance_site(before + old + after, replacement)
        self.assertEqual(result, before + replacement + '\n' + after)
        self.assertIn('@api path /api /api/*', result)
        self.assertNotIn('handle_path', result)
        self.assertEqual(module.replace_finance_site(result, replacement), result)

    def test_refuses_missing_duplicate_or_unclosed_sites(self):
        for source in ['other.example { }', 'finance.hazdeen.xyz { }\nfinance.hazdeen.xyz { }', 'finance.hazdeen.xyz { handle { }']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                module.replace_finance_site(source, 'finance.hazdeen.xyz { respond "ok" }')
