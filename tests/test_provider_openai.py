"""Public preparation/invocation contracts; HTTP and counts are external fixtures."""
import json
import unittest

from model_adapter import ModelAdapter
from tests.provider_fixtures import BINDING, FINAL_SCHEMA, MODEL, NativeScriptedSender, case_directory, native_response, request, reserved_native, save
from tests.runtime_fixtures import RuntimeFixture
from token_counting import InputCounter


class OpenAINativeTests(unittest.TestCase):
    def test_unrequested_hosted_tool_output_cannot_be_hidden_behind_a_valid_message(self):
        def sender(body, **kw):
            response = native_response()
            response['body']['output'].insert(0, {'type': 'web_search_call', 'id': 'PUBLIC-UNREQUESTED-TOOL'})
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'unsupported_provider_tool')
        self.assertIsNone(result['usage']['cost_microusd'])
        self.assertFalse(result['error']['retryable'])
        save(root / 'result.json', result)

    def test_native_S_and_M_quality_projection_share_history_and_preserve_components(self):
        for method in ('S', 'M'):
            with self.subTest(method=method):
                sender = NativeScriptedSender()
                model = ModelAdapter(sender, capability_binding=BINDING,
                                     counter=InputCounter('PUBLIC-PROJECT', fixture_count=100))
                fixture = RuntimeFixture(case_directory('native-quality-' + method))
                fixture.quality()
                fixture.history = [{'review_text': 'PUBLIC rice preference', 'rating': 4}]
                result = fixture.make(method, model=model, arm='quality', prefix=2,
                    binding_changes={'schema_version': 'rsm-run-0.2.0', 'execution_kind': 'openai_native_fixture',
                        'orchestration': 'batch32-0.1.0', 'project_id': 'PUBLIC-PROJECT'},
                    limits={'input_tokens': 1000, 'output_tokens': 20000, 'cost_microusd': 100000},
                    final_reserve={'input_tokens': 100, 'output_tokens': 1500, 'cost_microusd': 6825}).run()
                self.assertEqual(result['terminal'], 'released', (result['terminal'], result['reason']))
                self.assertEqual(result['budget']['usage']['input_tokens'], 900)
                self.assertEqual(result['binding']['C'], ['PUBLIC-A', 'PUBLIC-B'])
                if method == 'M':
                    self.assertEqual(result['components']['full']['topK'], result['delivered'])
                    self.assertEqual(result['components']['full']['anchor']['execution_kind'], 'openai_native_fixture')
                frames = [json.loads(i['content'])['runtime'] for w in sender.wires for i in w['input']
                    if i.get('role') == 'user' and isinstance(json.loads(i['content']), dict) and 'runtime' in json.loads(i['content'])]
                self.assertTrue(all(frame['history'] == fixture.history for frame in frames))

    def test_wrong_returned_model_keeps_fee_unknown_instead_of_pricing_it_as_the_bound_model(self):
        def sender(body, **kw):
            response = native_response()
            response['body']['model'] = 'UNBOUND-PUBLIC-MODEL'
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'provider_binding_mismatch')
        self.assertIsNone(result['usage']['cost_microusd'])
        self.assertEqual(result['usage']['input_tokens'], 100)
        self.assertFalse(result['usage_known'])
        self.assertFalse(result['error']['retryable'])
        save(root / 'result.json', result)

    def test_malformed_native_envelope_is_a_recorded_failure_with_unknown_usage(self):
        adapter, req, root = reserved_native(lambda body, **kw: {
            'status_code': 200, 'headers': None, 'body': {'output': [None]}})
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'format_error')
        self.assertFalse(result['usage_known'])
        self.assertIsNone(result['usage']['input_tokens'])
        self.assertEqual(result['raw_response']['body']['output'], [None])
        save(root / 'result.json', result)

    def test_late_native_result_keeps_usage_and_is_not_released_as_success(self):
        now = [0]
        def sender(body, *, deadline_ms):
            now[0] = 45001
            return native_response()
        adapter, req, root = reserved_native(sender, now=now)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'timeout')
        self.assertTrue(result['usage_known'])
        self.assertEqual(result['usage']['cost_microusd'], 183)
        self.assertTrue(result['late'])
        save(root / 'result.json', result)

    def test_invocation_cannot_extend_the_reserved_deadline_into_unreserved_time(self):
        sends = []
        def sender(body, *, deadline_ms):
            sends.append(body)
            return native_response()
        adapter, req, _ = reserved_native(sender)
        req['deadline_ms'] = 90000
        self.assertEqual(adapter.invoke(req)['status'], 'preflight_denied')
        self.assertEqual(sends, [])

    def test_native_runtime_six_roles_use_complete_fixture_counts_in_the_shared_budget(self):
        sender = NativeScriptedSender()
        model = ModelAdapter(sender, capability_binding=BINDING, counter=InputCounter('PUBLIC-PROJECT', fixture_count=100))
        fixture = RuntimeFixture(case_directory('native-runtime'))
        result = fixture.make('M', model=model, binding_changes={'schema_version': 'rsm-run-0.2.0',
            'execution_kind': 'openai_native_fixture', 'orchestration': 'batch32-0.1.0', 'project_id': 'PUBLIC-PROJECT'},
            limits={'input_tokens': 1000, 'output_tokens': 20000, 'cost_microusd': 100000},
            final_reserve={'input_tokens': 100, 'output_tokens': 1500, 'cost_microusd': 6825}).run()
        self.assertEqual(result['terminal'], 'released', (result['terminal'], result['reason']))
        self.assertEqual(len(result['roles_completed']), 6)
        self.assertEqual((result['budget']['usage']['model_calls'], result['budget']['usage']['input_tokens'],
            result['budget']['usage']['output_tokens'], result['budget']['usage']['cost_microusd']), (9, 900, 270, 1890))
        self.assertEqual(result['delivered'], ['PUBLIC-A'])
        self.assertEqual(len(sender.wires), 9)
        self.assertTrue(all(m['usage_basis'] == 'fixture' and m['response']['provider_requests_sent'] == 0 for m in result['messages']))
        self.assertEqual(result['versions']['adapter'], 'rsm-model-adapter-native-0.1.0')

    def test_native_runtime_stops_on_missing_count_without_spending_a_model_or_final_slot(self):
        sends = []
        model = ModelAdapter(lambda *a, **kw: sends.append(a), capability_binding=BINDING,
                             counter=InputCounter('PUBLIC-PROJECT'))
        fixture = RuntimeFixture(case_directory('native-missing-count'))
        run = fixture.make('M', model=model, binding_changes={'schema_version': 'rsm-run-0.2.0',
            'execution_kind': 'openai_native_fixture', 'orchestration': 'batch32-0.1.0', 'project_id': 'PUBLIC-PROJECT'})
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('incomplete_count', 'count_missing'))
        self.assertEqual(result['budget']['usage']['model_calls'], 0)
        self.assertEqual(result['budget']['final_reserve']['model_calls'], 1)
        self.assertEqual(result['preparations'][0]['count']['input_tokens'], None)
        self.assertEqual(sends, [])

    def test_native_refusal_incomplete_and_rate_limit_keep_truthful_usage(self):
        for expected in ('refusal', 'truncated', 'rate_limit'):
            with self.subTest(expected=expected):
                def sender(body, *, deadline_ms):
                    response = native_response()
                    if expected == 'refusal':
                        response['body']['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'public refusal'}]
                    elif expected == 'truncated':
                        response['body']['status'] = 'incomplete'
                        response['body']['incomplete_details'] = {'reason': 'max_output_tokens'}
                    else:
                        response['status_code'] = 429
                        response['body']['usage'] = None
                        response['body']['error'] = {'code': 'rate_limit_exceeded'}
                    return response
                adapter, req, root = reserved_native(sender)
                result = adapter.invoke(req)
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['usage_known'], expected != 'rate_limit')
                self.assertEqual(result['provider_request_id'], 'PUBLIC-HTTP-ID')
                self.assertEqual(result['raw_response']['status_code'], 429 if expected == 'rate_limit' else 200)
                save(root / 'result.json', result)

    def test_native_role_output_must_satisfy_its_bound_closed_schema(self):
        def sender(body, *, deadline_ms):
            response = native_response()
            response['body']['output'][0]['content'][0]['text'] = '{"kind":"final_submit","data":{"wrong":"x"}}'
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'format_error')
        self.assertTrue(result['usage_known'])
        save(root / 'result.json', result)

    def test_native_function_call_maps_original_call_id_and_arguments(self):
        def sender(body, *, deadline_ms):
            response = native_response()
            response['body']['output'] = [{'type': 'function_call', 'id': 'PUBLIC-OUTPUT-ITEM',
                'call_id': 'PUBLIC-NEXT-CALL', 'name': 'list_evidence', 'arguments': '{"cursor":null}'}]
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['message']['content'])
        self.assertEqual(result['message']['tool_requests'], [{'call_id': 'PUBLIC-NEXT-CALL',
            'name': 'list_evidence', 'arguments': {'cursor': None}}])
        save(root / 'result.json', result)

    def test_bad_native_json_preserves_known_usage_for_host_owned_repair(self):
        def sender(body, *, deadline_ms):
            response = native_response()
            response['body']['output'][0]['content'][0]['text'] = '{broken JSON'
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'format_error')
        self.assertTrue(result['usage_known'])
        self.assertEqual(result['usage']['cost_microusd'], 183)
        self.assertTrue(result['error']['retryable'])
        self.assertEqual(adapter.invoke(req)['status'], 'preflight_denied')
        save(root / 'result.json', result)

    def test_changed_input_usage_stops_with_original_usage_and_without_retry(self):
        sends = []
        def sender(body, *, deadline_ms):
            sends.append(body)
            response = native_response()
            response['body']['usage']['input_tokens'] = 101
            response['body']['usage']['total_tokens'] = 131
            return response
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'usage_mismatch')
        self.assertEqual(result['usage']['input_tokens'], 101)
        self.assertFalse(result['error']['retryable'])
        self.assertEqual(len(sends), 1)
        save(root / 'result.json', result)

    def test_native_invocation_uses_bound_wire_and_normalizes_usage_without_double_reasoning(self):
        sends = []
        def sender(body, *, deadline_ms):
            sends.append((body, deadline_ms))
            return native_response()
        adapter, req, root = reserved_native(sender)
        result = adapter.invoke(req)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['message']['content'], {'kind': 'final_submit', 'data': {'draft_id': 'PUBLIC-DRAFT'}})
        self.assertEqual(result['usage']['input_tokens'], 100)
        self.assertEqual(result['usage']['output_tokens'], 30)
        self.assertEqual(result['usage']['cost_microusd'], 183)
        self.assertEqual(result['usage']['reasoning_output_tokens'], 20)
        self.assertEqual(result['provider_response_id'], 'PUBLIC-RESPONSE-ID')
        self.assertEqual(result['provider_request_id'], 'PUBLIC-HTTP-ID')
        self.assertEqual(result['usage_basis'], 'fixture')
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0][0], adapter.prepare(request())['wire_utf8'])
        save(root / 'result.json', result)

    def test_prepare_rejects_an_open_role_schema_before_any_sender(self):
        sends = []
        adapter = ModelAdapter(lambda body: sends.append(body), capability_binding=BINDING)
        unsafe = request()
        unsafe['output_schema']['properties']['data']['additionalProperties'] = True
        self.assertEqual(adapter.prepare(unsafe)['status'], 'invalid_request')
        self.assertEqual(sends, [])

    def test_prepare_freezes_full_native_messages_tools_and_output_without_sending(self):
        sends = []
        adapter = ModelAdapter(lambda body: sends.append(body), capability_binding=BINDING)
        prepared = adapter.prepare(request())
        expected_input = [{'role': 'system', 'content': '公开协议\nSIM'},
            {'role': 'user', 'content': '{"C":["PUBLIC-A"],"H":["rice"]}'},
            {'type': 'function_call', 'call_id': 'PUBLIC-CALL', 'name': 'list_evidence', 'arguments': '{"cursor":null}'},
            {'type': 'function_call_output', 'call_id': 'PUBLIC-CALL', 'output': '{"entries":[],"next_cursor":null}'}]
        expected = {'model': MODEL, 'input': expected_input,
            'tools': [{'type': 'function', 'name': 'list_evidence', 'description': 'list_evidence', 'strict': True,
                'parameters': {'type': 'object', 'properties': {'cursor': {'type': ['string', 'null']}},
                               'required': ['cursor'], 'additionalProperties': False}}],
            'text': {'format': {'type': 'json_schema', 'name': 'rsm_final_submit', 'strict': True, 'schema': FINAL_SCHEMA}},
            'reasoning': {'effort': 'none'}, 'parallel_tool_calls': False, 'tool_choice': 'auto',
            'truncation': 'disabled', 'max_output_tokens': 1500, 'service_tier': 'default', 'store': False, 'stream': False}
        self.assertEqual(prepared['status'], 'prepared')
        self.assertEqual(prepared['wire_body'], expected)
        self.assertEqual(prepared['count_body'], {k: v for k, v in expected.items()
            if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')})
        self.assertEqual(prepared['count_body']['text'], expected['text'])
        self.assertEqual(prepared['input_tokens'], None)
        self.assertEqual(sends, [])
        self.assertEqual(adapter.prepare(request())['wire_sha256'], prepared['wire_sha256'])
        save(case_directory('prepare') / 'prepared.json', prepared)
