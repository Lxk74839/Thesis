"""Synthetic PUBLIC protocol cases, never A5 response replays."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import provider_fourrouter as provider
from tests.test_fourrouter_protocol_diagnostics import public_request, public_response, public_invocation, setUpModule


def message(text, phase=None):
    return {'type': 'message', 'role': 'assistant', 'status': 'completed', 'phase': phase,
        'content': [{'type': 'output_text', 'text': text}]}


class MessageSelection(unittest.TestCase):
    def test_commentary_is_not_the_final_role_JSON(self):
        response = public_response()
        response['body']['output'] = [message('PUBLIC checking evidence', 'commentary'),
            message('{"kind":"final_submit","data":{"draft_id":"PUBLIC"}}', 'final_answer')]
        result = provider.normalize(response, public_request(), pricing=None, engineering=True)
        self.assertEqual(result['message']['content']['data']['draft_id'], 'PUBLIC')

    def test_single_message_parts_are_joined_in_order_not_across_messages(self):
        for phase in (None, 'final_answer'):
            response = public_response()
            item = message('', phase)
            item['content'] = [{'type': 'output_text', 'text': '{"kind":"final_submit",'},
                {'type': 'output_text', 'text': '"data":{"draft_id":"PUBLIC"}}'}]
            response['body']['output'] = [item]
            self.assertEqual(provider.normalize(response, public_request(), pricing=None,
                engineering=True)['message']['content']['data']['draft_id'], 'PUBLIC')

    def test_multiple_business_messages_are_ambiguous_even_if_concatenation_is_JSON(self):
        for phases in ((None, None), ('final_answer', 'final_answer'), (None, 'final_answer')):
            response = public_response()
            response['body']['output'] = [message('{"kind":"final_submit",', phases[0]),
                message('"data":{"draft_id":"PUBLIC"}}', phases[1])]
            with self.assertRaises(provider.ProtocolError) as caught:
                provider.normalize(response, public_request(), pricing=None, engineering=True)
            self.assertEqual(caught.exception.diagnostic['code'], 'ambiguous_business_messages')
            self.assertEqual(caught.exception.diagnostic['message_indices'], [0, 1])

    def test_commentary_only_unknown_phase_incomplete_and_unsupported_parts_reject(self):
        for output, code in (([message('PUBLIC', 'commentary')], 'missing_business_message'),
                ([message('{}', 'PUBLIC-unknown')], 'unsupported_message_phase'),
                ([message('{}') | {'status': 'incomplete'}], 'message_not_completed'),
                ([message('{}') | {'role': 'user'}], 'invalid_message_role'),
                ([{'type': 'PUBLIC_unknown'}], 'unsupported_output_type'),
                ([message('{}') | {'content': [{'type': 'refusal'}]}], 'unsupported_content_type')):
            with self.subTest(code=code):
                response = public_response()
                response['body']['output'] = output
                with self.assertRaises(provider.ProtocolError) as caught:
                    provider.normalize(response, public_request(), pricing=None, engineering=True)
                self.assertEqual(caught.exception.diagnostic['code'], code)

    def test_commentary_can_accompany_tool_calls_but_business_cannot(self):
        call = {'type': 'function_call', 'call_id': 'PUBLIC-NEW', 'name': 'list_evidence',
            'arguments': '{"cursor":null}', 'status': 'completed'}
        response = public_response()
        response['body']['output'] = [message('PUBLIC lookup', 'commentary'), call]
        result = provider.normalize(response, public_request(), pricing=None, engineering=True)
        self.assertEqual(result['message']['tool_requests'][0]['call_id'], 'PUBLIC-NEW')
        response['body']['output'].append(message('{"kind":"final_submit","data":{"draft_id":"PUBLIC"}}', 'final_answer'))
        with self.assertRaises(provider.ProtocolError) as caught:
            provider.normalize(response, public_request(), pricing=None, engineering=True)
        self.assertEqual(caught.exception.diagnostic['code'], 'mixed_tool_and_text_output')

    def test_malformed_or_ambiguous_JSON_is_never_repaired(self):
        for text in ('{"kind":', 'PUBLIC prefix {"kind":"final_submit","data":{"draft_id":"PUBLIC"}}',
                '{"kind":"PUBLIC-wrong","kind":"final_submit","data":{"draft_id":"PUBLIC"}}'):
            with self.subTest(text=text):
                response = public_response()
                response['body']['output'] = [message(text, 'final_answer')]
                with self.assertRaises(provider.ProtocolError):
                    provider.normalize(response, public_request(), pricing=None, engineering=True)

    def test_failure_capture_replays_business_parts_without_reasoning_or_headers(self):
        from tests.test_fourrouter_production_protocol import reasoning
        response = public_response()
        item = message('{"kind":', 'final_answer')
        item['content'].append({'type': 'output_text', 'text': 'PUBLIC broken'})
        response['body']['output'] = [reasoning(), item]
        response['headers'] = {'Authorization': 'PUBLIC-AUTH-SECRET'}
        with public_invocation(response) as (model, req, budget, calls):
            result = model.invoke(req)
            capture = result['raw_response']['business_output']
            self.assertTrue(capture['replayable'])
            saved = capture['items'][0]
            self.assertEqual(saved['output_index'], 1)
            self.assertEqual(saved['item'], item)
            self.assertEqual(saved['text_sha256'], hashlib.sha256(b'{"kind":PUBLIC broken').hexdigest())
            self.assertEqual(result['usage']['input_tokens'], 100)
            self.assertEqual(result['usage']['output_tokens'], 30)
            self.assertFalse(result['error']['retryable'])
            self.assertEqual(len(calls), 1)
            replay = public_response()
            replay['body']['output'] = [saved['item']]
            with self.assertRaises(provider.ProtocolError) as caught:
                provider.normalize(replay, req, pricing=None, engineering=True)
            self.assertEqual(caught.exception.diagnostic['position'], result['protocol_diagnostic']['position'])
            encoded = json.dumps(capture)
            for private in ('PUBLIC-AUTH-SECRET', 'PUBLIC INTERNAL REASONING',
                    'PUBLIC INTERNAL SUMMARY', 'PUBLIC-OPAQUE-CIPHERTEXT'):
                self.assertNotIn(private, encoded)

    def test_failure_capture_is_bounded_and_does_not_claim_partial_text_is_replayable(self):
        response = public_response()
        response['body']['output'] = [message('PUBLIC' * 20000, 'final_answer')]
        with public_invocation(response) as (model, req, budget, calls):
            capture = model.invoke(req)['raw_response']['business_output']
            self.assertFalse(capture['replayable'])
            self.assertEqual(capture['omission_reason'], 'capture_size_limit')
            self.assertLessEqual(len(json.dumps(capture).encode()), 96 * 1024)

    def test_production_prepare_preserves_all_native_items_phase_and_order_for_tool_followup(self):
        from model_adapter import ModelAdapter
        from tests.test_fourrouter_production_protocol import logical_request, reasoning
        from tests.test_p1_wiring import FIXTURE_BINDING
        adapter = ModelAdapter(None, capability_binding=FIXTURE_BINDING)
        request = logical_request()
        self.assertEqual(adapter.prepare(request)['status'], 'prepared')
        response = public_response()
        response['body']['output'] = [reasoning(), message('PUBLIC lookup', 'commentary'),
            {'type': 'function_call', 'status': 'completed', 'call_id': 'PUBLIC-NEW',
                'name': 'list_evidence', 'arguments': '{"cursor":null}'}]
        result = provider.normalize(response, request, pricing=None, engineering=True,
            continuations=adapter.protocol_context)
        following = copy.deepcopy(request)
        following['messages'] += [result['message'], {'role': 'tool', 'tool_call_id': 'PUBLIC-NEW',
            'content': {'entries': [], 'next_cursor': None}}]
        prepared = adapter.prepare(following)
        self.assertEqual(prepared['status'], 'prepared')
        self.assertEqual(prepared['wire_body']['input'][2:5], response['body']['output'])
        self.assertEqual(prepared['wire_body']['input'][5]['call_id'], 'PUBLIC-NEW')
        self.assertNotIn('PUBLIC-OPAQUE-CIPHERTEXT', json.dumps(result))
        final = public_response()
        final['body']['output'].insert(0, message('PUBLIC done', 'commentary'))
        final['body']['output'][1]['phase'] = 'final_answer'
        self.assertEqual(provider.normalize(final, following, pricing=None, engineering=True,
            continuations=adapter.protocol_context)['message']['content']['kind'], 'final_submit')

    def test_sensitive_echo_and_unsupported_capture_are_explicitly_not_replayable(self):
        for response in ({'body': []}, {'body': {'output': None}},
                {'body': {'output': [{'type': 'PUBLIC-unknown'}]}}):
            self.assertFalse(provider.failure_business_output(response)['replayable'])
        for text in ('Authorization: PUBLIC-secret', 'Bearer PUBLIC-secret', '{"api_key":"PUBLIC-secret"}'):
            response = public_response()
            response['body']['output'] = [message(text, 'final_answer')]
            capture = provider.failure_business_output(response)
            self.assertFalse(capture['replayable'])
            self.assertNotIn('PUBLIC-secret', json.dumps(capture))
        response['_business_capture_forbidden'] = True
        self.assertEqual(provider.failure_business_output(response)['omission_reason'], 'credential_echo')

    def test_incomplete_function_call_cannot_execute(self):
        response = public_response()
        response['body']['output'] = [{'type': 'function_call', 'call_id': 'PUBLIC-NEW',
            'name': 'list_evidence', 'arguments': '{"cursor":null}', 'status': 'incomplete'}]
        with self.assertRaises(provider.ProtocolError) as caught:
            provider.normalize(response, public_request(), pricing=None, engineering=True)
        self.assertEqual(caught.exception.diagnostic['code'], 'function_call_not_completed')

    def test_saved_business_capture_can_be_reloaded_and_replayed_through_normalize(self):
        response = public_response()
        response['body']['output'] = [message('PUBLIC progress', 'commentary'),
            message('{"kind":PUBLIC broken', 'final_answer')]
        with public_invocation(response) as (model, req, budget, calls):
            result = model.invoke(req)
            with tempfile.TemporaryDirectory(dir=Path.cwd() / '.tmp') as tmp:
                path = Path(tmp) / 'PUBLIC-business-capture.json'
                path.write_text(provider.canonical(result['raw_response']['business_output']), encoding='utf-8')
                capture = json.loads(path.read_text(encoding='utf-8'))
            response['body']['output'] = [saved['item'] for saved in capture['items']]
            with self.assertRaises(provider.ProtocolError) as caught:
                provider.normalize(response, req, pricing=None, engineering=True)
            self.assertEqual(caught.exception.diagnostic, result['protocol_diagnostic'])

    def test_lazy_sender_marks_synthetic_authentication_echo_without_archiving_it(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd() / '.tmp') as tmp:
            credential = Path(tmp) / 'PUBLIC-synthetic-key.json'
            credential.write_text('{"api_key":"PUBLIC-FICTIONAL-KEY"}', encoding='utf-8')
            calls = []
            def transport(endpoint, body, key, timeout, **kwargs):
                calls.append(endpoint)
                response = public_response()
                response['body']['output'] = [message('PUBLIC broken ' + key, 'final_answer')]
                return response
            sender = provider.make_sender(clock=lambda: 0, max_request_bytes=2 * 1024**2,
                credential_path=credential, http_sender=transport)
            envelope = sender('{"model":"gpt-6-luna","input":["PUBLIC"]}', deadline_ms=30000)
            capture = provider.failure_business_output(envelope)
            self.assertEqual(capture['omission_reason'], 'credential_echo')
            self.assertNotIn('PUBLIC-FICTIONAL-KEY', json.dumps(capture))
            self.assertEqual(calls, [provider.ENDPOINT])  # injected transport only, zero real HTTP


if __name__ == '__main__':
    unittest.main()
