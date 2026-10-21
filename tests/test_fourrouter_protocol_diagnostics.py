"""Handwritten PUBLIC fixtures; never a replay of the old HTTP response."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import contextmanager

import provider_fourrouter as provider


def public_request():
    from tests.provider_fixtures import request
    req = request()
    req.update(execution_kind='fourrouter_responses', model_id=provider.MODEL,
        input_token_upper_bound=None, count_receipt_id=None)
    return req


def public_response():
    return {'http_status': 200, 'request_id': 'PUBLIC-HTTP', 'body': {'id': 'PUBLIC-response',
        'model': provider.MODEL, 'status': 'completed', 'output': [{'type': 'message',
            'content': [{'type': 'output_text', 'text': '{"kind":"final_submit","data":{"draft_id":"PUBLIC"}}'}]}],
        'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130,
            'input_tokens_details': {'cached_tokens': 0}, 'output_tokens_details': {'reasoning_tokens': 7}}}}


def setUpModule():
    def offline(event, args):
        if event.startswith(('socket.', 'http.client.', 'subprocess.')):
            raise OSError('PUBLIC_protocol_test_offline')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            parts = {p.lower() for p in Path(os.fsdecode(args[0])).parts}
            if parts & {'.secrets', 'private', 'evaluation', 'gold'}:
                raise OSError('PUBLIC_protocol_test_no_credentials_labels')
    sys.addaudithook(offline)


@contextmanager
def public_invocation(response, *, late=False):
    from evidence_access import PROJECT
    from model_adapter import ModelAdapter
    from p1_engineering import AUTHORIZATION, SEngineeringBudget, reservation_deadline
    from tests.test_p1_wiring import FIXTURE_BINDING
    parent = PROJECT / '.tmp/recommendation-runtime/PUBLIC-protocol-diagnostics'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        now, calls = [10000.25], []
        limits = dict.fromkeys(SEngineeringBudget.resources, 100)
        limits.update(model_calls=12, request_output_tokens=98304, elapsed_ms=350000, retries=0)
        reserve = dict.fromkeys(SEngineeringBudget.resources, 0)
        reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=10000)
        req = public_request()
        req.pop('count_receipt_id')
        budget = SEngineeringBudget({'run_id': req['run_id'], 'root_task_id': 'PUBLIC-ROOT',
            'method': 'S', 'fixture': 'public_runtime_adapter', 'project_id': 'PUBLIC-P1'},
            limits, reserve, clock=lambda: now[0], journal_path=Path(tmp) / 'budget.jsonl')
        def transport(text, *, deadline_ms):
            calls.append(True)
            if late:
                now[0] = deadline_ms + 1
            return copy.deepcopy(response)
        model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
            'engineering_authorization': AUTHORIZATION, 'execution_authorized': True, 'pricing': None}, root_budget=budget)
        prepared = model.prepare(req)
        reservation = budget.reserve({'kind': 'model', 'request_id': req['request_id'],
            'prepared_id': prepared['prepared_id'], 'wire_sha256': prepared['wire_sha256'], 'count_receipt_id': None},
            {'model_calls': 1, 'request_output_tokens': 1500, 'elapsed_ms': 30000}, phase='final', retry_of=None)
        req.update(prepared_id=prepared['prepared_id'], reservation_id=reservation['reservation_id'],
            count_receipt_id=None, deadline_ms=int(reservation_deadline(budget, reservation['reservation_id'])))
        yield model, req, budget, calls


class ProtocolDiagnostics(unittest.TestCase):
    def test_missing_or_rejected_usage_stays_unknown_on_failure(self):
        for variant, state in (('absent', 'field_absent'), ('null', 'value_null'), ('invalid', 'parser_rejected')):
            with self.subTest(variant=variant):
                response = public_response()
                response['body']['output'] = [{'type': 'reasoning'}]
                if variant == 'absent':
                    response['body'].pop('usage')
                else:
                    response['body']['usage'] = None if variant == 'null' else {'input_tokens': 'PUBLIC-private'}
                with public_invocation(response) as (model, req, budget, calls):
                    result = model.invoke(req)
                    self.assertEqual(result['status'], 'reasoning_required_field')
                    self.assertEqual(result['usage_diagnostic']['state'], state)
                    self.assertIsNone(result['usage']['input_tokens'])
                    self.assertIsNone(result['usage']['output_tokens'])
                    self.assertIsNone(result['usage']['cost_microusd'])
                    self.assertEqual(len(calls), 1)

    def test_late_response_retains_usage_and_original_protocol_diagnostic(self):
        for invalid in (False, True):
            with self.subTest(invalid=invalid):
                response = public_response()
                if invalid:
                    response['body']['output'][0]['content'][0]['text'] = '{PUBLIC-secret'
                with public_invocation(response, late=True) as (model, req, budget, calls):
                    result = model.invoke(req)
                    self.assertEqual(result['usage']['input_tokens'], 100)
                    self.assertEqual(result['usage']['output_tokens'], 30)
                    self.assertEqual(result['deadline_diagnostic']['code'], 'response_late')
                    self.assertEqual(result['status'], 'invalid_role_JSON' if invalid else 'response_late')
                    if invalid:
                        self.assertEqual(result['protocol_diagnostic']['stage'], 'json_decode')
                    self.assertFalse(result['error']['retryable'])
                    self.assertEqual(len(calls), 1)

    def test_strict_tool_reuse_and_native_output_cap_still_reject(self):
        response = public_response()
        response['body']['output'] = [{'type': 'function_call', 'call_id': 'PUBLIC-CALL',
            'name': 'list_evidence', 'arguments': '{"cursor":null}'}]
        with public_invocation(response) as (model, req, budget, calls):
            result = model.invoke(req)
            self.assertEqual(result['status'], 'reused_tool_call_id')
            self.assertEqual(result['usage']['output_tokens'], 30)
            self.assertFalse(result['error']['retryable'])
        response = public_response()
        response['body']['usage'].update(output_tokens=1501, total_tokens=1601)
        with public_invocation(response) as (model, req, budget, calls):
            result = model.invoke(req)
            self.assertEqual(result['status'], 'output_token_cap_exceeded')
            self.assertEqual(result['usage']['output_tokens'], 1501)
            self.assertEqual(len(calls), 1)

    def test_protocol_failure_preserves_known_usage_and_budget_observation(self):
        response = public_response()
        response['body']['output'] = [{'type': 'reasoning'}]  # invented PUBLIC case, not old response
        with public_invocation(response) as (model, req, budget, calls):
            result = model.invoke(req)
            self.assertEqual(result['usage']['input_tokens'], 100)
            self.assertEqual(result['status'], 'reasoning_required_field')
            self.assertEqual(result['protocol_diagnostic']['stage'], 'reasoning')
            self.assertEqual(result['usage']['input_tokens'], 100)
            self.assertEqual(result['usage']['output_tokens'], 30)
            self.assertEqual(result['usage']['reasoning_output_tokens'], 7)
            self.assertIsNone(result['usage']['cost_microusd'])
            self.assertEqual(result['raw_response']['http_status'], 200)
            self.assertEqual(result['provider_requests_sent'], 0)  # PUBLIC fixture, zero real HTTP
            self.assertFalse(result['error']['retryable'])
            budget.settle(req['reservation_id'], {'status': result['status'],
                'usage': result['usage'] | {'model_calls': int(result['attempted'])}})
            view = budget.audit_view()
            self.assertEqual(view['usage']['output_tokens'], 30)  # reasoning is a subset, never +7
            self.assertIsNone(view['usage']['cost_microusd'])
            self.assertFalse(view['usage_exact'])
            self.assertEqual(model.invoke(req)['status'], 'not_started')
            self.assertEqual(len(calls), 1)

    def test_failure_stages_are_specific_and_JSON_error_text_is_not_exposed(self):
        cases = [
            ('response_status', 'response_not_completed', lambda r: r['body'].update(status='incomplete')),
            ('response_status', 'http_status_not_200', lambda r: r.update(http_status=429)),
            ('response_status', 'model_mismatch', lambda r: r['body'].update(model='PUBLIC-other')),
            ('output_item', 'invalid_output_shape', lambda r: r['body'].update(output=None)),
            ('output_item', 'unsupported_content_type', lambda r: r['body']['output'][0].update(content=[{'type': 'refusal'}])),
            ('json_decode', 'invalid_role_JSON', lambda r: r['body']['output'][0]['content'][0].update(text='{"PUBLIC-PRIVATE":')),
            ('role_schema', 'role_schema_mismatch', lambda r: r['body']['output'][0]['content'][0].update(text='{"kind":"final_submit","data":{"draft_id":"PUBLIC","extra":"PUBLIC-PRIVATE"}}')),
            ('native_usage', 'invalid_native_usage', lambda r: r['body'].update(usage={'input_tokens': -1})),
            ('tool_call', 'invalid_tool_call', lambda r: r['body'].update(output=[{'type': 'function_call', 'call_id': 'PUBLIC-new', 'name': 'PUBLIC-unknown-tool', 'arguments': '{}'}])),
            ('json_decode', 'invalid_tool_JSON', lambda r: r['body'].update(output=[{'type': 'function_call', 'call_id': 'PUBLIC-new', 'name': 'list_evidence', 'arguments': '{"PUBLIC-PRIVATE":'}])),
        ]
        for stage, code, mutate in cases:
            with self.subTest(code=code):
                response = public_response()
                mutate(response)
                with self.assertRaises(ValueError) as caught:
                    provider.normalize(response, public_request(), pricing=None, engineering=True)
                diagnostic = getattr(caught.exception, 'diagnostic', {})
                self.assertEqual((diagnostic.get('stage'), diagnostic.get('code')), (stage, code))
                self.assertNotIn('PUBLIC-PRIVATE', json.dumps(diagnostic))

    def test_unknown_output_has_safe_specific_stage_code_and_position(self):
        response = public_response()
        response['body']['output'] = [{'type': 'PUBLIC-PRIVATE-COMMENT-Authorization'}]
        with self.assertRaises(ValueError) as caught:
            provider.normalize(response, public_request(), pricing=None, engineering=True)
        diagnostic = getattr(caught.exception, 'diagnostic', None)
        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic['stage'], 'output_item')
        self.assertEqual(diagnostic['code'], 'unsupported_output_type')
        self.assertEqual(diagnostic['output_index'], 0)
        self.assertNotIn('PUBLIC-PRIVATE', json.dumps(diagnostic))


if __name__ == '__main__':
    unittest.main()
