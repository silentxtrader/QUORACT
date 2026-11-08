"""Exercise result-identifier checks through the real conformance CLI.

The executable fixture supplies controlled responses, not an independent
QUORACT handler or proof of handler conformance.
"""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_VECTORS = ('schemaorg-calendar.json', 'activitystreams-note.json')
HANDLER = '''import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--envelope', required=True)
vector = Path(parser.parse_args().envelope)
if vector.parent.name == 'negative':
    raise SystemExit(7)
request = json.loads(vector.read_text())
result_type = request['result']['expects']
if result_type == 'https://example.org/semantic/calendar/created/1':
    binding_mode = 'direct-schema-id'
    result = {'event_id': 'fixture-event'}
else:
    binding_mode = 'external-vocabulary'
    result = {'@type': result_type, **request['object']['data']}
    if vector.name == target and include_id:
        result['@id'] = identifier
print(json.dumps({
    'status': 'ok', 'binding_mode': binding_mode,
    'object_type': request['object']['type'],
    'intent': request['intent']['action'], 'result_type': result_type,
    'result': result,
}))
'''


class ResultIdentifierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.handler = Path(temporary.name) / 'handler'

    def run_cli(self, target, identifier, include_id=True):
        self.handler.write_text(
            '#!' + sys.executable + '\n'
            + f'target = {target!r}\nidentifier = {identifier!r}\n'
            + f'include_id = {include_id!r}\n' + HANDLER,
            encoding='utf-8',
        )
        self.handler.chmod(0o700)
        return subprocess.run(
            [sys.executable, '-B', str(ROOT / 'conformance.py'),
             '--handler', str(self.handler)],
            capture_output=True, text=True, timeout=10,
        )

    def test_raw_spaces_and_controls_fail_in_both_external_bindings(self):
        # Literal identifiers violate URI syntax even when urlparse silently
        # removes the offending characters or still reports a scheme.
        invalid = (
            ' https://example.org/id',
            '\x00https://example.org/id',
            '\nhttps://example.org/id',
            'ht\ttps://example.org/id',
            'https://example.org/a\nb',
            'https://example.org/id\r',
            'https://example.org/a b',
            'urn:example:bad\x1fvalue',
            'urn:example:bad\x7fvalue',
        )
        for target in EXTERNAL_VECTORS:
            for identifier in invalid:
                with self.subTest(vector=target, identifier=identifier):
                    result = self.run_cli(target, identifier)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn('result @id is not absolute URI', result.stderr)
                    self.assertIn(target, result.stderr)
                    self.assertNotIn('PASS v0.9', result.stdout)

    def test_valid_absolute_ids_and_omitted_ids_remain_accepted(self):
        for target in EXTERNAL_VECTORS:
            for identifier in (
                'https://example.org/id',
                'urn:example:local-event',
                'https://example.org/a%20b?note=%0A',
            ):
                with self.subTest(vector=target, identifier=identifier):
                    result = self.run_cli(target, identifier)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('PASS v0.9 clean-room proxy conformance:', result.stdout)
            with self.subTest(vector=target, identifier='omitted'):
                result = self.run_cli(target, None, include_id=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_relative_and_non_string_ids_remain_rejected(self):
        for identifier in ('/relative', '', None, 123, {}):
            with self.subTest(identifier=identifier):
                result = self.run_cli(EXTERNAL_VECTORS[0], identifier)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('result @id is not absolute URI', result.stderr)


if __name__ == '__main__':
    unittest.main()
