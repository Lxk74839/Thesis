"""PUBLIC R/S/M integration only; never a live experiment."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE_BINDING = {'execution_kind': 'fourrouter_responses', 'model_id': 'gpt-6-luna',
    'channel': '4Router', 'base_url': 'https://4router.net/v1', 'project_id': 'PUBLIC-P1',
    'provenance': 'fixture', 'max_request_bytes': 2 * 1024**2,
    'context_token_limit': 100000, 'max_output_tokens': 8192,
    'pricing': {'input_microusd_per_million': 1000000, 'output_microusd_per_million': 1000000,
                'cached_microusd_per_million': 1000000}}


class PublicCounter:
    def count(self, prepared, *, authorization):
        from provider_openai import sha
        receipt = {'status': 'counted', 'basis': 'fixture', 'input_tokens': 100,
            'prepared_id': prepared['prepared_id'], 'wire_sha256': prepared['wire_sha256'],
            'model_id': 'gpt-6-luna', 'project_id': 'PUBLIC-P1'}
        return receipt | {'receipt_id': sha(receipt)}


class RouterHTTPFixture:
    def __init__(self):
        from tests.test_batched_recommendation import BatchTransport
        self.script, self.wires = BatchTransport(), []

    def __call__(self, text, *, deadline_ms):
        wire = json.loads(text)
        self.wires.append(wire)
        messages = []
        for item in wire['input']:
            if 'role' in item:
                try:
                    content = json.loads(item['content'])
                except ValueError:
                    content = item['content']
                messages.append({'role': item['role'], 'content': content})
            elif item['type'] == 'function_call':
                messages.append({'role': 'assistant', 'content': None, 'tool_requests': [{
                    'call_id': item['call_id'], 'name': item['name'], 'arguments': json.loads(item['arguments'])}]})
            else:
                messages.append({'role': 'tool', 'tool_call_id': item['call_id'], 'content': json.loads(item['output'])})
        req = {'messages': messages, 'tools': wire['tools'],
            'output_kind': wire['text']['format']['name'].removeprefix('rsm_'),
            'attempt_id': 'PUBLIC-' + str(len(self.wires)), 'request_id': 'PUBLIC', 'run_id': 'PUBLIC'}
        message = self.script(req)['message']
        output = ([{'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                    'arguments': json.dumps(c['arguments'])} for c in message['tool_requests']]
            if message['tool_requests'] else [{'type': 'message', 'content': [{'type': 'output_text',
                'text': json.dumps(message['content'], ensure_ascii=False)}]}])
        return {'http_status': 200, 'request_id': 'PUBLIC-HTTP', 'body': {'model': 'gpt-6-luna',
            'status': 'completed', 'id': 'PUBLIC-RESPONSE', 'output': output,
            'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130}}}


def setUpModule():
    def boundary(event, args):
        if event.startswith('socket.'):
            raise OSError('P1_offline_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).resolve()
            if path.is_relative_to(PROJECT / '.secrets') or '/private/' in path.as_posix():
                raise OSError('P1_offline_private_forbidden')
    sys.addaudithook(boundary)


class P1Wiring(unittest.TestCase):
    def test_native_usage_diagnostic_distinguishes_absent_null_rejected_and_accepted(self):
        from provider_fourrouter import usage_diagnostic
        for body, expected in ((None, 'unknown'), ({}, 'field_absent'), ({'usage': None}, 'value_null'),
                ({'usage': {'input_tokens': 'PUBLIC-secret'}}, 'parser_rejected'),
                ({'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130}}, 'accepted')):
            result = usage_diagnostic(body)
            self.assertEqual(result['state'], expected)
            self.assertNotIn('PUBLIC-secret', json.dumps(result))

    def test_adapter_maps_existing_role_and_tools_only_to_exact_4Router_model(self):
        from model_adapter import ModelAdapter
        from tests.provider_fixtures import request
        req = request()
        req.update(execution_kind='fourrouter_responses', model_id='gpt-6-luna')
        binding = {'execution_kind': 'fourrouter_responses', 'model_id': 'gpt-6-luna',
            'channel': '4Router', 'base_url': 'https://4router.net/v1',
            'project_id': 'PUBLIC-P1', 'provenance': 'fixture'}
        adapter = ModelAdapter(None, capability_binding=binding)
        prepared = adapter.prepare(req)
        self.assertEqual(prepared['status'], 'prepared')
        self.assertEqual(prepared['wire_body']['model'], 'gpt-6-luna')
        self.assertEqual(prepared['wire_body']['input'][-1]['call_id'], 'PUBLIC-CALL')
        self.assertEqual(prepared['wire_body']['tools'][0]['name'], 'list_evidence')
        self.assertTrue(prepared['wire_body']['text']['format']['strict'])
        self.assertIsNone(prepared['input_tokens'])
        self.assertNotIn('gpt-5.4', prepared['wire_utf8'])

    def test_live_adapter_refuses_unknown_count_rates_budget_and_authorization_before_transport(self):
        from model_adapter import ModelAdapter
        calls = []
        binding = {'execution_kind': 'fourrouter_responses', 'model_id': 'gpt-6-luna',
            'channel': '4Router', 'base_url': 'https://4router.net/v1', 'project_id': 'P1',
            'provenance': '4router', 'pricing': None, 'api_budget_microusd': None,
            'execution_authorized': False, 'max_request_bytes': None}
        result = ModelAdapter(lambda *a, **k: calls.append(1), capability_binding=binding).invoke({})
        self.assertEqual(result['status'], 'not_started')
        self.assertTrue({'verified_full_input_count', 'pricing', 'api_budget_microusd',
                         'execution_authorization', 'max_request_bytes'} <= set(result['missing']))
        self.assertFalse(result['attempted'])
        self.assertTrue(all(v is None for v in result['usage'].values()))
        self.assertEqual(calls, [])

    def test_existing_R_S_M_pipeline_uses_exact_model_and_keeps_six_roles_and_publication(self):
        from tests.runtime_fixtures import RuntimeFixture
        from model_adapter import ModelAdapter
        parent = PROJECT / '.tmp/recommendation-runtime/p1-wiring'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp))
            fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
            for method in ('R', 'S', 'M'):
                http = RouterHTTPFixture()
                model = None if method == 'R' else ModelAdapter(http,
                    capability_binding=FIXTURE_BINDING, counter=PublicCounter())
                run = fixture.make(method, model=model, binding_changes={
                    'schema_version': 'rsm-run-0.4.0', 'execution_kind': 'fourrouter_responses',
                    'project_id': 'PUBLIC-P1', 'plan_source_scope': 'public_fixture',
                    'orchestration': 'batch32-0.1.0'})
                result = run.run()
                self.assertEqual(result['terminal'], 'released', (method, result.get('reason')))
                self.assertEqual(set(result['binding']['C']), {'PUBLIC-A', 'PUBLIC-B'})
                self.assertEqual(result['budget']['usage']['model_calls'], len(http.wires))
                self.assertEqual(len(http.wires), 0 if method == 'R' else 9)
                self.assertEqual(result['budget']['usage']['cost_microusd'], 0 if method == 'R' else 1170)
                if method == 'M':
                    self.assertEqual(len(result['roles_completed']), 6)
                self.assertTrue(all(w['model'] == 'gpt-6-luna' for w in http.wires))
                self.assertTrue(Path(result['publication_path']).exists())

    def test_P1_draft_refuses_all_three_real_tasks_without_assembly_credentials_or_HTTP(self):
        from p1_runtime import prepare_p1, execute_p1, DEFAULT_CONFIG
        for method in ('R', 'S', 'M'):
            result = prepare_p1(DEFAULT_CONFIG, method)
            self.assertEqual(result['terminal'], 'not_started')
            self.assertFalse(result['started'])
            self.assertIn('execution_authorization', result['missing'])
            self.assertEqual(result['provider_requests_sent'], 0)
            if method != 'R':
                self.assertIn('verified_full_input_count', result['missing'])
                self.assertIn('pricing', result['missing'])
            self.assertEqual(execute_p1(DEFAULT_CONFIG, method), result)

    def test_real_sender_bridge_uses_existing_HTTP_boundary_only_when_called(self):
        from provider_fourrouter import make_sender
        parent = PROJECT / '.tmp/recommendation-runtime/p1-auth'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            credential = Path(tmp) / 'PUBLIC-key.json'
            calls = []
            def http(endpoint, body, key, timeout, **kwargs):
                calls.append((endpoint, body, key, timeout, kwargs))
                return {'http_status': 200, 'request_id': key, 'body': {'model': 'gpt-6-luna', 'id': key}}
            sender = make_sender(clock=lambda: 0, max_request_bytes=2 * 1024**2,
                                 credential_path=credential, http_sender=http)
            self.assertEqual(calls, [])
            credential.write_text('{"api_key":"PUBLIC-SYNTHETIC-KEY"}', encoding='utf-8')
            reply = sender('{"model":"gpt-6-luna","input":["PUBLIC"]}', deadline_ms=45000)
            self.assertEqual(calls[0][0], 'https://4router.net/v1/responses')
            self.assertEqual(calls[0][3], 30)
            self.assertEqual(calls[0][4]['max_request_bytes'], 2 * 1024**2)
            self.assertNotIn('PUBLIC-SYNTHETIC-KEY', json.dumps(reply))

    def test_fixture_capability_cannot_be_used_to_authorize_real_D1(self):
        from p1_runtime import prepare_p1, DEFAULT_CONFIG
        parent = PROJECT / '.tmp/recommendation-runtime/p1-config'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            cfg = json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8'))
            cfg['model_binding']['provenance'] = 'fixture'
            path = Path(tmp) / 'PUBLIC-config.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            self.assertIn('fixture_cannot_authorize_D1', prepare_p1(path, 'M', counter=PublicCounter())['missing'])

    def test_absent_null_or_rejected_usage_stops_after_one_fixture_response_without_leaking_raw(self):
        from tests.runtime_fixtures import RuntimeFixture
        from model_adapter import ModelAdapter
        parent = PROJECT / '.tmp/recommendation-runtime/p1-usage'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp))
            for state in ('field_absent', 'value_null', 'parser_rejected'):
                http = RouterHTTPFixture()
                def sender(text, *, deadline_ms):
                    reply = http(text, deadline_ms=deadline_ms)
                    if state == 'field_absent':
                        reply['body'].pop('usage')
                    else:
                        reply['body']['usage'] = None if state == 'value_null' else {'input_tokens': 'PUBLIC-secret'}
                    return reply
                model = ModelAdapter(sender, capability_binding=FIXTURE_BINDING, counter=PublicCounter())
                run = fixture.make('M', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                    'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                    'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
                result = run.run()
                self.assertEqual((result['terminal'], len(http.wires)), ('failed_model', 1))
                response = run.state['messages'][0]['response']
                self.assertEqual(response['usage_diagnostic']['state'], state)
                self.assertIsNone(response['usage']['cost_microusd'])
                self.assertFalse(response['error']['retryable'])
                self.assertNotIn('PUBLIC-secret', json.dumps(run.audit_view(), ensure_ascii=False))

    def test_empty_root_budget_and_reserve_remain_missing(self):
        from p1_runtime import prepare_p1, DEFAULT_CONFIG
        parent = PROJECT / '.tmp/recommendation-runtime/p1-limits'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            cfg = json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8'))
            cfg['limits']['R'], cfg['final_reserve']['R'] = {}, {}
            path = Path(tmp) / 'PUBLIC-limits.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            missing = prepare_p1(path, 'R')['missing']
            self.assertTrue({'limits', 'final_reserve'} <= set(missing))

    def test_runtime_factory_constructs_shared_sessions_without_reading_credentials(self):
        from p1_runtime import build_runtime
        from tests.runtime_fixtures import RuntimeFixture
        parent = PROJECT / '.tmp/recommendation-runtime/p1-factory'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp))
            source = fixture.make('R')
            assembly = {'binding': source.binding | {'safe_initial_messages': source.initial_messages},
                'root': {'root_task_id': 'PUBLIC-ROOT', 'H': fixture.history, 'S': [],
                         'H_sha256': source.binding['H_sha256']},
                'candidates': {'C': fixture.parents, 'b': fixture.scores, 'batches': fixture.batches,
                               'background_statistics': [{} for p in fixture.parents]},
                'catalog': [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in fixture.parents],
                'view': {'arm': 'necessary', 'request': {'design_text': 'PUBLIC R1 AND R5', 'necessary_clauses': ['c1', 'c2']}},
                'snapshot_ref': source.evidence.source.snapshot_ref}
            cfg = {'limits': {'R': source.budget.limits}, 'final_reserve': {'R': source.budget.final_reserve},
                   'model_binding': FIXTURE_BINDING}
            built = build_runtime(assembly, cfg, 'R', counter=None, output_root=Path(tmp) / 'built')
            self.assertEqual(built.binding['C'], fixture.parents)
            self.assertIsNone(built.model)
            self.assertIs(built.evidence.root_budget, built.budget)
            self.assertIsInstance(built.budget.clock(), (int, float))

    def test_known_native_tokens_survive_unknown_cached_usage_and_cost(self):
        from provider_fourrouter import normalized_usage
        pricing = dict(FIXTURE_BINDING['pricing'], cached_microusd_per_million=500000)
        usage = normalized_usage({'body': {'usage': {'input_tokens': 100, 'output_tokens': 30,
                                                    'total_tokens': 130}}}, pricing=pricing)
        self.assertEqual((usage['input_tokens'], usage['output_tokens']), (100, 30))
        self.assertIsNone(usage['cached_input_tokens'])
        self.assertIsNone(usage['cost_microusd'])
