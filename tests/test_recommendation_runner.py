"""P1 public runtime behavior on handwritten SIM facts."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from tests.runtime_fixtures import RuntimeFixture, ScriptedTransport

PROJECT = Path(__file__).resolve().parents[1]


class RecommendationRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/recommendation-runtime')
        self.addCleanup(self.temp.cleanup)
        self.fixture = RuntimeFixture(self.temp.name)

    def test_rule_run_publishes_from_actual_assessed_facts_without_a_model(self):
        run = self.fixture.make()
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['delivered'], ['PUBLIC-A'])
        self.assertEqual(run.audit_view()['G'], ['PUBLIC-A'])
        self.assertEqual(result['budget']['usage']['model_calls'], 0)
        self.assertTrue((Path(result['publication_path'])).is_file())
        self.assertEqual(result['release_scope'], 'public_fixture_only')

    def test_necessary_arm_stops_at_first_ten_qualified_without_truncating_C(self):
        self.fixture.candidates(['PUBLIC-A%02d' % i for i in range(1, 13)])
        run = self.fixture.make()
        result = run.run()
        self.assertEqual((result['cursor'], result['stop_reason']), (10, 'first_10_qualified'))
        self.assertEqual(len(result['binding']['C']), 12)
        self.assertEqual(len(run.audit_view()['evidence']['acquired']['candidates']), 10)

    def test_only_complete_C_can_prove_empty_not_an_empty_candidate_prefix(self):
        self.fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
        for row in self.fixture.facts.rows['materials.jsonl']:
            if row['kind'] == 'inspection_report':
                row['facts']['conclusion'] = 'fail'
        self.fixture.facts.register_all()
        self.fixture.facts.seal()
        full = self.fixture.make().run()
        self.assertEqual(full['terminal'], 'valid_empty')
        prefix = self.fixture.make(limits={'candidates': 1}).run()
        self.assertEqual((prefix['terminal'], prefix['reason']), ('blocked_evidence', 'empty_unproven'))
        self.assertEqual(prefix['cursor'], 1)

    def test_empty_C_still_completes_six_real_role_outputs_and_publishes_empty_proof(self):
        self.fixture.candidates([])
        run = self.fixture.make('M', model=ScriptedTransport().adapter())
        result = run.run()
        self.assertEqual(result['terminal'], 'valid_empty')
        self.assertEqual(len(result['roles_completed']), 6)
        self.assertEqual(result['budget']['usage']['physical_tools'], 0)
        self.assertEqual((result['cursor'], result['G'], result['delivered']), (0, [], []))

    def test_single_and_six_role_runs_use_actual_scripted_messages_and_tool_responses(self):
        expected = {'需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验'}
        for method in ('S', 'M'):
            with self.subTest(method=method):
                transport = ScriptedTransport()
                run = self.fixture.make(method, model=transport.adapter())
                result = run.run()
                self.assertEqual(result['terminal'], 'released')
                self.assertEqual(result['delivered'], ['PUBLIC-A'])
                self.assertEqual(set(result['roles_completed']), {'单智能体'} if method == 'S' else expected)
                self.assertEqual(result['budget']['usage']['model_calls'], len(transport.requests))
                self.assertTrue(result['dispatches'])
                self.assertTrue(any(m['role'] == 'tool' for req in transport.requests for m in req['messages']))
                self.assertEqual(result['provider_requests_sent'], 0)

    def test_r_s_m_share_full_safe_history_and_the_actual_verification_time(self):
        self.fixture.history = [{'parent_asin': 'PUBLIC-HISTORY', 'review_text': '公开人工历史原文'}]
        projections = []
        for method in ('R', 'S', 'M'):
            transport = ScriptedTransport()
            run = self.fixture.make(method, model=transport.adapter() if method != 'R' else None)
            result = run.run()
            self.assertEqual(result['terminal'], 'released')
            projections.append(result['input_projection_sha256'])
            if method != 'R':
                for req in transport.requests:
                    payload = json.loads(req['messages'][1]['content'])
                    self.assertEqual(payload['H'], self.fixture.history)
                    self.assertEqual(payload['verify_at_ms'], 1000)
        self.assertEqual(len(set(projections)), 1)

    def test_issue_bound_revision_keeps_old_draft_and_does_not_fetch_more_evidence(self):
        def wrong_citation(req, raw, context):
            if context['stage'] == 'draft' and req['output_kind'] == 'draft':
                report = next(f['citation'] for f in context['facts']['PUBLIC-A']
                              if f['data'].get('kind') == 'inspection_report')
                raw['message']['content']['data']['items'][0]['reasons'][1]['citations'] = [report]
        transport = ScriptedTransport(mutate=wrong_citation)
        run = self.fixture.make('M', model=transport.adapter())
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['feedback_round'], 1)
        self.assertEqual(len(result['drafts']), 2)
        self.assertTrue(result['revisions'])
        self.assertIn('wrong_attribute_citation', [i['code'] for i in result['issues']])
        self.assertEqual(result['budget']['usage']['physical_tools'], 2)
        self.assertNotEqual(result['drafts'][0], result['drafts'][1])

    def test_stock_reason_can_be_repaired_only_to_the_same_acquired_stock_field(self):
        self.fixture.quality(['PUBLIC-A'])
        def stock(req, raw, context):
            if req['output_kind'] != 'draft':
                return
            field = 'inspection_report' if context['stage'] == 'draft' else 'retail_status'
            cite = next(dict(f['citation'], pointer='/facts/stock_units') for f in context['facts']['PUBLIC-A']
                        if f['data'].get('kind') == field)
            raw['message']['content']['data']['items'][0]['reasons'].append({'claim_id': 'retail_stock',
                'kind': 'retail_stock', 'value': 75, 'unit': 'units', 'text': '可售库存为75单位（SIM）。', 'citations': [cite]})
        run = self.fixture.make('M', model=ScriptedTransport(mutate=stock).adapter(), arm='quality', prefix=1)
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['feedback_round'], 1)
        self.assertEqual(result['drafts'][-1]['items'][0]['reasons'][-1]['value'], 75)
        self.assertEqual(result['budget']['usage']['physical_tools'], 2)
        self.assertTrue(any('/citations/' in r['pointer'] for r in result['revisions']))

    def test_base_preference_is_bound_to_safe_projection_and_exact_decimal_text(self):
        for wrong in (False, True):
            def preference(req, raw, context, wrong=wrong):
                if req['output_kind'] == 'draft':
                    base = context.get('base_preferences', {}).get('PUBLIC-A', {'citation': {}})
                    raw['message']['content']['data']['items'][0]['reasons'].append({
                        'claim_id': 'base_preference', 'kind': 'base_preference', 'value': .9, 'unit': None,
                        'text': '偏好基础分为0.900000000000。' if not wrong else '偏好基础分为0.9。',
                        'citations': [base['citation']]})
            run = self.fixture.make('M', model=ScriptedTransport(mutate=preference).adapter())
            result = run.run()
            self.assertEqual(result['terminal'], 'blocked_evidence' if wrong else 'released')
            self.assertEqual(result['budget']['usage']['physical_tools'], 2)

    def test_stock_reason_requires_the_quality_same_attribute_support_not_only_necessary_G(self):
        import copy
        self.fixture.quality(['PUBLIC-A'])
        other = copy.deepcopy(next(row for row in self.fixture.facts.rows['materials.jsonl'] if row['kind'] == 'retail_status'))
        other['evidence_id'] = 'D-PUBLIC-CONFLICT'
        other['facts']['stock_units'] = 25
        self.fixture.facts.add('materials.jsonl', other)
        self.fixture.seal()
        def stock(req, raw, context):
            if req['output_kind'] == 'draft':
                cite = next(dict(f['citation'], pointer='/facts/stock_units') for f in context['facts']['PUBLIC-A']
                            if f['data'].get('kind') == 'retail_status')
                raw['message']['content']['data']['items'][0]['reasons'].append({'claim_id': 'retail_stock',
                    'kind': 'retail_stock', 'value': 75, 'unit': 'units', 'text': '可售库存为75单位（SIM）。', 'citations': [cite]})
        result = self.fixture.make('M', model=ScriptedTransport(mutate=stock).adapter(), arm='quality', prefix=1).run()
        self.assertEqual(result['G'], ['PUBLIC-A'])
        self.assertEqual(result['terminal'], 'blocked_evidence')

    def test_whole_delivery_gate_rejects_bad_tail_order_batch_pointer_and_prose(self):
        self.fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
        for fault in ('tail', 'order', 'batch', 'pointer', 'prose', 'value'):
            def corrupt(req, raw, context, fault=fault):
                if req['output_kind'] != 'draft':
                    return
                items = raw['message']['content']['data']['items']
                if fault == 'tail':
                    items.extend([items[0]] * 9)
                elif fault == 'order':
                    items.reverse()
                elif fault == 'batch':
                    items[0]['sim_batch_id'] = 'OTHER-BATCH'
                elif fault == 'pointer':
                    items[0]['reasons'][0]['citations'][0]['pointer'] = '/absent'
                elif fault == 'prose':
                    items[0]['reasons'][0]['text'] = '真实品质更安全。'
                else:
                    items[0]['reasons'][0]['value'] = False
            with self.subTest(fault=fault):
                run = self.fixture.make('M', model=ScriptedTransport(mutate=corrupt).adapter())
                result = run.run()
                self.assertEqual(result['terminal'], 'blocked_evidence')
                self.assertEqual(result['delivered'], [])
                self.assertTrue(result['release_check']['issues'])
                self.assertEqual(result['feedback_round'], 1)
                self.assertEqual(len(result['drafts'][0]['items']), 11 if fault == 'tail' else 2)

    def test_a_real_but_irrelevant_pointer_cannot_support_a_necessary_claim(self):
        def irrelevant(req, raw, context):
            if req['output_kind'] == 'draft':
                for reason in raw['message']['content']['data']['items'][0]['reasons']:
                    for cite in reason['citations']:
                        cite['pointer'] = '/parent_asin'
        run = self.fixture.make('M', model=ScriptedTransport(mutate=irrelevant).adapter())
        result = run.run()
        self.assertEqual(result['terminal'], 'blocked_evidence')
        self.assertEqual(result['budget']['usage']['physical_tools'], 2)

    def test_verifier_issues_must_be_closed_and_bound_to_the_actual_draft_and_receipts(self):
        for fault in ('missing', 'draft', 'receipt'):
            def bad_issue(req, raw, context, fault=fault):
                if req['output_kind'] == 'verification':
                    issue = {'issue_id': 'PUBLIC-ISSUE', 'draft_id': context['draft']['draft_id'],
                        'candidate_id': 'PUBLIC-A', 'claim_id': 'c1', 'pointer': '/items/0/reasons/0',
                        'code': 'check_citation', 'blocking': True, 'allowed_actions': ['revise_and_resubmit'],
                        'verifier': 'model', 'source_receipts': []}
                    if fault == 'missing':
                        issue.pop('pointer')
                    elif fault == 'draft':
                        issue['draft_id'] = 'OTHER'
                    else:
                        issue['source_receipts'] = ['OTHER-ROOT']
                    raw['message']['content']['data']['issues'] = [issue]
            result = self.fixture.make('M', model=ScriptedTransport(mutate=bad_issue).adapter()).run()
            self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'invalid_model_issue'))
            self.assertEqual(result['delivered'], [])

    def test_real_execution_and_unbound_or_changed_inputs_stop_before_fact_io(self):
        for change in ({'execution_kind': 'provider_real'}, {'execution_authorized': True},
                       {'C_sha256': 'WRONG'}, {'arm': 'quality', 'prefix_limit': None}):
            with self.subTest(change=change):
                run = self.fixture.make(binding_changes=change)
                result = run.run()
                self.assertEqual(result['terminal'], 'failed_protocol')
                self.assertEqual(result['budget']['usage']['physical_tools'], 0)
                self.assertEqual(result['budget']['usage']['model_calls'], 0)
        self.assertEqual(self.fixture.make(limits={'model_calls': 1}).run()['terminal'], 'failed_protocol')

    def test_fusion_cannot_change_the_approved_weights_or_root_identity(self):
        import copy
        self.fixture.quality()
        declared = self.fixture.make('M', model=ScriptedTransport().adapter(), arm='quality', prefix=2).audit_view()['binding']['fusion']
        for field, value in (('alpha', .9), ('beta', [1, 0, 0]), ('H_sha256', 'OTHER'), ('task_id', 'OTHER')):
            fusion = copy.deepcopy(declared)
            fusion[field] = value
            run = self.fixture.make('M', model=ScriptedTransport().adapter(), arm='quality', prefix=2,
                                    binding_changes={'fusion': fusion})
            result = run.run()
            self.assertEqual((result['terminal'], result['budget']['usage']['physical_tools']), ('failed_protocol', 0))

    def test_quality_components_share_the_frozen_anchor_and_hand_worked_scores(self):
        import hashlib
        from evidence_access import encoded
        self.fixture.quality(['PUBLIC-A', 'PUBLIC-B', 'PUBLIC-HI', 'PUBLIC-LO'], [.9, .6, 1, 0])
        transport = ScriptedTransport()
        run = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4)
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['delivered'], ['PUBLIC-B', 'PUBLIC-A', 'PUBLIC-HI', 'PUBLIC-LO'])
        components = result['components']
        self.assertEqual([r['score'] for r in components['full']['candidates']], [.675, .75, .5, 0])
        self.assertEqual([r['score'] for r in components['no_quality']['candidates']], [.825, .8, .5, 0])
        self.assertEqual([r['score'] for r in components['mean_quality']['candidates']], [.703125, .6375, .5, 0])
        self.assertEqual(components['mean_quality']['mean_quality'], {'value': .675, 'denominator': 4})
        self.assertEqual(len({c['anchor_sha256'] for c in components.values()}), 1)
        self.assertEqual(result['budget']['usage']['physical_tools'], 8)
        self.assertEqual(result['budget']['usage']['model_calls'], len(transport.requests))
        anchor = components['full']['anchor']
        self.assertEqual(anchor['fusion_sha256'], hashlib.sha256(encoded(result['binding']['fusion'])).hexdigest())
        self.assertEqual(anchor['publication_record_sha256'], hashlib.sha256(Path(result['publication_path']).read_bytes()).hexdigest())
        self.assertEqual(anchor['H_sha256'], result['binding']['H_sha256'])

    def test_quality_prefix_keeps_processing_after_ten_and_does_not_read_the_tail(self):
        self.fixture.quality(['PUBLIC-A%02d' % i for i in range(1, 13)])
        run = self.fixture.make('M', model=ScriptedTransport().adapter(), arm='quality', prefix=11,
                                limits={'input_tokens': 1000000000})
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual((result['cursor'], result['stop_reason'], len(result['G'])), (11, 'quality_prefix', 11))
        self.assertEqual(len(run.audit_view()['evidence']['acquired']['candidates']), 11)
        self.assertEqual(len(result['delivered']), 10)

    def test_unassessed_current_candidate_is_not_skipped_or_filled_by_the_host(self):
        self.fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
        run = self.fixture.make('M', model=ScriptedTransport(empty_acquisition=True).adapter())
        result = run.run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'current_incomplete'))
        self.assertEqual((result['cursor'], result['G']), (0, []))
        self.assertEqual(run.audit_view()['evidence']['acquired']['candidates'], {})

    def test_positive_first_page_cannot_skip_unfinished_registration_pages(self):
        self.fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
        for number in range(23):
            self.fixture.facts.add('materials.jsonl', {'schema_version': 'sim-material-1.0.0', 'source': 'SIM',
                'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'version': 1, 'evidence_id': 'D-H-' + str(number),
                'kind': 'harvest_record', 'issuer_id': 'SIM-PRODUCER', 'event_id': 'E-A-harvest', 'issued_at_ms': 22,
                'temporal_mode': 'historical_fact', 'facts': {'origin_area_id': 'AREA-1'}})
        self.fixture.facts.policy['issuers'][0]['material_kinds'].append('harvest_record')
        self.fixture.facts.policy['read_scope']['material_kinds'].append('harvest_record')
        self.fixture.seal()
        def early(req, raw, context):
            calls = raw['message']['tool_requests']
            if calls and calls[0]['name'] == 'list_evidence' and calls[0]['arguments']['cursor'] is not None:
                raw['message'].update(content={'kind': 'acquire', 'data': {'done': True}}, tool_requests=[])
                raw['finish_reason'] = 'stop'
        run = self.fixture.make('M', model=ScriptedTransport(mutate=early).adapter())
        result = run.run()
        self.assertEqual((result['terminal'], result['cursor'], result['G']), ('failed_protocol', 0, []))
        acquired = run.audit_view()['evidence']['acquired']['candidates']
        self.assertEqual(set(acquired), {'PUBLIC-A'})
        self.assertFalse(acquired['PUBLIC-A']['enumeration_complete'])

    def test_model_format_repair_and_tool_retry_share_two_retries_and_backoff(self):
        from evidence_access import LocalEvidenceSource
        class Flaky(LocalEvidenceSource):
            def read(self, registrations):
                if not getattr(self, 'failed', False):
                    self.failed = True
                    raise OSError('PUBLIC transient read')
                return super().read(registrations)
        first = [True]
        def format_once(req, raw, context):
            if first[0]:
                first[0] = False
                raw['message']['content']['kind'] = 'WRONG'
        run = self.fixture.make('M', model=ScriptedTransport(mutate=format_once).adapter(), source_type=Flaky)
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['budget']['usage']['retries'], 2)
        self.assertEqual(result['budget']['usage']['elapsed_ms'], 3000)
        self.assertEqual(result['budget']['usage']['physical_tools'], 3)

    def test_acquired_but_unassessed_candidate_never_enters_G_and_all_components_fail_together(self):
        self.fixture.quality()
        def unfinished(req, raw, context):
            if context['current'] == 'PUBLIC-B' and raw['message']['content'] == {'kind': 'acquire', 'data': {'done': True}}:
                raw['message']['content']['data']['done'] = False
        run = self.fixture.make('M', model=ScriptedTransport(mutate=unfinished).adapter(), arm='quality', prefix=2)
        result = run.run()
        self.assertEqual(result['terminal'], 'failed_protocol')
        self.assertEqual((result['G'], result['cursor']), (['PUBLIC-A'], 1))
        self.assertTrue(run.audit_view()['evidence']['acquired']['candidates']['PUBLIC-B']['originals'])
        self.assertEqual({c['status'] for c in result['components'].values()}, {'anchor_failed'})
        self.assertEqual({c['failure_rule'] for c in result['components'].values()}, {'F1_zero_if_reference_applicable'})
        self.assertEqual(len({c['anchor_sha256'] for c in result['components'].values()}), 1)

    def test_failed_publication_never_releases_and_existing_records_are_not_overwritten(self):
        run = self.fixture.make()
        with patch('recommendation_runner.os.rename', side_effect=OSError('PUBLIC commit failure')):
            result = run.run()
        self.assertEqual((result['terminal'], result['delivered']), ('failed_protocol', []))
        self.assertIsNone(result['publication_path'])
        self.assertTrue(result['budget']['usage_exact'])
        other = self.fixture.make()
        target = other.output_root / 'publication.json'
        target.write_bytes(b'KEEP')
        result = other.run()
        self.assertEqual(result['terminal'], 'failed_protocol')
        self.assertEqual(target.read_bytes(), b'KEEP')

    def test_unknown_model_usage_and_late_models_stop_without_new_work(self):
        for fault in ('unknown', 'late', 'format'):
            def fail(req, raw, context, fault=fault):
                if fault == 'unknown':
                    raw['usage']['output_tokens'] = None
                elif fault == 'late':
                    self.fixture.now[0] += 45001
                else:
                    raw['message']['content']['kind'] = 'WRONG'
            run = self.fixture.make('M', model=ScriptedTransport(mutate=fail).adapter())
            result = run.run()
            self.assertEqual(result['terminal'], 'incomplete_deadline' if fault == 'late' else
                             'incomplete_budget' if fault == 'format' else 'failed_model')
            self.assertEqual(result['budget']['usage']['model_calls'], 3 if fault == 'format' else 1)
            self.assertEqual(result['budget']['usage']['retries'], 2 if fault == 'format' else 0)
            self.assertEqual(result['budget']['usage']['physical_tools'], 0)
            self.assertEqual(result['delivered'], [])
            if fault == 'unknown':
                self.assertFalse(result['budget']['usage_exact'])
                self.assertGreater(result['budget']['held']['output_tokens'], 0)
            elif fault == 'format':
                self.assertEqual(result['budget']['usage']['elapsed_ms'], 3000)
            self.assertFalse((run.output_root / 'publication.json').exists())

    def test_model_request_intent_is_durable_before_the_transport_and_response_is_journaled(self):
        from model_adapter import ModelAdapter
        def timeout(req):
            rows = [json.loads(line) for line in (run.output_root / 'budget.jsonl').read_text(encoding='utf-8').splitlines()]
            intent = rows[-1]['operation']
            self.assertIsInstance(intent, dict)
            self.assertEqual(intent['request_id'], req['request_id'])
            self.assertEqual(intent['messages'], req['messages'])
            raise TimeoutError('PUBLIC interrupted response')
        adapter = ModelAdapter(timeout, capability_binding={'execution_kind': 'scripted_public', 'model_id': None, 'provenance': 'scripted'})
        run = self.fixture.make('M', model=adapter)
        result = run.run()
        self.assertEqual(result['terminal'], 'failed_model')
        rows = [json.loads(line) for line in (run.output_root / 'budget.jsonl').read_text(encoding='utf-8').splitlines()]
        observed = next(r['observation'] for r in rows if r.get('status') == 'unresolved')
        self.assertEqual(observed['request']['request_id'], result['messages'][0]['role_message_id'])
        self.assertEqual(observed['response']['status'], 'timeout')

    def test_commit_time_is_in_the_root_and_late_commit_is_not_published(self):
        import os
        rename = os.rename
        def slow_commit(source, target):
            rename(source, target)
            if Path(target).name == 'publication.json':
                self.fixture.now[0] += 45001
        run = self.fixture.make()
        with patch('recommendation_runner.os.rename', side_effect=slow_commit):
            result = run.run()
        self.assertEqual((result['terminal'], result['delivered']), ('incomplete_deadline', []))
        self.assertFalse((run.output_root / 'publication.json').exists())
        self.assertTrue((run.output_root / 'publication.failed.json').exists())
        self.assertEqual(result['budget']['usage']['elapsed_ms'], 45001)

    def test_audit_seal_failure_invalidates_publication_and_keeps_failure_evidence(self):
        original = Path.open
        def fail_audit(path, *args, **kwargs):
            if path.name == 'audit.json':
                raise OSError('PUBLIC audit seal failure')
            return original(path, *args, **kwargs)
        run = self.fixture.make()
        with patch.object(Path, 'open', fail_audit):
            result = run.run()
        self.assertEqual((result['terminal'], result['delivered']), ('failed_protocol', []))
        self.assertIsNone(result['publication_path'])
        self.assertFalse((run.output_root / 'publication.json').exists())
        self.assertTrue((run.output_root / 'audit.failed.json').is_file())

    def test_pending_root_intent_prevents_the_final_gate_even_when_its_hold_is_zero(self):
        run = self.fixture.make()
        run.budget.reserve('unfinished-host-intent', {}, phase='work', retry_of=None)
        result = run.run()
        self.assertEqual((result['terminal'], result['delivered']), ('failed_protocol', []))
        self.assertFalse(result['budget']['usage_exact'])
        self.assertFalse((run.output_root / 'publication.json').exists())
