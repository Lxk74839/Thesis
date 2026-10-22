"""Synthetic PUBLIC Responses flows, never replays of the saved Q failures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest


def setUpModule():
    from tests.test_p1_wiring import setUpModule as offline_boundary
    offline_boundary()


class QualityOutputContract(unittest.TestCase):
    def flow(self, mutate=None, *, calls=18, count=5):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import RouterHTTPFixture, FIXTURE_BINDING
        from tests.test_fourrouter_production_protocol import reasoning
        from development_pilot import AUTHORIZATION
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget
        parent = Path(__file__).resolve().parents[1] / '.tmp/recommendation-runtime'
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        fixture = RuntimeFixture(Path(self.temp.name)).quality(['PUBLIC-' + str(i) for i in range(count)],
            scores=[round(1-i/100, 12) for i in range(count)])
        http = RouterHTTPFixture()
        frames = []
        def transport(text, *, deadline_ms):
            wire = json.loads(text)
            frame = (json.loads(wire['input'][-1]['content'])['runtime']
                if 'role' in wire['input'][-1] else None)
            business = copy.deepcopy(wire)
            business['input'] = [i for i in business['input'] if i.get('type') != 'reasoning']
            for item in business['input']:
                if item.get('type') == 'message':
                    item['content'] = ''.join(p['text'] for p in item['content'])
            envelope = http(json.dumps(business), deadline_ms=deadline_ms)
            if frame:
                frames.append(frame)
                text_part = envelope['body']['output'][0]['content'][0] if envelope['body']['output'][0]['type'] == 'message' else None
                if text_part:
                    reply = json.loads(text_part['text'])
                    if frame['stage'] == '农产品画像':
                        observations = reply['data']['observations']
                        if isinstance(observations, list):
                            reply['data']['observations'] = {o['candidate_id']: {
                                k: v for k, v in o.items() if k != 'candidate_id'} for o in reversed(observations)}
                    if frame.get('bound_draft_contract'):
                        for item in reply['data']['items']:
                            bundle = next(key for key, row in frame['citation_catalog'].items()
                                if row['candidate_id'] == item['parent_asin'] and 'member_ids' in row)
                            for reason in item['reasons']:
                                reason['citations'] = [bundle]
                        reply['data'].update(frame['draft_identifiers'])
                    override = mutate(frame, reply, envelope) if mutate else None
                    text_part['text'] = override if isinstance(override, str) else json.dumps(reply, ensure_ascii=False)
                envelope['body']['output'].insert(0, reasoning())
            return envelope
        model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
            'development_authorization': AUTHORIZATION, 'execution_authorized': True, 'pricing': None})
        run = fixture.make('M', model=model, arm='quality', prefix=count, binding_changes={
            'schema_version': 'rsm-run-0.4.0', 'execution_kind': 'fourrouter_responses',
            'project_id': 'PUBLIC-P1', 'authorization_id': AUTHORIZATION,
            'development_authorization': AUTHORIZATION, 'plan_source_scope': 'public_fixture',
            'orchestration': 'batch32-0.1.0', 'task_key': 'PUBLIC-Q-contract',
            'view_id': 'PUBLIC-view', 'material_version': 'PUBLIC-material',
            'request_profile_id': 'PUBLIC-request', 'profile_chunk_size': 4})
        limits = dict.fromkeys(SEngineeringBudget.resources, 100000)
        limits.update(model_calls=calls, request_output_tokens=(calls-1)*8192+1500,
            elapsed_ms=1780000, retries=0)
        reserve = dict.fromkeys(SEngineeringBudget.resources, 0)
        reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=145000)
        (run.output_root / 'budget.jsonl').unlink()  # Unused synthetic initialization only.
        budget = SEngineeringBudget(run.binding, limits, reserve, clock=lambda: fixture.now[0],
            journal_path=run.output_root / 'budget.jsonl')
        run.budget = run.evidence.root_budget = model.root_budget = budget
        return run, http, frames

    def test_keyed_profiles_preserve_raw_object_and_frozen_order_projection(self):
        run, http, _ = self.flow()
        result = run.run()
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertEqual(len(result['profile_object_bindings']), 2)
        from development_evaluation import read
        for item in result['profile_object_bindings']:
            raw = json.loads(read(item['raw_ref']))
            derived = json.loads(read(item['derived_ref']))
            self.assertIsInstance(raw, dict)
            self.assertEqual([o['candidate_id'] for o in derived], item['frozen_order'])
            self.assertEqual(set(raw), set(item['frozen_order']))
            self.assertTrue(all('candidate_id' not in value for value in raw.values()))
        self.assertEqual(len(http.wires), 10)
        self.assertEqual({v['status'] for v in result['components'].values()}, {'computed'})

    @staticmethod
    def ranking_issue(frame):
        issue = {'issue_id': 'PUBLIC-ranking-' + frame['draft']['draft_id'],
            'draft_id': frame['draft']['draft_id'], 'candidate_id': None, 'claim_id': None,
            'pointer': '/items', 'code': 'ranking_order_mismatch', 'blocking': True,
            'allowed_actions': ['revise_and_resubmit'], 'verifier': 'model', 'source_receipts': []}
        if frame.get('ranking_issue_contract'):
            issue.update(category='ranking', ranking_evidence={
                'observed_order': [i['parent_asin'] for i in frame['draft']['items']],
                'claimed_expected_order': frame['ordered'][:],
                'basis': copy.deepcopy(frame['ranking_contract']['basis']), 'first_difference': 0})
        return issue

    def test_invalid_sorting_claim_gets_one_explicit_correction_without_draft_revision(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'verification':
                reply['data']['issues'] = [self.ranking_issue(frame)]
        run, http, frames = self.flow(mutate)
        result = run.run()
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertNotIn('revision', [f['stage'] for f in frames])
        self.assertEqual([f['stage'] for f in frames].count('verification_correction'), 1)
        reviews = result['model_verifications']
        self.assertEqual([r['valid'] for r in reviews], [False, True])
        self.assertEqual(len(reviews[0]['issues']), 1)
        self.assertEqual(reviews[1]['issues'], [])
        self.assertEqual(len(http.wires), 11)

    def test_valid_ranking_claim_authorizes_only_the_bound_revision(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'draft':
                reply['data']['items'].reverse()
            if frame['stage'] == 'verification' and frame['draft']['parent_draft_id'] is None:
                reply['data']['issues'] = [self.ranking_issue(frame)]
        run, _, frames = self.flow(mutate)
        result = run.run()
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertEqual([f['stage'] for f in frames].count('revision'), 1)
        self.assertNotIn('verification_correction', [f['stage'] for f in frames])
        self.assertTrue(result['model_verifications'][0]['valid'])

    def test_missing_duplicate_extra_or_wrong_profile_bindings_are_rejected(self):
        for defect in ('missing', 'extra', 'duplicate_JSON_key', 'receipt', 'quality', 'citation'):
            with self.subTest(defect=defect):
                def mutate(frame, reply, envelope):
                    if frame['stage'] != '农产品画像':
                        return
                    values = reply['data']['observations']
                    key = next(iter(values))
                    if defect == 'missing':
                        values.pop(key)
                    elif defect == 'extra':
                        values['PUBLIC-unrequested'] = copy.deepcopy(values[key])
                    elif defect == 'receipt':
                        values[key]['assessment_receipt_id'] = 'PUBLIC-unbound'
                    elif defect == 'quality':
                        values[key]['quality']['m'] += .125
                    elif defect == 'citation':
                        values[key]['attributes'][0]['citation']['receipt_id'] = 'PUBLIC-unbound'
                    else:
                        pairs = list(values.items()) + [(key, values[key])]
                        body = ','.join(json.dumps(k) + ':' + json.dumps(v) for k, v in pairs)
                        return '{"kind":"analysis","data":{"necessary_clauses":["c1","c2"],"observations":{' + body + '}}}'
                run, _, _ = self.flow(mutate, count=4)
                result = run.run()
                self.assertEqual(result['terminal'], 'failed_model', result.get('reason'))
                self.assertIsNone(result['publication_path'])
                self.assertEqual(len(result['profiled_candidates']), 0)

    def test_old_array_duplicate_pattern_cannot_satisfy_the_new_object_contract(self):
        from provider_openai import role_output_schema, matches
        from development_evaluation import read
        run, _, frames = self.flow(count=4)
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        context = next(f for f in frames if f['stage'] == '农产品画像')
        raw = json.loads(read(result['profile_object_bindings'][0]['raw_ref']))
        parents = context['profile_candidates']
        # The saved real failure's pattern, with independent fictional candidates.
        old_reply = {'kind': 'analysis', 'data': {'necessary_clauses': ['c1','c2'],
            'observations': [{'candidate_id': parents[i], **raw[parents[i]]} for i in (1,2,3,2)]}}
        old_context = context | {'bound_profile_contract': 'acquired-product-bindings-0.2.0'}
        old_schema = role_output_schema('农产品画像','analysis',[{'role':'user','content':{'runtime':old_context}}])
        new_schema = role_output_schema('农产品画像','analysis',[{'role':'user','content':{'runtime':context}}])
        self.assertTrue(matches(old_reply, old_schema))
        self.assertFalse(matches(old_reply, new_schema))

    def test_repeated_invalid_verdict_fails_without_revision_or_publication(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] in ('verification', 'verification_correction'):
                reply['data']['issues'] = [self.ranking_issue(frame)]
        run, _, frames = self.flow(mutate)
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'invalid_model_issue_claim'))
        self.assertEqual([r['valid'] for r in result['model_verifications']], [False, False])
        self.assertEqual([f['stage'] for f in frames].count('verification_correction'), 1)
        self.assertNotIn('revision', [f['stage'] for f in frames])
        self.assertIsNone(result['publication_path'])

    def test_wrong_order_still_fails_the_original_final_gate(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] in ('draft', 'revision'):
                reply['data']['items'].reverse()
        run, _, _ = self.flow(mutate)
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('blocked_evidence', 'final_gate_blocked'))
        self.assertIn('invalid_order_or_count', [i['code'] for i in result['release_check']['issues']])
        self.assertIsNone(result['publication_path'])

    def test_correction_preserves_the_final_call_output_and_time_reserves(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'verification':
                reply['data']['issues'] = [self.ranking_issue(frame)]
        run, http, _ = self.flow(mutate, calls=10)
        result = run.run()
        self.assertEqual(result['terminal'], 'incomplete_budget', result.get('reason'))
        self.assertEqual(len(http.wires), 9)  # Correction cannot consume the reserved final call.
        self.assertEqual(result['budget']['usage']['model_calls'], 9)
        self.assertEqual(run.budget.final_reserve['elapsed_ms'], 145000)
        self.assertEqual(run.budget.final_reserve['request_output_tokens'], 1500)
        run, http, _ = self.flow(mutate, calls=11)
        result = run.run()
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertEqual(len(http.wires), 11)
        self.assertEqual(http.wires[-1]['max_output_tokens'], 1500)

    def test_mismatched_ranking_proof_is_retained_and_must_be_corrected(self):
        for field in ('observed_order', 'claimed_expected_order', 'basis', 'first_difference'):
            with self.subTest(field=field):
                def mutate(frame, reply, envelope):
                    if frame['stage'] == 'draft':
                        reply['data']['items'].reverse()
                    if frame['stage'] == 'verification' and frame['draft']['parent_draft_id'] is None:
                        issue = self.ranking_issue(frame)
                        if field in ('observed_order', 'claimed_expected_order'):
                            issue['ranking_evidence'][field] = list(reversed(issue['ranking_evidence'][field]))
                        elif field == 'basis':
                            issue['ranking_evidence']['basis']['G_sha256'] = 'PUBLIC-unbound'
                        elif field == 'first_difference':
                            issue['ranking_evidence'][field] = 1
                        reply['data']['issues'] = [issue]
                run, _, frames = self.flow(mutate)
                result = run.run()
                self.assertEqual(result['terminal'], 'released', result.get('reason'))
                self.assertFalse(result['model_verifications'][0]['valid'])
                self.assertTrue(result['model_verifications'][1]['valid'])
                self.assertEqual([f['stage'] for f in frames].count('verification_correction'), 1)

    def test_correction_is_once_per_run_even_after_a_valid_revision(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'draft':
                reply['data']['items'].reverse()
            if frame['stage'] in ('verification', 'verification_correction'):
                issue = self.ranking_issue(frame)
                if frame['stage'] == 'verification' and frame['draft']['parent_draft_id'] is None:
                    issue['ranking_evidence']['basis']['G_sha256'] = 'PUBLIC-unbound'
                reply['data']['issues'] = [issue]
        run, _, frames = self.flow(mutate)
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'invalid_model_issue_claim'))
        self.assertEqual([r['valid'] for r in result['model_verifications']], [False, True, False])
        self.assertEqual([f['stage'] for f in frames].count('verification_correction'), 1)
        self.assertEqual([f['stage'] for f in frames].count('revision'), 1)
        self.assertIsNone(result['publication_path'])

    def test_wrong_draft_binding_is_rejected_by_the_production_role_schema(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'verification':
                issue = self.ranking_issue(frame)
                issue['draft_id'] = 'PUBLIC-other-draft'
                reply['data']['issues'] = [issue]
        run, _, frames = self.flow(mutate)
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_model', 'role_schema_mismatch'))
        self.assertNotIn('revision', [f['stage'] for f in frames])
        self.assertIsNone(result['publication_path'])

    def test_full_32_candidate_Q_flow_keeps_all_three_components_and_final_reserve(self):
        def mutate(frame, reply, envelope):
            if frame['stage'] == 'verification':
                reply['data']['issues'] = [self.ranking_issue(frame)]
        run, http, _ = self.flow(mutate, count=32, calls=18)
        result = run.run()
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertEqual(len(result['profiled_candidates']), 32)
        self.assertEqual(len(result['G']), 32)
        self.assertEqual(len(http.wires), 17)
        self.assertEqual(http.wires[-1]['max_output_tokens'], 1500)
        self.assertEqual({v['status'] for v in result['components'].values()}, {'computed'})
        self.assertEqual({v['anchor_sha256'] for v in result['components'].values()},
            {result['components']['full']['anchor_sha256']})
        from experiment_io import _execution
        from experiment_runner import _path
        from experiment_evaluation import BINDING
        from development_evaluation import read, reference
        record = {k: result[k] for k in ('run_id', 'terminal', 'acquired_ref', 'audit_path', 'publication_path', 'delivered')}
        record.update(task_key=run.binding['task_key'], plan_id='PUBLIC-plan',
            audit_ref=reference(Path(result['audit_path'])), publication_ref=reference(Path(result['publication_path'])),
            budget_ref=reference(run.budget.journal_path))
        path = run.output_root / 'PUBLIC-result.json'; path.write_text(json.dumps(record))
        task = {k: run.binding['base_score_sha256' if k == 'base_scores_sha256' else k] for k in BINDING}
        task.update(task_key=run.binding['task_key'], base_scores=run.binding['base_scores'], method='M', scene='Q1')
        execution = _execution(task, reference(path), 'PUBLIC-plan', read_artifact=read, resolve_artifact=_path)
        self.assertTrue(execution['gate_passed'])
        self.assertTrue(execution['publication_verified'])


if __name__ == '__main__':
    unittest.main()
