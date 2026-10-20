"""PUBLIC handwritten fixture only; never an old HTTP response replay."""
import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile

from tests.test_fourrouter_protocol_diagnostics import public_request, public_response, setUpModule


class FirstRequestDiagnostic(unittest.TestCase):
    def test_all_artifact_copies_and_stdout_share_one_mib(self):
        spec = importlib.util.spec_from_file_location('first_diagnostic_quota', Path(__file__).resolve().parents[1]
            / '.scratch/ticket14-first-request-20261020/run_once.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.tmp') as tmp:
            package, output = Path(tmp) / 'control', Path(tmp) / 'output'
            package.mkdir(); output.mkdir()
            (package / 'execution.stdout').write_bytes(b'PUBLIC\n' * 100)
            (package / 'execution-claim.json').write_bytes(b'{}')
            entry.write_artifact(output / 'result.json', b'P' * 900000, package=package, output=output)
            entry.write_artifact(package / 'execution-result.json', b'{}', package=package, output=output)
            with self.assertRaises(OSError):
                entry.write_artifact(output / 'overflow.json', b'X' * 150000, package=package, output=output)
            self.assertFalse((output / 'overflow.json').exists())
            self.assertEqual(entry.artifact_bytes(package, output), 900704)

    def test_transport_failure_preserves_explicit_unknown_metering(self):
        spec = importlib.util.spec_from_file_location('first_diagnostic_transport', Path(__file__).resolve().parents[1]
            / '.scratch/ticket14-first-request-20261020/run_once.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        calls = []
        def sender(wire, *, deadline_ms):
            calls.append(True)
            raise OSError('PUBLIC PRIVATE PROVIDER TEXT')
        result = entry.diagnose(public_request(), {'wire_utf8': '{}'}, sender=sender, clock=lambda: 1000)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(result['usage']['input_tokens'])
        self.assertIsNone(result['usage']['output_tokens'])
        self.assertIsNone(result['usage']['cost_microusd'])
        self.assertEqual(result['usage_diagnostic'], {'state': 'unknown', 'usage': None})
        self.assertEqual(result['metering_status'], 'unknown/incomplete')
        self.assertNotIn('PRIVATE PROVIDER TEXT', str(result))

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
