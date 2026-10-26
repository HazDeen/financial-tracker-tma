import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('check_server', ROOT / 'scripts/check-server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReadinessTests(unittest.TestCase):
    def test_restart_connection_error_and_502_recover_without_parsing_error(self):
        with patch.object(module, 'fetch', side_effect=[(0, 'connection refused'), (502, ''), (200, '{"status":"ok"}')]) as fetch, patch.object(module.time, 'sleep') as sleep, contextlib.redirect_stdout(io.StringIO()):
            module.wait_for_json('http://test/api', lambda data: data.get('status') == 'ok')
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_html_or_permanent_backend_error_is_reported_immediately(self):
        for response in [(200, '<html>frontend</html>'), (500, 'Internal Server Error')]:
            with self.subTest(response=response), patch.object(module, 'fetch', return_value=response), patch.object(module.time, 'sleep') as sleep:
                with self.assertRaises(module.CheckError):
                    module.wait_for_json('http://test/api', lambda data: True)
                sleep.assert_not_called()

    def test_readiness_timeout_has_actionable_error(self):
        with patch.object(module, 'fetch', return_value=(502, '')), patch.object(module.time, 'monotonic', side_effect=[0, 60]):
            with self.assertRaisesRegex(module.CheckError, 'pm2 logs smart-finance-api'):
                module.wait_for_json('http://test/api', lambda data: True)
