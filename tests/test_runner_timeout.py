import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RunnerTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copyfile(ROOT / 'conformance.py', self.root / 'conformance.py')
        self.handler = self.root / 'handler'
        self.pid = self.root / 'pid'

    def handler_script(self, body):
        self.handler.write_text('#!' + sys.executable + '\n' + body)
        self.handler.chmod(0o700)

    def cases(self, kind):
        (self.root / 'case.json').write_text(json.dumps({
            'object': {'type': 'urn:object'}, 'intent': {'action': 'urn:intent'}}))
        case = {'file': 'case.json', 'binding_mode': 'exact', 'result_type': 'urn:result'}
        (self.root / 'expectations.json').write_text(json.dumps({
            'positive': [case] if kind == 'positive' else [],
            'negative': [case] if kind == 'negative' else []}))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(self.root / 'conformance.py'),
                               '--handler', str(self.handler), *args],
                              capture_output=True, text=True, timeout=5)

    def test_positive_and_negative_timeouts_fail_and_reap(self):
        for kind in ('positive', 'negative'):
            with self.subTest(kind=kind):
                self.cases(kind)
                self.handler_script('import os, time\nfrom pathlib import Path\n'
                                    f'Path({str(self.pid)!r}).write_text(str(os.getpid()))\n'
                                    'time.sleep(30)\n')
                p = self.run_cli('--timeout-seconds', '0.5')
                self.assertEqual(p.returncode, 1, p.stderr)
                self.assertIn('handler timed out', p.stderr)
                self.assertIn('case.json', p.stderr)
                self.assertNotIn('PASS', p.stdout)
                self.assertTrue(self.pid.exists(), 'fixture child actually started')
                if os.name == 'posix':
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int(self.pid.read_text()), 0)

    def test_success_with_timeout_and_without_timeout(self):
        self.cases('positive')
        self.handler_script('import json\nprint(json.dumps(' + repr({
            'status': 'ok', 'binding_mode': 'exact', 'object_type': 'urn:object',
            'intent': 'urn:intent', 'result_type': 'urn:result', 'result': {}}) + '))\n')
        for args in ((), ('--timeout-seconds', '2'), ('--timeout-seconds', '86400')):
            with self.subTest(args=args):
                p = self.run_cli(*args)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn('1 vectors', p.stdout)

    def test_negative_normal_nonzero_remains_pass(self):
        self.cases('negative')
        self.handler_script('raise SystemExit(7)\n')
        p = self.run_cli('--timeout-seconds', '2')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('PASS negative case.json', p.stdout)

    def test_oversized_timeout_rejected_before_handler(self):
        self.cases('negative')
        self.handler_script(f'from pathlib import Path\nPath({str(self.pid)!r}).touch()\n')
        for value in ('86400.0001', '1e10', '1e20', '1e308'):
            with self.subTest(value=value):
                p = self.run_cli('--timeout-seconds=' + value)
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertIn('at most 86400', p.stderr)
                self.assertFalse(self.pid.exists())

    def test_invalid_timeout_rejected_before_handler(self):
        self.cases('negative')
        self.handler_script(f'from pathlib import Path\nPath({str(self.pid)!r}).touch()\n')
        for value in ('0', '-1', 'nan', 'NaN', 'inf', '-inf', '1e999', 'text'):
            with self.subTest(value=value):
                p = self.run_cli('--timeout-seconds=' + value)
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertIn('positive finite number', p.stderr)
                self.assertFalse(self.pid.exists())


if __name__ == '__main__':
    unittest.main()
