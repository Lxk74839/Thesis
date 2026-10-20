"""PUBLIC-only HTTP/process seams; actual credentials and network are forbidden."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import contextlib
import io
import copy

from tests.test_fourrouter_probe import setUpModule


class LiveProbe(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.tmp/manual-4router'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public, self.credentials = self.root / 'public.json', self.root / 'PUBLIC-key.json'
        self.receipt = self.root / 'receipt.jsonl'
        self.public.write_text(json.dumps({'model_binding': {'channel': '4Router',
            'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna'}}), encoding='utf-8')
        self.credentials.write_text('{"api_key":"PUBLIC-SYNTHETIC-KEY"}', encoding='utf-8')
        self.replies = [
            {'http_status': 200, 'request_id': 'PUBLIC-http-1', 'body': {
                'status': 'completed', 'model': 'gpt-6-luna', 'id': 'resp_PUBLIC_1',
                'usage': {'input_tokens': 40, 'output_tokens': 12, 'total_tokens': 52,
                          'input_tokens_details': {'cached_tokens': 0}},
                'output': [{'type': 'function_call', 'id': 'fc_PUBLIC_1', 'call_id': 'call_PUBLIC_1',
                    'name': 'read_evidence', 'arguments': '{"evidence_refs":["PUBLIC-REF-1"]}'}]}},
            {'http_status': 200, 'request_id': 'PUBLIC-http-2', 'body': {
                'status': 'completed', 'model': 'gpt-6-luna', 'id': 'resp_PUBLIC_2',
                'usage': {'input_tokens': 65, 'output_tokens': 20, 'total_tokens': 85},
                'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': '{"probe":"PUBLIC-4ROUTER","result":"PUBLIC-OK"}'}]}]}}]

    def test_live_roundtrip_records_native_metadata_without_secret_or_response_text(self):
        from fourrouter_probe import run_live_probe
        calls = []
        def sender(endpoint, body, key, timeout):
            calls.append((endpoint, body, timeout))
            self.assertEqual(key, 'PUBLIC-SYNTHETIC-KEY')
            return self.replies[len(calls)-1]
        result = run_live_probe(public_path=self.public, credential_path=self.credentials,
                                receipt_path=self.receipt, sender=sender)
        self.assertEqual((result['status'], result['send_attempts'], result['provider_requests_sent']),
                         ('protocol_passed', 2, 2))
        self.assertEqual(result['provenance'], 'live_HTTP')
        self.assertTrue(result['tool_call_valid'])
        self.assertTrue(result['tool_result_sent'])
        self.assertTrue(result['strict_json_valid'])
        self.assertIsNone(result['cost'])
        self.assertEqual(result['responses'][0]['usage']['input_tokens'], 40)
        self.assertEqual(result['responses'][1]['request_id'], 'PUBLIC-http-2')
        self.assertEqual(result['responses'][0]['response_id'], 'resp_PUBLIC_1')
        self.assertEqual(calls[1][1]['input'][-1]['call_id'], 'call_PUBLIC_1')
        self.assertTrue(all(0 < c[2] <= 30 for c in calls))
        raw = self.receipt.read_text(encoding='utf-8')
        for prohibited in ('PUBLIC-SYNTHETIC-KEY', 'Authorization', 'output_text', 'arguments'):
            self.assertNotIn(prohibited, raw)
        self.assertEqual(json.loads(raw.splitlines()[-1]), result)

    def test_unknown_send_state_stops_once_and_records_null_without_exception_text(self):
        from fourrouter_probe import run_live_probe
        attempts = []
        def sender(*args):
            attempts.append(1)
            raise TimeoutError('PUBLIC-SYNTHETIC-KEY Authorization')
        result = run_live_probe(public_path=self.public, credential_path=self.credentials,
                                receipt_path=self.receipt, sender=sender)
        self.assertEqual((result['status'], result['send_attempts'], len(attempts)), ('protocol_failed', 1, 1))
        self.assertIsNone(result['provider_requests_sent'])
        self.assertEqual(len(result['responses']), 1)
        self.assertIsNone(result['responses'][0]['http_status'])
        self.assertEqual(result['responses'][0]['send_state'], 'unknown')
        self.assertNotIn('PUBLIC-SYNTHETIC-KEY', self.receipt.read_text(encoding='utf-8'))

    def test_sender_bounds_process_time_and_keeps_key_out_of_arguments_without_retry(self):
        from fourrouter_probe import send_response
        calls = []
        def process_run(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, stdout=b'{"http_status":302,"body":null,"request_id":null}')
        reply = send_response('https://4router.net/v1/responses', {'model': 'gpt-6-luna'},
                              'PUBLIC-SYNTHETIC-KEY', 0.25, process_run=process_run)
        self.assertEqual((reply['http_status'], len(calls)), (302, 1))
        self.assertNotIn('PUBLIC-SYNTHETIC-KEY', repr(calls[0][0]))
        self.assertIn(b'PUBLIC-SYNTHETIC-KEY', calls[0][1]['input'])
        self.assertEqual((calls[0][1]['timeout'], calls[0][1]['stderr']), (0.25, subprocess.DEVNULL))
        def timed_out(args, **kwargs):
            calls.append((args, kwargs))
            raise subprocess.TimeoutExpired(args, kwargs['timeout'], output=b'PUBLIC-SYNTHETIC-KEY')
        reply = send_response('https://4router.net/v1/responses', {}, 'PUBLIC-SYNTHETIC-KEY',
                              0.25, process_run=timed_out)
        self.assertIsNone(reply['http_status'])
        self.assertEqual(len(calls), 2)
        self.assertNotIn('PUBLIC-SYNTHETIC-KEY', json.dumps(reply))

    def test_authorized_CLI_consumes_one_receipt_and_never_restarts(self):
        from fourrouter_probe import main
        calls = []
        def sender(*args):
            calls.append(args)
            return self.replies[len(calls)-1]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['probe'], public_path=self.public, credential_path=self.credentials,
                        receipt_path=self.receipt, sender=sender)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'protocol_passed')
        self.assertNotIn('PUBLIC-SYNTHETIC-KEY', output.getvalue())
        self.credentials.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['probe'], public_path=self.public, credential_path=self.credentials,
                        receipt_path=self.receipt, sender=sender)
        self.assertEqual((code, len(calls), json.loads(output.getvalue())['status']),
                         (2, 2, 'authorization_already_consumed'))

    def test_redirect_wrong_model_or_invalid_tool_never_reaches_second_request(self):
        from fourrouter_probe import run_live_probe
        for case in ('redirect', 'model', 'tool'):
            reply = copy.deepcopy(self.replies[0])
            if case == 'redirect':
                reply['http_status'] = 302
            elif case == 'model':
                reply['body']['model'] = 'PUBLIC-other-model'
            else:
                reply['body']['output'][0]['name'] = 'PUBLIC-other-tool'
            calls = []
            def sender(*args):
                calls.append(args)
                return reply
            result = run_live_probe(public_path=self.public, credential_path=self.credentials,
                receipt_path=self.root / (case + '.jsonl'), sender=sender)
            self.assertEqual((result['status'], result['provider_requests_sent'], len(calls)),
                             ('protocol_failed', 1, 1))
            self.assertFalse(result['tool_result_sent'])

    def test_total_deadline_prevents_the_second_dispatch(self):
        from fourrouter_probe import run_live_probe
        times = iter((0, 0, 60, 60))
        calls = []
        def sender(*args):
            calls.append(args)
            return self.replies[0]
        result = run_live_probe(public_path=self.public, credential_path=self.credentials,
            receipt_path=self.receipt, sender=sender, clock=lambda: next(times))
        self.assertEqual((result['status'], result['send_attempts'], len(calls)), ('protocol_failed', 1, 1))
        self.assertEqual(result['error'], 'total_deadline')
        self.assertTrue(result['tool_call_valid'])
        self.assertFalse(result['tool_result_sent'])

    def test_uncertain_tool_result_and_untrusted_metadata_remain_null(self):
        from fourrouter_probe import run_live_probe
        calls = []
        def sender(*args):
            calls.append(args)
            if len(calls) == 1:
                return self.replies[0]
            raise OSError('PUBLIC-SYNTHETIC-KEY')
        result = run_live_probe(public_path=self.public, credential_path=self.credentials,
            receipt_path=self.receipt, sender=sender)
        self.assertEqual((result['status'], len(calls)), ('protocol_failed', 2))
        self.assertIsNone(result['provider_requests_sent'])
        self.assertIsNone(result['tool_result_sent'])
        self.assertFalse(result['strict_json_valid'])
        reply = copy.deepcopy(self.replies[0])
        reply['body'].update(model='PUBLIC-SYNTHETIC-KEY', id='PUBLIC-SYNTHETIC-KEY',
                             usage={'untrusted': 'PUBLIC-SYNTHETIC-KEY'})
        reply['request_id'] = 'PUBLIC-SYNTHETIC-KEY'
        result = run_live_probe(public_path=self.public, credential_path=self.credentials,
            receipt_path=self.root / 'redacted.jsonl', sender=lambda *args: reply)
        self.assertTrue(all(result['responses'][0][k] is None for k in ('model','response_id','usage','request_id')))
        self.assertNotIn('PUBLIC-SYNTHETIC-KEY', (self.root / 'redacted.jsonl').read_text(encoding='utf-8'))

    def test_HTTP_boundary_returns_redirect_and_worker_rejects_other_hosts(self):
        from fourrouter_probe import http_response, send_response
        calls = []
        class Connection:
            def __init__(self, host, **kwargs):
                self.host = host
            def request(self, method, path, **kwargs):
                calls.append((self.host, method, path, kwargs))
            def getresponse(self):
                return self
            status = 302
            def getheader(self, name):
                return 'PUBLIC-http-redirect'
            def read(self, limit):
                return b'{}'
            def close(self):
                pass
        result = http_response('https://4router.net/v1/responses', {'model':'gpt-6-luna'},
            'PUBLIC-SYNTHETIC-KEY', 30, connection_factory=Connection)
        self.assertEqual((result['http_status'], len(calls)), (302, 1))
        self.assertEqual(calls[0][:3], ('4router.net', 'POST', '/v1/responses'))
        result = send_response('https://PUBLIC.invalid/v1/responses', {}, 'PUBLIC-SYNTHETIC-KEY', 2)
        self.assertEqual(result, {'http_status': None, 'body': None, 'request_id': None})


if __name__ == '__main__':
    unittest.main()
