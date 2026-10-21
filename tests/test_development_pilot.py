"""PUBLIC management fixtures; no credentials, live calls or evaluation labels."""
import json
from pathlib import Path
import tempfile
import unittest
import copy
import io
import os
from unittest.mock import patch


class SharedCalls(unittest.TestCase):
    def test_runtime_cannot_read_independent_reference_paths(self):
        from p1_storage import P1StorageGuard
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ('joint-reference', 'sim-reference'):
                target = root / directory / 'PUBLIC.json'
                target.parent.mkdir()
                target.write_text('{"scope":"PUBLIC fixture"}')
            with P1StorageGuard(root / 'output', 1024**3, development=True):
                for directory in ('joint-reference', 'sim-reference'):
                    with self.assertRaises(OSError):
                        (root / directory / 'PUBLIC.json').read_bytes()

    def test_entry_preserves_control_space_and_never_starts_worker_when_root_is_full(self):
        import development_pilot as entry
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'PUBLIC-existing'
            existing.write_bytes(b'PUBLIC')
            original = Path.stat
            def stat(path, *args, **kwargs):
                result = original(path, *args, **kwargs)
                if path == existing:
                    values = list(result)
                    values[6] = 1024**3 - 512
                    return os.stat_result(values)
                return result
            worker = Mock(side_effect=AssertionError('PUBLIC_worker_must_not_start'))
            with patch.object(entry, 'OUTPUT', root), patch.object(entry, 'CONTROL', root / 'control'), \
                    patch.object(Path, 'stat', stat), patch('subprocess.Popen', worker):
                with self.assertRaises(OSError):
                    entry.run_guarded('diag-short_tools', 'PUBLIC-headroom')
            self.assertEqual(worker.call_count, 0)
            self.assertFalse((root / 'control').exists())

    def test_initial_diagnostics_have_six_call_subcap_and_bad_model_is_not_sent(self):
        from development_pilot import claim_request
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'PUBLIC-requests.jsonl'
            for _ in range(6):
                claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 512}, 'PUBLIC-diagnostic', diagnostic=True)
            with self.assertRaises(OSError):
                claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 512}, 'PUBLIC-diagnostic', diagnostic=True)
            with self.assertRaises(OSError):
                claim_request(path, {'model': 'old-model', 'max_output_tokens': 512}, 'PUBLIC-bad')
            with self.assertRaises(OSError):
                claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1501,
                    'text': {'format': {'name': 'rsm_final_submit'}}}, 'PUBLIC-invalid-final')
            self.assertEqual(len(path.read_text().splitlines()), 6)

    def test_development_storage_cap_is_explicit_and_writes_remain_guarded(self):
        from p1_storage import P1StorageGuard
        from development_pilot import AUTHORIZATION
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                P1StorageGuard(root, 1024**3)
            guard = P1StorageGuard(root, 1024**3, run_root=root / 'PUBLIC',
                run_limit_bytes=128 * 1024**2, development=True)
            with guard:
                guard.authorize_development(AUTHORIZATION)
                with self.assertRaises(OSError):
                    guard.authorize_development('OLD-GRANT')
                with self.assertRaises(OSError):
                    (root.parent / 'PUBLIC-outside').write_text('PUBLIC')

    def test_persistent_new_budget_counts_failed_intents_without_using_old_balance(self):
        from development_pilot import claim_request
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'PUBLIC-requests.jsonl'
            old = Path(tmp) / 'PUBLIC-historical.jsonl'
            old.write_text('{"historical_calls":16}\n')
            original = old.read_bytes()
            for i in range(160):
                row = claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1500}, 'PUBLIC-run')
                self.assertEqual(row['sequence'], i + 1)
            with self.assertRaises(OSError):
                claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1}, 'PUBLIC-next')
            self.assertEqual(len(path.read_text().splitlines()), 160)
            self.assertEqual(old.read_bytes(), original)


class ProductionFlow(unittest.TestCase):
    def test_verification_schema_limits_ids_to_actual_draft_and_evidence_receipts(self):
        from provider_openai import role_output_schema, matches
        context = {'stage': 'verification', 'necessary_clauses': ['c1', 'c2'],
            'draft': {'draft_id': 'PUBLIC-d', 'items': [{'parent_asin': 'PUBLIC-A', 'reasons': [{'claim_id': 'c1'}]}]},
            'verification_receipts': ['PUBLIC-read']}
        schema = role_output_schema('单智能体', 'verification', [{'role': 'user', 'content': {'runtime': context}}])
        issue = {'issue_id': 'PUBLIC-i', 'draft_id': 'PUBLIC-d', 'candidate_id': 'PUBLIC-A', 'claim_id': 'c1',
            'pointer': '/items/0/reasons/0', 'code': 'PUBLIC-issue', 'blocking': True,
            'allowed_actions': ['revise_and_resubmit'], 'verifier': 'model', 'source_receipts': ['PUBLIC-read']}
        valid = {'kind': 'verification', 'data': {'issues': [issue]}}
        self.assertTrue(matches(valid, schema))
        for key, value in (('source_receipts', ['PUBLIC-invented']), ('draft_id', 'PUBLIC-old'),
                ('candidate_id', 'PUBLIC-other'), ('pointer', '/items/99')):
            wrong = copy.deepcopy(valid)
            wrong['data']['issues'][0][key] = value
            self.assertFalse(matches(wrong, schema))

    def test_draft_wire_contract_rejects_invented_kinds_and_resolves_only_bound_citations(self):
        from provider_openai import role_output_schema, matches
        from recommendation_runner import resolve_draft_references
        citation = {'evidence_ref': 'PUBLIC-e', 'receipt_id': 'PUBLIC-r', 'target_id': 'PUBLIC-t', 'version': 1, 'pointer': '/'}
        context = {'stage': 'draft', 'necessary_clauses': ['c1', 'c2'], 'bound_draft_contract': True,
            'ordered': ['PUBLIC-A'], 'candidate_batches': {'PUBLIC-A': 'PUBLIC-b'},
            'base_preferences': {}, 'citation_catalog': {'s0': {'candidate_id': 'PUBLIC-A', 'citation': citation}}}
        schema = role_output_schema('单智能体', 'draft', [{'role': 'user', 'content': {'runtime': context}}])
        draft = {'draft_id': 'PUBLIC-d', 'parent_draft_id': None, 'items': [{'parent_asin': 'PUBLIC-A',
            'sim_batch_id': 'PUBLIC-b', 'reasons': [{'claim_id': 'c1', 'kind': 'inspection_supported',
                'value': True, 'unit': None, 'text': '检验必要条件有完整有效支持（SIM）。', 'citations': ['s0']}]}]}
        self.assertTrue(matches({'kind': 'draft', 'data': draft}, schema))
        wrong = copy.deepcopy(draft)
        wrong['items'][0]['reasons'][0]['kind'] = 'inspection'
        self.assertFalse(matches({'kind': 'draft', 'data': wrong}, schema))
        resolved = resolve_draft_references(draft, context['citation_catalog'])
        self.assertEqual(resolved['items'][0]['reasons'][0]['citations'], [citation])
        self.assertEqual(draft['items'][0]['reasons'][0]['citations'], ['s0'])
        for bad in (['not-acquired'], [citation]):
            wrong = copy.deepcopy(draft)
            wrong['items'][0]['reasons'][0]['citations'] = bad
            with self.assertRaises(ValueError):
                resolve_draft_references(wrong, context['citation_catalog'])

    def test_product_profile_requires_exact_receipt_and_complete_acquired_references(self):
        from provider_openai import role_output_schema, matches
        cite = lambda ref: {'evidence_ref': ref, 'receipt_id': 'PUBLIC-read', 'target_id': ref,
            'version': 1, 'pointer': '/'}
        facts = [{'data': {'kind': 'inspection_report', 'facts': {'conclusion': 'PASS'}}, 'citation': cite('PUBLIC-report')},
            {'data': {'kind': 'retail_status', 'facts': {'status': 'on_sale', 'stock_units': 8}}, 'citation': cite('PUBLIC-stock')}]
        context = {'stage': '农产品画像', 'necessary_clauses': ['c1', 'c2'], 'current': 'PUBLIC-A',
            'profile_candidates': ['PUBLIC-A'], 'assessment_receipts': {'PUBLIC-A': 'PUBLIC-assess'},
            'quality': {}, 'assessments': {'PUBLIC-A': {'claims': {'c1': {'evidence_state': 'Supported'},
                'c2': {'evidence_state': 'Supported'}}}}, 'facts': {'PUBLIC-A': facts}, 'bound_profile_contract': True}
        schema = role_output_schema('单智能体', 'analysis', [{'role': 'user', 'content': {'runtime': context}}])
        attributes = [{'attribute': k, 'citation': f['citation'] | {'pointer': '/facts/' + k}}
            for f in facts for k in f['data']['facts']]
        valid = {'kind': 'analysis', 'data': {'necessary_clauses': ['c1', 'c2'], 'observations': [{
            'candidate_id': 'PUBLIC-A', 'assessment_receipt_id': 'PUBLIC-assess', 'quality': None,
            'attributes': attributes, 'unknown': []}]}}
        self.assertTrue(matches(valid, schema))
        bad = copy.deepcopy(valid)
        bad['data']['observations'][0]['assessment_receipt_id'] = 'PUBLIC-wrong'
        self.assertFalse(matches(bad, schema))
        missing = copy.deepcopy(valid)
        missing['data']['observations'][0]['attributes'].pop()
        self.assertFalse(matches(missing, schema))

    def test_acquire_resource_plan_is_validated_by_the_production_parser(self):
        from tests.test_fourrouter_production_protocol import logical_request
        from evidence_access import EvidenceSession
        from provider_fourrouter import normalize, ProtocolError
        request = logical_request()
        request['tools'] = EvidenceSession.tool_schemas(batch=True)
        tool = request['tools'][-1]
        for name in ('max_list_pages', 'max_read_batches'):
            tool['input_schema']['properties'][name]['enum'] = [32]
        args = {'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A',
            'candidate_limit': 32, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 32,
            'max_read_batches': 32, 'stop_policy': 'first_10_qualified'}
        def response(value):
            return {'http_status': 200, 'body': {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                {'type': 'function_call', 'call_id': 'PUBLIC-plan', 'name': 'acquire_batch',
                    'arguments': json.dumps(value)}]}}
        with self.assertRaises(ProtocolError):
            normalize(response(args | {'max_list_pages': 1, 'max_read_batches': 1}), request,
                pricing=None, engineering=True)
        self.assertEqual(normalize(response(args), request, pricing=None, engineering=True)['status'], 'ok')

    def test_frozen_seven_tasks_prepare_without_key_count_or_attempt_and_reject_R(self):
        from development_pilot import prepare_task, preflight_task
        original, forbidden = io.open, []
        def opened(file, *args, **kwargs):
            if not isinstance(file, int) and {'private', '.secrets', 'evaluation', 'gold'} & set(Path(file).parts):
                forbidden.append(True)
                raise OSError('PUBLIC_test_private_read_forbidden')
            return original(file, *args, **kwargs)
        with patch('io.open', opened):
            for label, method in [('V00', 'S')] + [(s, 'M') for s in ('V00', 'V01', 'V05', 'V06', 'Q1', 'Q2')]:
                prepared = prepare_task(label, method, 'T14-D1-' + label + '-' + method + '-PUBLIC-preflight')
                self.assertEqual(prepared['terminal'], 'ready')
                self.assertEqual(len(prepared['assembly']['binding']['C']), 1493)
                self.assertFalse(prepared['started'])
                self.assertEqual(preflight_task(label, method)['terminal'], 'ready')
        self.assertEqual(forbidden, [])
        with self.assertRaises(ValueError):
            prepare_task('V00', 'R', 'PUBLIC-not-authorized')
        with self.assertRaises(ValueError):
            prepare_task('V03', 'M', 'PUBLIC-not-authorized')

    def test_unsupported_wire_keyword_is_omitted_but_local_tool_rules_are_preserved(self):
        from tests.test_fourrouter_production_protocol import logical_request
        from tests.test_p1_wiring import FIXTURE_BINDING
        from model_adapter import ModelAdapter
        from evidence_access import EvidenceSession
        from provider_fourrouter import normalize, ProtocolError
        request = logical_request()
        request['tools'] = EvidenceSession.tool_schemas(batch=True)
        original = copy.deepcopy(request)
        model = ModelAdapter(None, capability_binding=FIXTURE_BINDING | {'wire_schema_subset': True})
        prepared = model.prepare(request)
        self.assertEqual(prepared['status'], 'prepared')
        self.assertNotIn('uniqueItems', json.dumps(prepared['wire_body']['tools']))
        self.assertEqual(request, original)
        self.assertTrue(all(t['strict'] for t in prepared['wire_body']['tools']))
        bad = {'http_status': 200, 'body': {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'function_call', 'call_id': 'PUBLIC-duplicate', 'name': 'read_evidence',
                'arguments': '{"evidence_refs":["PUBLIC-A","PUBLIC-A"]}'}]}}
        with self.assertRaises(ProtocolError):
            normalize(bad, request, pricing=None, engineering=True)

    def test_new_scoped_grant_uses_complete_S_and_M_without_counting(self):
        from development_pilot import AUTHORIZATION
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from tests.test_fourrouter_production_protocol import reasoning
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget
        for method in ('S', 'M'):
            with self.subTest(method=method), tempfile.TemporaryDirectory(
                    dir=Path(__file__).resolve().parents[1] / '.tmp/recommendation-runtime') as tmp:
                fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
                http = RouterHTTPFixture()
                def transport(text, *, deadline_ms):
                    wire = json.loads(text)
                    frame = json.loads(wire['input'][-1]['content'])['runtime'] if 'role' in wire['input'][-1] else None
                    if frame:
                        self.assertEqual(set(frame['candidate_base_scores']), {'PUBLIC-A', 'PUBLIC-B'})
                        self.assertEqual(set(frame['candidate_batches']), {'PUBLIC-A', 'PUBLIC-B'})
                    business = copy.deepcopy(wire)
                    business['input'] = [i for i in business['input'] if i.get('type') != 'reasoning']
                    for i in business['input']:
                        if i.get('type') == 'message':
                            i['content'] = ''.join(p['text'] for p in i['content'])
                    result = http(json.dumps(business), deadline_ms=deadline_ms)
                    if frame and frame.get('bound_draft_contract'):
                        # PUBLIC synthetic model follows the compact production wire contract.
                        output = result['body']['output'][0]['content'][0]
                        reply = json.loads(output['text'])
                        for item in reply['data']['items']:
                            for reason in item['reasons']:
                                reason['citations'] = [next(key for key, row in frame['citation_catalog'].items()
                                    if row['candidate_id'] == item['parent_asin'] and row['citation'] == c)
                                    for c in reason['citations']]
                        output['text'] = json.dumps(reply, ensure_ascii=False)
                    result['body'].pop('usage')
                    result['body']['output'].insert(0, reasoning())
                    return result
                model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
                    'development_authorization': AUTHORIZATION, 'execution_authorized': True, 'pricing': None})
                run = fixture.make(method, model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                    'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                    'authorization_id': AUTHORIZATION, 'development_authorization': AUTHORIZATION,
                    'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
                limits = dict.fromkeys(SEngineeringBudget.resources, 100)
                limits.update(model_calls=24, request_output_tokens=189916, elapsed_ms=1780000, retries=0)
                reserve = dict.fromkeys(SEngineeringBudget.resources, 0)
                reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=145000)
                budget = SEngineeringBudget(run.binding, limits, reserve, clock=lambda: fixture.now[0],
                    journal_path=Path(tmp) / 'PUBLIC-budget.jsonl')
                run.budget = run.evidence.root_budget = model.root_budget = budget
                result = run.run()
                self.assertEqual(result['terminal'], 'released', result.get('reason'))
                self.assertIsNone(result['budget']['usage']['input_tokens'])
                self.assertIsNone(result['budget']['usage']['cost_microusd'])
                self.assertTrue((run.output_root / 'dispatch-checkpoint.json').exists())
                audit = json.loads(Path(result['audit_path']).read_bytes())
                self.assertTrue('acquired_ref' in audit)
                self.assertTrue('request_ref' in audit['messages'][0])
                self.assertNotIn('request', audit['messages'][0])
                self.assertTrue(audit['draft_reference_bindings'])
                self.assertNotEqual(audit['draft_reference_bindings'][0]['raw_draft_sha256'],
                    audit['draft_reference_bindings'][0]['derived_draft_sha256'])
                count = len(http.wires)
                run.run()
                self.assertEqual(len(http.wires), count)


if __name__ == '__main__':
    unittest.main()
