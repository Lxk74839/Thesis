"""Only PUBLIC files and injected transport; never read the user's credential."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys


PROJECT = Path(__file__).resolve().parents[1]


def setUpModule():
    def boundary(event, args):
        if event.startswith('socket.'):
            raise OSError('PUBLIC_tests_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes)):
            path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve()
            if any(path.is_relative_to(PROJECT / root) for root in ('data', 'research', 'manuscript', '.secrets')):
                raise OSError('PUBLIC_tests_private_read_forbidden')
    sys.addaudithook(boundary)


class ManualProbe(unittest.TestCase):
    def setUp(self):
        parent = PROJECT / '.tmp/manual-4router'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / 'public.json'
        self.credentials = self.root / 'PUBLIC-credential.json'
        self.public.write_text(json.dumps({'model_binding': {'channel': '4Router',
            'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna',
            'pricing': None, 'api_budget': None}, 'token_group': None}), encoding='utf-8')
        self.credentials.write_text('{"api_key":""}', encoding='utf-8')

    def test_check_distinguishes_empty_and_filled_without_disclosing_the_value(self):
        from fourrouter_probe import main
        for value, filled in (('', False), ('PUBLIC-SYNTHETIC-KEY', True)):
            self.credentials.write_text(json.dumps({'api_key': value}), encoding='utf-8')
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(['check'], public_path=self.public, credential_path=self.credentials)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), {'api_key_filled': filled, 'local_config_valid': True})
            self.assertNotIn('PUBLIC-SYNTHETIC-KEY', stdout.getvalue()+stderr.getvalue())
            self.assertEqual(stderr.getvalue(), '')

    def test_invalid_configuration_and_malformed_secret_only_return_booleans(self):
        from fourrouter_probe import main
        for raw in ('{"api_key": "PUBLIC-SYNTHETIC-KEY"', '{"api_key": 5}', '[]'):
            self.credentials.write_text(raw, encoding='utf-8')
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(['check'], public_path=self.public, credential_path=self.credentials)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stdout.getvalue()), {'api_key_filled': False, 'local_config_valid': False})
            self.assertNotIn('PUBLIC-SYNTHETIC-KEY', stdout.getvalue()+stderr.getvalue())
            self.assertEqual(stderr.getvalue(), '')

    def test_prepare_reuses_public_model_and_endpoint_without_credentials_or_data(self):
        from fourrouter_probe import prepare_probe
        prepared = prepare_probe(public_path=self.public)
        self.assertEqual(prepared['endpoint'], 'https://4router.net/v1/responses')
        self.assertEqual(prepared['request']['model'], 'gpt-6-luna')
        self.assertEqual(prepared['request']['reasoning'], {'effort': 'none'})
        self.assertEqual((prepared['max_generate_requests'], prepared['max_count_requests']), (2, 0))
        self.assertIsNone(prepared['cost'])
        self.assertFalse(prepared['execution_authorized'])
        self.assertEqual(prepared['request']['tools'][0]['name'], 'read_evidence')
        self.assertTrue(prepared['request']['text']['format']['strict'])
        self.assertIn('PUBLIC-REF-1', json.dumps(prepared['request']))
        self.assertNotIn('api_key', json.dumps(prepared))

    def test_probe_refuses_empty_PUBLIC_credentials_without_sending(self):
        from fourrouter_probe import main
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(['probe'], public_path=self.public, credential_path=self.credentials,
                        receipt_path=self.root / 'unused.jsonl')
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'invalid_local_configuration')
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertIsNone(result['cost'])

    def test_PUBLIC_fixture_roundtrip_pairs_tool_output_then_validates_strict_JSON(self):
        from fourrouter_probe import run_fixture_probe
        responses = [
            {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'function_call',
                'id': 'fc_PUBLIC_1', 'call_id': 'call_PUBLIC_1', 'name': 'read_evidence',
                'arguments': '{"evidence_refs":["PUBLIC-REF-1"]}'}]},
            {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'message',
                'content': [{'type': 'output_text', 'text': '{"probe":"PUBLIC-4ROUTER","result":"PUBLIC-OK"}'}]}]}]
        calls = []
        def transport(endpoint, body):
            calls.append((endpoint, body))
            return responses[len(calls)-1]
        result = run_fixture_probe(transport, public_path=self.public)
        self.assertEqual((result['status'], result['fixture_calls'], result['provenance']), ('fixture_passed', 2, 'fixture'))
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertIsNone(result['cost'])
        self.assertEqual(calls[1][1]['input'][-1], {'type': 'function_call_output',
            'call_id': 'call_PUBLIC_1', 'output': '{"marker": "PUBLIC-OK"}'})
        self.assertEqual(calls[1][1]['input'][-2]['id'], 'fc_PUBLIC_1')
        self.assertEqual(calls[1][1]['tool_choice'], 'none')

    def test_unsupported_tool_or_continuation_stops_after_one_fixture_call(self):
        from fourrouter_probe import run_fixture_probe
        for output in ([{'type': 'function_call', 'call_id': 'PUBLIC-call', 'name': 'other_tool',
                         'arguments': '{}'}], [{'type': 'reasoning', 'id': 'PUBLIC-opaque'}]):
            calls = []
            def transport(endpoint, body):
                calls.append(body)
                return {'status': 'completed', 'model': 'gpt-6-luna', 'output': output}
            result = run_fixture_probe(transport, public_path=self.public)
            self.assertEqual((result['status'], result['fixture_calls'], len(calls)), ('fixture_failed', 1, 1))
            self.assertEqual(result['error'], 'first_response')

    def test_extra_final_JSON_field_is_rejected_and_never_retried(self):
        from fourrouter_probe import run_fixture_probe
        replies = [
            {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'function_call',
                'call_id': 'PUBLIC-call', 'name': 'read_evidence', 'arguments': '{"evidence_refs":["PUBLIC-REF-1"]}'}]},
            {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': '{"probe":"PUBLIC-4ROUTER","result":"PUBLIC-OK","extra":1}'}]}]}]
        calls = []
        def transport(endpoint, body):
            calls.append(body)
            return replies[len(calls)-1]
        result = run_fixture_probe(transport, public_path=self.public)
        self.assertEqual((result['status'], result['fixture_calls'], len(calls)), ('fixture_failed', 2, 2))
        self.assertEqual(result['error'], 'final_response')
        self.assertIsNone(result['cost'])

    def test_wrong_endpoint_or_model_is_invalid_without_loading_legacy_defaults(self):
        from fourrouter_probe import check_config
        self.public.write_text('{"model_binding":{"channel":"4Router","base_url":"https://wrong.example/v1",'
                               '"model_id":"old-model"}}', encoding='utf-8')
        self.assertEqual(check_config(public_path=self.public, credential_path=self.credentials),
                         {'api_key_filled': False, 'local_config_valid': False})

    def test_missing_or_unsafe_secret_and_unsupported_CLI_arguments_never_echo_content(self):
        from fourrouter_probe import main, check_config
        self.assertFalse(check_config(public_path=self.public, credential_path=self.root / 'missing.json')['local_config_valid'])
        self.credentials.write_text('{"api_key":"PUBLIC-KEY\\r\\ninvalid"}', encoding='utf-8')
        self.assertEqual(check_config(public_path=self.public, credential_path=self.credentials),
                         {'api_key_filled': True, 'local_config_valid': False})
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(['--api-key', 'PUBLIC-KEY'], public_path=self.public, credential_path=self.credentials)
        self.assertEqual((code, json.loads(stdout.getvalue()), stderr.getvalue()), (2, {'status': 'invalid_command'}, ''))

    def test_prepare_CLI_only_emits_PUBLIC_preparation(self):
        from fourrouter_probe import main
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(['prepare'], public_path=self.public, credential_path=PROJECT / '.secrets/4router.json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())['status'], 'prepared_offline')
        self.assertNotIn('api_key', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
