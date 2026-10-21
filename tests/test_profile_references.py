"""Synthetic PUBLIC long-history reference contract, never A4 audit replay."""
import copy
import json
import unittest
import importlib.util
from pathlib import Path

from evidence_access import encoded, digest
from model_adapter import ModelAdapter
import provider_fourrouter as provider
from provider_openai import role_output_schema
from tests.test_p1_wiring import FIXTURE_BINDING, setUpModule
from tests.test_fourrouter_production_protocol import logical_request
from tests.test_fourrouter_protocol_diagnostics import public_response

HISTORY = [{'review_text': 'PUBLIC fictional grain review. ' * 60, 'rating': 4}]


def profile_request():
    request = logical_request()
    request['messages'] = [{'role': 'user', 'content': {'runtime': {'stage': '用户画像',
        'method': 'S', 'necessary_clauses': ['c1', 'c2'], 'history': copy.deepcopy(HISTORY)}}}]
    request['output_kind'] = 'analysis'
    request['output_schema'] = role_output_schema('单智能体', 'analysis', request['messages'])
    return request


class ProfileReferences(unittest.TestCase):
    def test_PUBLIC_driver_keeps_raw_business_response_and_derived_fact_separate(self):
        spec = importlib.util.spec_from_file_location('PUBLIC_profile', Path(__file__).resolve().parents[1]
            / '.scratch/ticket14-profile-references-20261021/run_public.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for pointer, extra, passed in (('/H/0/review_text', {}, True), ('/H/99', {}, False),
                ('/H/0/review_text', {'value': 'PUBLIC paraphrase'}, False)):
            calls = []
            def sender(text, **kwargs):
                wire = json.loads(text)
                calls.append(wire)
                self.assertLessEqual(len(json.dumps(wire).encode()), 16384)
                self.assertEqual(wire['max_output_tokens'], 512)
                self.assertNotIn('value', wire['text']['format']['schema']['properties']['data']
                    ['properties']['observations']['items']['properties'])
                response = public_response()
                response['body']['output'][0]['content'][0]['text'] = json.dumps({'kind': 'analysis',
                    'data': {'necessary_clauses': ['c1', 'c2'], 'observations': [
                        {'pointer': pointer, 'preference_status': 'unknown', **extra}]}})
                return response
            result = entry.run_protocol(sender, clock=lambda: 10000)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['status'], 'passed' if passed else 'failed')
            if passed:
                self.assertNotIn('value', result['model_response']['data']['observations'][0])
                self.assertEqual(result['derived_facts'][0]['value'], entry.HISTORY[0]['review_text'])
                self.assertEqual(result['derived_facts'][0]['preference_status'], 'unknown')

    def test_stale_invalid_or_legacy_history_reference_is_not_silently_repaired(self):
        from recommendation_runner import resolve_history_references
        sha = digest(encoded(HISTORY))
        for pointer in ('/outside', '/H/90', '/H/-1', '/H/00', '/H/0/~3', '/H/0/missing'):
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                resolve_history_references(HISTORY, sha, [{'pointer': pointer, 'preference_status': 'unknown'}])
        old = {'pointer': '/H/0/review_text', 'preference_status': 'history_fact', 'value': 'PUBLIC paraphrase'}
        with self.assertRaises(ValueError):
            resolve_history_references(HISTORY, sha, [old])
        changed = copy.deepcopy(HISTORY)
        changed[0]['review_text'] = 'PUBLIC changed source'
        with self.assertRaises(ValueError):
            resolve_history_references(changed, sha, [{'pointer': '/H', 'preference_status': 'unknown'}])
        response = public_response()
        response['body']['output'][0]['content'][0]['text'] = json.dumps({'kind': 'analysis',
            'data': {'necessary_clauses': ['c1', 'c2'], 'observations': [old]}})
        with self.assertRaises(provider.ProtocolError):
            provider.normalize(response, profile_request(), pricing=None, engineering=True)
        self.assertEqual(old['value'], 'PUBLIC paraphrase')

    def test_product_original_attributes_use_existing_receipt_and_pointer_without_value_echo(self):
        citation = {'evidence_ref': 'PUBLIC-E', 'receipt_id': 'PUBLIC-R', 'target_id': 'PUBLIC-T', 'version': 1, 'pointer': '/'}
        fact = {'data': {'kind': 'retail_status', 'facts': {'status': 'ON_SALE', 'stock_units': 7, 'unit': 'kg'}},
            'citation': citation}
        attributes = [{'attribute': name, 'citation': {**citation, 'pointer': '/facts/' + name}}
            for name in ('status', 'stock_units')]
        request = profile_request()
        context = request['messages'][0]['content']['runtime']
        context.update(stage='农产品画像', current='PUBLIC-A', profile_candidates=['PUBLIC-A'], quality={}, assessments={})
        request['output_schema'] = role_output_schema('单智能体', 'analysis', request['messages'])
        observation = {'candidate_id': 'PUBLIC-A', 'assessment_receipt_id': 'PUBLIC-assess',
            'quality': None, 'attributes': attributes, 'unknown': []}
        response = public_response()
        response['body']['output'][0]['content'][0]['text'] = json.dumps({'kind': 'analysis',
            'data': {'necessary_clauses': ['c1', 'c2'], 'observations': [observation]}})
        normalized = provider.normalize(response, request, pricing=None, engineering=True)
        from recommendation_runner import resolve_attribute_references
        resolved = resolve_attribute_references([fact], attributes)
        self.assertEqual([a['value'] for a in resolved], ['ON_SALE', 7])
        self.assertEqual(resolved[1]['unit'], 'kg')
        self.assertEqual(resolved[1]['fact_sha256'], digest(encoded(7)))
        self.assertEqual(normalized['message']['content']['data']['observations'][0], observation)
        for field, value in (('receipt_id', 'PUBLIC-stale'), ('version', 2), ('pointer', '/outside')):
            changed = copy.deepcopy(attributes)
            changed[0]['citation'][field] = value
            with self.assertRaises(ValueError):
                resolve_attribute_references([fact], changed)
        legacy = copy.deepcopy(attributes)
        legacy[0]['value'] = 'PUBLIC paraphrase'
        with self.assertRaises(ValueError):
            resolve_attribute_references([fact], legacy)

    def test_long_fact_is_resolved_by_host_while_production_response_stays_reference_only(self):
        request = profile_request()
        adapter = ModelAdapter(None, capability_binding=FIXTURE_BINDING)
        self.assertEqual(adapter.prepare(request)['status'], 'prepared')
        observation = {'pointer': '/H/0/review_text', 'preference_status': 'unknown'}
        response = public_response()
        response['body']['output'][0]['content'][0]['text'] = json.dumps({'kind': 'analysis',
            'data': {'necessary_clauses': ['c1', 'c2'], 'observations': [observation]}})
        normalized = provider.normalize(response, request, pricing=None, engineering=True)
        from recommendation_runner import resolve_history_references
        facts = resolve_history_references(HISTORY, digest(encoded(HISTORY)), [observation])
        self.assertEqual(facts[0]['value'], HISTORY[0]['review_text'])
        self.assertEqual(facts[0]['fact_sha256'], digest(encoded(HISTORY[0]['review_text'])))
        self.assertEqual(facts[0]['H_sha256'], digest(encoded(HISTORY)))
        self.assertEqual(facts[0]['preference_status'], 'unknown')
        self.assertEqual(normalized['message']['content']['data']['observations'], [observation])
        self.assertNotIn('value', normalized['message']['content']['data']['observations'][0])

