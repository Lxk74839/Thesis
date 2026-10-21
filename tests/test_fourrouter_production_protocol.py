"""Synthetic PUBLIC Responses fixtures, not a replay of A1/A2 or real user data."""
import copy
import json
import unittest
import importlib.util
from pathlib import Path

import provider_fourrouter as provider
from model_adapter import ModelAdapter
from tests.test_fourrouter_protocol_diagnostics import public_request, public_response, setUpModule
from tests.test_p1_wiring import FIXTURE_BINDING


def logical_request():
    req = public_request()
    for key in ('input_token_upper_bound', 'count_receipt_id', 'deadline_ms', 'reservation_id'):
        req.pop(key, None)
    req.update(schema_version='rsm-model-prepare-0.1.0', max_output_tokens=1024,
        messages=[{'role': 'system', 'content': 'PUBLIC fictional protocol task'},
                  {'role': 'user', 'content': 'PUBLIC tool then final JSON'}])
    return req


def reasoning():
    return {'type': 'reasoning', 'id': 'opaque-PUBLIC-ID', 'status': 'completed',
        'summary': [{'type': 'summary_text', 'text': 'PUBLIC INTERNAL SUMMARY'}],
        'content': [{'type': 'reasoning_text', 'text': 'PUBLIC INTERNAL REASONING'}],
        'encrypted_content': 'PUBLIC-OPAQUE-CIPHERTEXT'}


class ProductionProtocol(unittest.TestCase):
    def test_PUBLIC_driver_uses_production_chain_and_stops_on_first_error(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('PUBLIC_production_driver',
            root / '.scratch/ticket14-production-protocol-20261021/run_public.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for invalid in (False, True):
            sent = []
            def sender(wire, *, deadline_ms):
                body = json.loads(wire)
                sent.append(body)
                response = public_response()
                if len(sent) == 1:
                    meta = reasoning()
                    if invalid:
                        meta['encrypted_content'] = 7
                    response['body']['output'] = [meta, {'type': 'function_call', 'id': 'fc_PUBLIC',
                        'call_id': 'PUBLIC-NEXT', 'name': 'list_evidence', 'arguments': '{"cursor":null}'}]
                else:
                    self.assertEqual(body['input'][2]['encrypted_content'], 'PUBLIC-OPAQUE-CIPHERTEXT')
                    response['body']['output'][0]['content'][0]['text'] = '{"kind":"final_submit","data":{"draft_id":"PUBLIC-DRAFT-7"}}'
                return response
            result = entry.run_protocol(sender, clock=lambda: 1000)
            self.assertEqual(len(sent), 1 if invalid else 2)
            self.assertEqual(result['status'], 'failed' if invalid else 'passed')
            if not invalid:
                self.assertTrue(result['encrypted_context_replayed'])
                self.assertTrue(result['strict_json_valid'])
            self.assertNotIn('PUBLIC-OPAQUE-CIPHERTEXT', json.dumps(result))
            self.assertNotIn('PUBLIC INTERNAL REASONING', json.dumps(result))

    def test_store_false_tool_round_replays_original_protocol_items_with_opaque_ciphertext(self):
        adapter = ModelAdapter(None, capability_binding=FIXTURE_BINDING)
        request = logical_request()
        prepared = adapter.prepare(request)
        self.assertEqual(prepared['status'], 'prepared')
        reply = public_response()
        reply['body']['output'] = [reasoning(), {'type': 'function_call', 'id': 'fc_PUBLIC',
            'status': 'completed', 'call_id': 'PUBLIC-NEXT', 'name': 'list_evidence', 'arguments': '{"cursor":null}'}]
        result = provider.normalize(reply, request, pricing=None, engineering=True,
            continuations=adapter.protocol_context)
        following = copy.deepcopy(request)
        following['messages'] += [result['message'], {'role': 'tool', 'tool_call_id': 'PUBLIC-NEXT',
            'content': {'entries': [], 'next_cursor': None}}]
        second = adapter.prepare(following)
        self.assertEqual(second['status'], 'prepared')
        self.assertFalse(second['wire_body']['store'])
        self.assertEqual(second['wire_body']['input'][2:4], reply['body']['output'])
        self.assertEqual(second['wire_body']['input'][4]['call_id'], 'PUBLIC-NEXT')
        self.assertEqual(second['wire_body']['include'], ['reasoning.encrypted_content'])
        self.assertNotIn('PUBLIC-OPAQUE-CIPHERTEXT', json.dumps(result))
        self.assertTrue(provider.verify_prepared(second))
        safe = provider.prepared_diagnostic(second)
        for private in ('PUBLIC-OPAQUE-CIPHERTEXT', 'PUBLIC INTERNAL REASONING', 'PUBLIC INTERNAL SUMMARY'):
            self.assertNotIn(private, json.dumps(safe))
        final = provider.normalize(public_response(), following, pricing=None, engineering=True,
            continuations=adapter.protocol_context)
        self.assertEqual(final['message']['content']['data']['draft_id'], 'PUBLIC')
        missing = copy.deepcopy(following)
        missing['messages'][-2].pop('protocol_ref')
        self.assertNotEqual(adapter.prepare(missing)['status'], 'prepared')
        changed = copy.deepcopy(following)
        changed['messages'][-2]['tool_requests'][0]['arguments'] = {'cursor': 'PUBLIC-altered'}
        self.assertNotEqual(adapter.prepare(changed)['status'], 'prepared')
        following['session_id'] = 'PUBLIC-OTHER-SESSION'
        self.assertNotEqual(adapter.prepare(following)['status'], 'prepared')

    def test_rejected_reasoning_conditions_report_safe_specific_shapes(self):
        cases = [('summary', None, 'reasoning_invalid_array'),
            ('encrypted_content', 7, 'reasoning_invalid_encrypted_type'),
            ('content', [{'type': 'PUBLIC_UNKNOWN', 'text': 'PUBLIC INTERNAL REASONING'}], 'reasoning_invalid_part_type'),
            ('status', 'PUBLIC_BAD', 'reasoning_invalid_status'), ('id', 7, 'reasoning_invalid_id'),
            ('PUBLIC_SECRET_FIELD', 'PUBLIC-OPAQUE-CIPHERTEXT', 'reasoning_unknown_fields')]
        for field, value, code in cases:
            with self.subTest(code=code):
                response = public_response()
                item = reasoning()
                item[field] = value
                response['body']['output'].insert(0, item)
                with self.assertRaises(provider.ProtocolError) as caught:
                    provider.normalize(response, logical_request(), pricing=None, engineering=True)
                diagnostic = caught.exception.diagnostic
                self.assertEqual(diagnostic['code'], code)
                self.assertEqual(diagnostic['output_index'], 0)
                self.assertNotIn('PUBLIC_SECRET_FIELD', json.dumps(diagnostic))
                self.assertNotIn('PUBLIC INTERNAL REASONING', json.dumps(diagnostic))
                self.assertNotIn('PUBLIC-OPAQUE-CIPHERTEXT', json.dumps(diagnostic))

    def test_legal_absent_null_and_status_fields_remain_metadata(self):
        for status in (None, 'in_progress', 'completed', 'incomplete'):
            response = public_response()
            item = {'type': 'reasoning', 'id': 'PUBLIC-reason', 'summary': [], 'encrypted_content': None}
            if status is not None:
                item['status'] = status
            response['body']['output'].insert(0, item)
            self.assertEqual(provider.normalize(response, logical_request(), pricing=None, engineering=True)['status'], 'ok')

    def test_tool_and_business_output_remain_strict(self):
        req = logical_request()
        for output, stage in (([{'type': 'PUBLIC_UNKNOWN'}], 'output_item'),
                ([{'type': 'function_call', 'call_id': 'PUBLIC-X', 'name': 'list_evidence', 'arguments': '{'}], 'json_decode'),
                ([{'type': 'function_call', 'call_id': 'PUBLIC-X', 'name': 'list_evidence', 'arguments': '{"cursor":null,"extra":1}'}], 'tool_call'),
                ([{'type': 'message', 'content': [{'type': 'output_text', 'text': '{"kind":"final_submit","data":{"draft_id":"PUBLIC","extra":1}}'}]}], 'role_schema')):
            response = public_response()
            response['body']['output'] = output
            with self.assertRaises(provider.ProtocolError) as caught:
                provider.normalize(response, req, pricing=None, engineering=True)
            self.assertEqual(caught.exception.diagnostic['stage'], stage)

    def test_legal_optional_reasoning_fields_and_structure_without_original_values(self):
        response, request = public_response(), logical_request()
        response['body']['output'].insert(0, reasoning())
        result = provider.normalize(response, request, pricing=None, engineering=True)
        self.assertEqual(result['status'], 'ok')
        encoded = json.dumps(result)
        for private in ('PUBLIC INTERNAL SUMMARY', 'PUBLIC INTERNAL REASONING', 'PUBLIC-OPAQUE-CIPHERTEXT'):
            self.assertNotIn(private, encoded)
        shape = result['raw_response']['output_structure'][0]
        self.assertEqual(shape['fields']['encrypted_content']['type'], 'string')
        self.assertEqual(shape['fields']['summary']['length'], 1)

