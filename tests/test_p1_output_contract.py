"""A3-derived minimal PUBLIC business mismatch; no private response replay."""
import copy
import json
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

from model_adapter import ModelAdapter
import provider_fourrouter as provider
from tests.test_p1_wiring import FIXTURE_BINDING, setUpModule
from tests.test_fourrouter_production_protocol import logical_request
from tests.test_fourrouter_protocol_diagnostics import public_response


class OutputContract(unittest.TestCase):
    def test_PUBLIC_entry_composes_production_request_and_stops_after_one(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('A4_PUBLIC', root / '.scratch/ticket14-s-a4-20261021/run_public.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for ids, passed in ((['c1', 'c2'], True), (['c1说明', 'c2说明'], False), (['c2', 'c1'], False)):
            calls = []
            def sender(text, **kwargs):
                wire = json.loads(text)
                calls.append(wire)
                self.assertEqual(wire['max_output_tokens'], 512)
                ids_schema = wire['text']['format']['schema']['properties']['data']['properties']['necessary_clauses']
                self.assertEqual(ids_schema['items']['enum'], ['c1', 'c2'])
                self.assertIn('same order and content', text)
                reply = public_response()
                reply['body']['output'][0]['content'][0]['text'] = json.dumps({'kind': 'analysis',
                    'data': {'necessary_clauses': ids, 'observations': []}})
                return reply
            result = entry.run_protocol(sender, clock=lambda: 10000)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['status'], 'passed' if passed else 'failed')

    def test_A4_real_1493_nonexecuting_preflight(self):
        import tests.test_p1_s_a3 as inherited
        original_config = inherited.config
        def a4_config():
            cfg = original_config()
            cfg['limits']['S'].update(model_calls=9, request_output_tokens=73728, elapsed_ms=1733612)
            return cfg
        with patch.object(inherited, 'GRANT', 'S-COMPLETE-ONCE-20261021-A4'), patch.object(inherited, 'config', a4_config):
            inherited.A3S().test_A3_real_1493_prepare_and_preflight_never_execute_or_read_credentials()

    def test_fixed_dispatch_and_completion_fields_reject_explanations_and_wrong_values(self):
        from provider_openai import matches
        schema = self.request('dispatch')['output_schema']
        valid = {'kind': 'dispatch', 'data': {'candidate': 'PUBLIC-A', 'to': '单智能体',
            'claim_ids': ['c1', 'c2'], 'candidate_limit': 32}}
        self.assertTrue(matches(valid, schema))
        for key, value in (('candidate', 'PUBLIC-OTHER'), ('to', '单智能体说明'),
                ('claim_ids', ['c1说明', 'c2']), ('candidate_limit', 31)):
            bad = copy.deepcopy(valid)
            bad['data'][key] = value
            self.assertFalse(matches(bad, schema), key)
        self.assertFalse(matches({'kind': 'acquire', 'data': {'done': False,
            'plan_sha256': 'PUBLIC', 'processed': []}}, self.request('acquire')['output_schema']))

    def request(self, kind='analysis'):
        from provider_openai import role_output_schema
        req = logical_request()
        context = {'stage': '需求解析', 'method': 'S', 'necessary_clauses': ['c1', 'c2'],
            'current': 'PUBLIC-A', 'batch_limit': 32}
        req.update(output_kind=kind, messages=[{'role': 'user', 'content': {'runtime': context}}])
        req['output_schema'] = role_output_schema('单智能体', kind, req['messages'])
        return req

    def test_A3_description_strings_are_rejected_by_production_schema_without_rewriting(self):
        request = self.request()
        adapter = ModelAdapter(None, capability_binding=FIXTURE_BINDING)
        self.assertEqual(adapter.prepare(request)['status'], 'prepared')
        reply = public_response()
        data = {'kind': 'analysis', 'data': {'necessary_clauses': ['c1: PUBLIC说明', 'c2: PUBLIC说明'], 'observations': []}}
        reply['body']['output'][0]['content'][0]['text'] = json.dumps(data)
        with self.assertRaises(provider.ProtocolError) as caught:
            provider.normalize(reply, request, pricing=None, engineering=True)
        self.assertEqual(caught.exception.diagnostic['stage'], 'role_schema')
        self.assertEqual(request['messages'][0]['content']['runtime']['necessary_clauses'], ['c1', 'c2'])
        self.assertEqual(json.loads(reply['body']['output'][0]['content'][0]['text']), data)

