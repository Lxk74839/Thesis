"""PUBLIC handwritten fixture only; never an old HTTP response replay."""
import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile

from tests.test_fourrouter_protocol_diagnostics import public_request, public_response, setUpModule


class FirstRequestDiagnostic(unittest.TestCase):
    def test_exclusive_claim_prevents_second_diagnostic(self):
        spec = importlib.util.spec_from_file_location('first_diagnostic_claim', Path(__file__).resolve().parents[1]
            / '.scratch/ticket14-first-request-20261020/run_once.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.tmp') as tmp:
            path = Path(tmp)
            receipt = entry.claim_first_execution(path, path / 'attempt.json', 'a' * 40)
            self.assertEqual(receipt.name, 'execution-result.json')
            self.assertTrue((path / 'execution-claim.json').exists())
            with self.assertRaises(FileExistsError):
                entry.claim_first_execution(path, path / 'attempt.json', 'a' * 40)
        for marker in ('execution-result.json', 'execution-resources.jsonl', 'attempt.json'):
            with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.tmp') as tmp:
                path = Path(tmp)
                (path / marker).write_text('PUBLIC fixture')
                with self.assertRaises(FileExistsError):
                    entry.ensure_first_execution(path, path / 'attempt.json')

    def test_one_response_strict_diagnostic_without_recording_text(self):
        spec = importlib.util.spec_from_file_location('first_diagnostic', Path(__file__).resolve().parents[1]
            / '.scratch/ticket14-first-request-20261020/run_once.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        response = public_response()
        response['body']['output'].insert(0, {'type': 'reasoning', 'summary': ['PUBLIC-SECRET-TEXT']})
        sent = []
        def sender(wire, *, deadline_ms):
            sent.append(True)
            return copy.deepcopy(response)
        result = entry.diagnose(public_request(), {'wire_utf8': '{}'}, sender=sender, clock=lambda: 1000)
        self.assertEqual(len(sent), 1)
        self.assertEqual(result['protocol_diagnostic'], {'stage': 'output_item',
            'code': 'unsupported_output_type', 'field': 'type', 'output_index': 0, 'item_type': 'reasoning'})
        self.assertEqual(result['usage']['input_tokens'], 100)
        self.assertIsNone(result['cost'])
        self.assertNotIn('PUBLIC-SECRET-TEXT', str(result))
        self.assertEqual(result['output_structure'][1]['content_types'], ['output_text'])
