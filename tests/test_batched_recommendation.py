"""Offline batch behaviors at the authorized public runtime and evidence seams."""
from pathlib import Path
import copy
import os
import tempfile
import unittest

from evidence_access import LocalEvidenceSource, encoded
from model_adapter import ModelAdapter
from tests.runtime_fixtures import RuntimeFixture, ScriptedTransport

PROJECT = Path(__file__).resolve().parents[1]


class BatchTransport(ScriptedTransport):
    """External scripted model; decisions use only its actual input messages."""
    def __init__(self, mutate=None, after=None):
        super().__init__(mutate=mutate)
        self.after = after

    def __call__(self, request):
        index = max(i for i, m in enumerate(request['messages']) if m['role'] == 'user'
                    and isinstance(m['content'], dict) and 'runtime' in m['content'])
        context = request['messages'][index]['content']['runtime']
        kind = request['output_kind']
        if kind == 'analysis' and context['stage'] == '农产品画像':
            self.requests.append(copy.deepcopy(request))
            raw = {'request_id': request['request_id'], 'model_id': None, 'finish_reason': 'stop',
                'message': {'content': None}, 'usage': {'cost_microusd': 0,
                    'input_tokens': len(encoded({'messages': request['messages'], 'tools': request['tools']}))}, 'error': None}
        else:
            raw = super().__call__(request)
        data, calls = raw['message']['content'], []
        if kind == 'dispatch':
            data['data']['candidate_limit'] = context.get('batch_limit', 32)
        elif kind == 'acquire':
            results = [m['content'] for m in request['messages'][index + 1:] if m['role'] == 'tool']
            batches = [r for r in results if 'processed' in r]
            if batches:
                batch = batches[-1]
                data = {'kind': kind, 'data': {'done': True, 'plan_sha256': batch['plan_sha256'],
                                              'processed': batch['processed']}}
            else:
                calls = [{'call_id': request['attempt_id'] + ':batch', 'name': 'acquire_batch',
                    'arguments': {'schema_version': 'acquisition-batch-0.1.0',
                        'start_candidate': context['current'], 'candidate_limit': context.get('batch_limit', 32),
                        'claim_ids': ['c1', 'c2'], 'max_list_pages': 32, 'max_read_batches': 32,
                        'stop_policy': 'fixed_prefix' if context['quality_arm'] else 'first_10_qualified'}}]
                data = None
        elif kind == 'analysis' and context['stage'] == '农产品画像':
            observations = []
            for parent in context['profile_candidates']:
                assessment, quality = context['assessments'][parent], context['quality'].get(parent)
                attributes = []
                for fact in context['facts'][parent]:
                    row = fact['data']
                    for key in (('conclusion',) if row.get('kind') == 'inspection_report' else
                                ('status', 'stock_units') if row.get('kind') == 'retail_status' else ()):
                        if key in row['facts']:
                            attributes.append({'attribute': key,
                                'citation': {**fact['citation'], 'pointer': '/facts/' + key}})
                observations.append({'candidate_id': parent,
                    'assessment_receipt_id': context['assessment_receipts'][parent], 'quality': quality,
                    'attributes': attributes, 'unknown': [c for c, v in assessment['claims'].items()
                        if v['evidence_state'] != 'Supported'] + (['retail_stock'] if quality and not quality['z'] else [])})
            data = {'kind': kind, 'data': {'necessary_clauses': ['c1', 'c2'], 'observations': observations}}
        raw['finish_reason'] = 'tool_calls' if calls else 'stop'
        raw['message'] = {'role': 'assistant', 'content': data, 'tool_requests': calls}
        raw['usage']['output_tokens'] = len(encoded(raw['message']))
        if kind == 'analysis' and context['stage'] == '农产品画像' and self.mutate:
            self.mutate(request, raw, context)
        if self.after:
            self.after(request, raw, context)
        return raw


class BatchedRecommendationTests(unittest.TestCase):
    def setUp(self):
        parent = PROJECT / 'data/recommendation-runtime-audit/20261018-batch/cases' / os.environ.get('THESIS_BATCH_CHECK_LABEL', 'manual')
        parent.mkdir(parents=True, exist_ok=True)
        self.case_root = Path(tempfile.mkdtemp(prefix=self._testMethodName[5:29] + '-', dir=parent))
        self.fixture = RuntimeFixture(self.case_root)

    def test_explicit_batch_accounts_for_each_acquisition_and_assessment(self):
        run = self.fixture.make('M', model=ScriptedTransport().adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'})
        result = run.evidence.dispatch('acquire_batch', {
            'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A',
            'candidate_limit': 1, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 1,
            'max_read_batches': 1, 'stop_policy': 'first_10_qualified'}, actor_role='生命周期追溯')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['processed'], ['PUBLIC-A'])
        self.assertEqual(result['assessments']['PUBLIC-A']['evidence_state'], 'Supported')
        self.assertEqual(result['usage_after']['logical_tools'], 25)
        self.assertEqual(result['usage_after']['physical_tools'], 2)
        self.assertEqual(result['usage_after']['candidates'], 1)
        self.assertEqual([r['operation'] for r in result['steps']],
                         ['begin_batch', 'list_evidence', 'read_evidence', 'assess_current'])

    def test_batch_stops_inside_window_at_tenth_eligible_without_reading_eleventh(self):
        self.fixture.candidates(['PUBLIC-A%02d' % i for i in range(1, 13)])
        run = self.fixture.make('M', model=ScriptedTransport().adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'})
        result = run.evidence.dispatch('acquire_batch', {
            'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A01',
            'candidate_limit': 32, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 32,
            'max_read_batches': 32, 'stop_policy': 'first_10_qualified'}, actor_role='生命周期追溯')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['processed'], ['PUBLIC-A%02d' % i for i in range(1, 11)])
        self.assertEqual(result['stop_reason'], 'first_10_qualified')
        self.assertEqual(result['usage_after']['logical_tools'], 223)
        self.assertEqual(result['usage_after']['physical_tools'], 20)
        self.assertEqual(len(result['observations']), 10)
        self.assertNotIn('PUBLIC-A11', [s['candidate_id'] for s in result['steps']])

    def test_four_quality_candidates_have_six_roles_and_nine_actual_calls(self):
        self.fixture.quality(['PUBLIC-HI', 'PUBLIC-A', 'PUBLIC-B', 'PUBLIC-LO'])
        transport = BatchTransport()
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['budget']['usage']['model_calls'], 9)
        self.assertEqual(len(transport.requests), 9)
        self.assertEqual(set(result['roles_completed']),
            {'需求解析', '用户画像', '推荐管理', '生命周期追溯', '农产品画像', '推荐依据核验'})
        self.assertEqual(result['profiled_candidates'], ['PUBLIC-HI', 'PUBLIC-A', 'PUBLIC-B', 'PUBLIC-LO'])
        self.assertEqual(len(result['binding']['C']), 4)
        self.assertEqual(result['budget']['usage']['logical_tools'], 134)
        self.assertEqual(result['budget']['usage']['physical_tools'], 8)

    def test_one_dispatch_cannot_authorize_more_than_thirty_two_candidates(self):
        parents = ['PUBLIC-A%02d' % i for i in range(1, 35)]
        self.fixture.quality(parents, scores=[.9] * 34)

        def overflow(request, raw, context):
            if request['output_kind'] != 'acquire':
                return
            batches = [m['content'] for m in request['messages'] if m['role'] == 'tool' and 'processed' in m['content']]
            if len(batches) == 1:
                raw['finish_reason'] = 'tool_calls'
                raw['message'] = {'role': 'assistant', 'content': None, 'tool_requests': [{
                    'call_id': request['attempt_id'] + ':overflow', 'name': 'acquire_batch', 'arguments': {
                        'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A33',
                        'candidate_limit': 2, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 2,
                        'max_read_batches': 2, 'stop_policy': 'fixed_prefix'}}]}
            elif len(batches) == 2:
                raw['message']['content']['data']['processed'] = parents
            raw['usage']['output_tokens'] = len(encoded(raw['message']))

        result = self.fixture.make('M', model=BatchTransport(after=overflow).adapter(), arm='quality', prefix=34,
            limits={'input_tokens': 100000000}, binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'batch_dispatch_exhausted'))
        self.assertEqual(result['cursor'], 32)
        self.assertEqual(result['budget']['usage']['physical_tools'], 64)

    def test_necessary_runtime_publishes_immediately_after_tenth_qualified(self):
        self.fixture.candidates(['PUBLIC-A%02d' % i for i in range(1, 13)])
        transport = BatchTransport()
        result = self.fixture.make('M', model=transport.adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual((result['terminal'], result['cursor'], result['stop_reason']),
                         ('released', 10, 'first_10_qualified'))
        self.assertEqual(result['budget']['usage']['model_calls'], 9)
        self.assertEqual(result['budget']['usage']['physical_tools'], 20)
        self.assertEqual(result['binding']['C'][-2:], ['PUBLIC-A11', 'PUBLIC-A12'])
        self.assertEqual(result['profiled_candidates'], result['binding']['C'][:10])

    def test_batch_messages_preserve_full_information_without_repeated_runtime_frames(self):
        self.fixture.quality(['PUBLIC-A%02d' % i for i in range(1, 13)])
        self.fixture.history = [{'parent_asin': 'PUBLIC-HISTORY', 'review_text': 'public complete history'}]
        for method in ('M', 'S'):
            with self.subTest(method=method):
                transport = BatchTransport()
                result = self.fixture.make(method, model=transport.adapter(), arm='quality', prefix=12,
                    binding_changes={'orchestration': 'batch32-0.1.0'}).run()
                self.assertEqual(result['terminal'], 'released')
                self.assertEqual(result['budget']['usage']['model_calls'], 9)
                for request in transport.requests:
                    frames = [m['content']['runtime'] for m in request['messages'] if m['role'] == 'user'
                              and isinstance(m['content'], dict) and 'runtime' in m['content']]
                    self.assertEqual(len(frames), 1)
                    self.assertEqual(len(frames[0]['candidate_batches']), 12)
                    self.assertEqual(len(frames[0]['base_preferences']), 12)
                    self.assertEqual(frames[0]['history'], self.fixture.history)
                    self.assertEqual(request['session_id'], request['run_id'] + ':' + request['role'])
                if method == 'M':
                    self.assertEqual(result['components']['full']['topK'], result['delivered'])

    def test_sixty_four_prefix_uses_two_batches_and_thirteen_calls_without_truncating_C(self):
        parents = ['PUBLIC-A%02d' % i for i in range(1, 67)]
        self.fixture.quality(parents, scores=[round(.9 - i / 1000, 12) for i in range(66)])
        transport = BatchTransport()
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=64,
            limits={'model_calls': 13, 'input_tokens': 100000000},
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual((result['terminal'], result['cursor'], result['stop_reason']),
                         ('released', 64, 'quality_prefix'))
        self.assertEqual(result['budget']['usage']['model_calls'], 13)
        self.assertEqual(len(transport.requests), 13)
        self.assertEqual([len(b['processed']) for b in result['batches']], [32, 32])
        self.assertEqual(result['profiled_candidates'], parents[:64])
        self.assertEqual(result['binding']['C'], parents)
        self.assertEqual(result['budget']['usage']['logical_tools'], 2055)
        self.assertEqual(result['budget']['usage']['physical_tools'], 128)

    def test_finished_batch_cannot_reopen_its_last_closed_candidate(self):
        run = self.fixture.make('M', model=ScriptedTransport().adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'})
        plan = {'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A',
            'candidate_limit': 1, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 1,
            'max_read_batches': 1, 'stop_policy': 'first_10_qualified'}
        first = run.evidence.dispatch('acquire_batch', plan, actor_role='生命周期追溯')
        self.assertEqual(first['status'], 'ok')
        again = run.evidence.dispatch('acquire_batch', plan, actor_role='生命周期追溯')
        self.assertEqual(again['status'], 'access_denied')
        self.assertEqual(again['receipt']['root_usage_after']['physical_tools'], 2)
        self.assertEqual(again['receipt']['root_usage_after']['candidates'], 1)

    def test_additional_trace_round_is_charged_and_profiles_all_acquired_candidates(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])

        def split_batch(request, raw, context):
            if request['output_kind'] != 'acquire':
                return
            batches = [m['content'] for m in request['messages'] if m['role'] == 'tool'
                       and 'processed' in m['content']]
            if len(batches) < 2:
                raw['finish_reason'] = 'tool_calls'
                raw['message'] = {'role': 'assistant', 'content': None, 'tool_requests': [{
                    'call_id': request['attempt_id'] + ':partial', 'name': 'acquire_batch', 'arguments': {
                        'schema_version': 'acquisition-batch-0.1.0',
                        'start_candidate': 'PUBLIC-A03' if batches else 'PUBLIC-A01',
                        'candidate_limit': 2, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 2,
                        'max_read_batches': 2, 'stop_policy': 'fixed_prefix'}}]}
            else:
                raw['message']['content']['data']['processed'] = ['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04']
            raw['usage']['output_tokens'] = len(encoded(raw['message']))

        transport = BatchTransport(after=split_batch)
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['budget']['usage']['model_calls'], 10)
        self.assertEqual(result['budget']['usage']['logical_tools'], 135)
        self.assertEqual(result['profiled_candidates'], ['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])
        self.assertEqual(len(result['batches']), 2)

    def test_final_submission_fits_protected_remaining_time_without_new_work(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])
        fixture = self.fixture

        class ClockedSource(LocalEvidenceSource):
            def list(self, *args, **kwargs):
                result = super().list(*args, **kwargs)
                fixture.now[0] += 40000
                return result

            def read(self, *args, **kwargs):
                result = super().read(*args, **kwargs)
                fixture.now[0] += 40000
                return result

        def model_latency(request, raw, context):
            fixture.now[0] += 45000 if request['output_kind'] == 'final_submit' else 27500

        transport = BatchTransport(after=model_latency)
        result = fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            source_type=ClockedSource, final_reserve={'elapsed_ms': 60000},
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'released', {
            'reason': result['reason'], 'usage': result['budget']['usage'],
            'last_statuses': [r['status'] for r in result['budget']['receipts'][-2:]]})
        self.assertEqual(result['budget']['usage']['elapsed_ms'], 585000)
        self.assertEqual(result['budget']['usage']['physical_tools'], 8)
        self.assertEqual(result['budget']['usage']['model_calls'], 9)
        self.assertTrue(result['budget']['usage_exact'])

    def test_feedback_and_two_known_retries_share_the_same_root_account(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])
        errors = []

        def rate_limit(request, raw, context):
            if context['stage'] == '需求解析' and len(errors) < 2:
                errors.append(request['attempt_id'])
                raw.update(finish_reason='error', error={'category': 'rate_limit'})
                raw['usage']['output_tokens'] = 7

        def wrong_reason(request, raw, context):
            if context['stage'] == 'draft':
                report = next(f['citation'] for f in context['facts']['PUBLIC-A01']
                              if f['data'].get('kind') == 'inspection_report')
                item = next(i for i in raw['message']['content']['data']['items'] if i['parent_asin'] == 'PUBLIC-A01')
                item['reasons'][1]['citations'] = [report]

        transport = BatchTransport(mutate=wrong_reason, after=rate_limit)
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            limits={'model_calls': 13}, binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'released')
        self.assertEqual(result['budget']['usage']['model_calls'], 13)
        self.assertEqual(result['budget']['usage']['retries'], 2)
        self.assertEqual(result['feedback_round'], 1)
        self.assertEqual(len(result['drafts']), 2)
        self.assertTrue(result['revisions'])
        self.assertEqual([m['response']['status'] for m in result['messages'][:2]], ['rate_limit', 'rate_limit'])
        self.assertEqual(result['budget']['usage']['logical_tools'], 136)
        self.assertEqual(result['budget']['usage']['physical_tools'], 8)

    def test_normal_work_cannot_spend_the_final_model_slot(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])
        transport = BatchTransport()
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            limits={'model_calls': 8}, binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'incomplete_budget')
        self.assertEqual(result['budget']['usage']['model_calls'], 7)
        self.assertEqual(result['budget']['final_reserve']['model_calls'], 1)
        self.assertIsNone(result['publication_path'])
        self.assertTrue(Path(result['audit_path']).is_file())
        self.assertFalse(any(r['output_kind'] == 'final_submit' for r in transport.requests))
        self.assertTrue(any(r['status'] == 'budget_exhausted' for r in result['budget']['receipts']))

    def test_empty_batch_binding_keeps_the_existing_six_role_empty_proof(self):
        self.fixture.quality([])
        result = self.fixture.make('M', model=ScriptedTransport().adapter(), arm='quality', prefix=64,
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'valid_empty')
        self.assertEqual(len(result['roles_completed']), 6)
        self.assertEqual(result['budget']['usage']['physical_tools'], 0)
        self.assertEqual(result['budget']['usage']['model_calls'], 8)
        self.assertEqual(result['components']['mean_quality']['mean_quality']['denominator'], 0)
        self.assertTrue(Path(result['audit_path']).is_file())

    def test_batch_tool_mapping_requires_the_explicit_new_model_request_version(self):
        requests = []

        def sender(request):
            requests.append(copy.deepcopy(request))
            return {'request_id': request['request_id'], 'model_id': None, 'finish_reason': 'tool_calls',
                'message': {'role': 'assistant', 'content': None, 'tool_requests': [{
                    'call_id': 'PUBLIC-BATCH-CALL', 'name': 'acquire_batch', 'arguments': {
                        'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A',
                        'candidate_limit': 32, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 32,
                        'max_read_batches': 32, 'stop_policy': 'fixed_prefix'}}]},
                'usage': {'input_tokens': 5, 'output_tokens': 7, 'cost_microusd': 0}, 'error': None}

        adapter = ModelAdapter(sender, capability_binding={
            'execution_kind': 'scripted_public', 'model_id': None, 'provenance': 'scripted'})
        request = {'schema_version': 'rsm-model-request-0.2.0', 'execution_kind': 'scripted_public',
            'request_id': 'PUBLIC-REQUEST', 'attempt_id': 'PUBLIC-ATTEMPT', 'run_id': 'PUBLIC-RUN',
            'session_id': 'PUBLIC-SESSION', 'role': '生命周期追溯', 'reply_to': None, 'model_id': None,
            'messages': [{'role': 'user', 'content': 'public fixture'}], 'tools': [{'name': 'acquire_batch'}],
            'output_kind': 'acquire', 'max_output_tokens': 100, 'input_token_upper_bound': 100,
            'deadline_ms': 45000, 'reservation_id': 'PUBLIC-RESERVATION'}
        accepted = adapter.invoke(request)
        self.assertEqual(accepted['status'], 'ok')
        self.assertEqual(accepted['message']['tool_requests'][0]['name'], 'acquire_batch')
        rejected = adapter.invoke({**request, 'schema_version': 'rsm-model-request-0.1.0'})
        self.assertEqual(rejected['status'], 'invalid_request')
        self.assertFalse(rejected['attempted'])
        self.assertEqual(len(requests), 1)

    def test_unknown_usage_after_batch_keeps_hold_and_failed_quality_anchor(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])

        def unknown(request, raw, context):
            if request['output_kind'] == 'acquire' and raw['message']['content'] is not None:
                raw['usage']['output_tokens'] = None

        transport = BatchTransport(after=unknown)
        result = self.fixture.make('M', model=transport.adapter(), arm='quality', prefix=4,
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'failed_model')
        self.assertEqual(result['budget']['usage']['model_calls'], 5)
        self.assertEqual(result['budget']['usage']['retries'], 0)
        self.assertFalse(result['budget']['usage_exact'])
        self.assertGreater(result['budget']['held']['output_tokens'], 0)
        self.assertEqual(result['cursor'], 4)
        self.assertEqual(result['budget']['usage']['physical_tools'], 8)
        self.assertIsNone(result['publication_path'])
        self.assertEqual([v['status'] for v in result['components'].values()], ['anchor_failed'] * 3)

    def test_tool_budget_exhaustion_inside_batch_is_sealed_without_reading_more(self):
        self.fixture.quality(['PUBLIC-A01', 'PUBLIC-A02', 'PUBLIC-A03', 'PUBLIC-A04'])
        result = self.fixture.make('M', model=BatchTransport().adapter(), arm='quality', prefix=4,
            limits={'physical_tools': 1}, binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual(result['terminal'], 'incomplete_budget')
        self.assertEqual(result['cursor'], 0)
        self.assertEqual(result['budget']['usage']['physical_tools'], 1)
        self.assertEqual(result['budget']['usage']['model_calls'], 4)
        self.assertEqual(result['batches'][0]['steps'][-1]['status'], 'budget_exhausted')
        self.assertIsNotNone(result['batches'][0]['steps'][-1]['root_reservation_id'])
        self.assertTrue(Path(result['audit_path']).is_file())
        self.assertIsNone(result['publication_path'])

    def test_batch_scope_and_authority_cannot_be_overridden_by_model_arguments(self):
        plan = {'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A',
            'candidate_limit': 1, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 1,
            'max_read_batches': 1, 'stop_policy': 'first_10_qualified'}
        for changes in ({'candidate_limit': 33}, {'candidate_limit': True}, {'start_candidate': 'OTHER'},
                        {'claim_ids': ['c1']}, {'stop_policy': 'fixed_prefix'}, {'principal_id': 'OTHER'}):
            with self.subTest(changes=changes):
                run = self.fixture.make('M', model=ScriptedTransport().adapter(),
                    binding_changes={'orchestration': 'batch32-0.1.0'})
                result = run.evidence.dispatch('acquire_batch', {**plan, **changes}, actor_role='生命周期追溯')
                self.assertEqual(result['status'], 'access_denied')
                self.assertEqual(result['receipt']['root_usage_after']['physical_tools'], 0)
                self.assertEqual(result['receipt']['root_usage_after']['candidates'], 0)

    def test_unfinished_registration_page_does_not_read_or_advance_to_next_candidate(self):
        self.fixture.candidates(['PUBLIC-A01', 'PUBLIC-A02'])
        report = next(r for r in self.fixture.facts.rows['materials.jsonl']
                      if r['parent_asin'] == 'PUBLIC-A01' and r['kind'] == 'inspection_report')
        for i in range(23):
            self.fixture.facts.add('materials.jsonl', {**copy.deepcopy(report), 'evidence_id': 'EXTRA-%02d' % i})
        self.fixture.seal()
        run = self.fixture.make('M', model=ScriptedTransport().adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'})
        result = run.evidence.dispatch('acquire_batch', {
            'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': 'PUBLIC-A01',
            'candidate_limit': 2, 'claim_ids': ['c1', 'c2'], 'max_list_pages': 1,
            'max_read_batches': 32, 'stop_policy': 'first_10_qualified'}, actor_role='生命周期追溯')
        self.assertEqual(result['status'], 'batch_plan_exhausted')
        self.assertEqual(result['processed'], [])
        self.assertEqual(result['assessments'], {})
        self.assertEqual(result['usage_after']['physical_tools'], 1)
        self.assertEqual([s['operation'] for s in result['steps']], ['begin_batch', 'list_evidence'])

    def test_manager_dispatch_requires_an_integer_candidate_bound(self):
        def wrong_type(request, raw, context):
            if request['output_kind'] == 'dispatch':
                raw['message']['content']['data']['candidate_limit'] = 32.0

        result = self.fixture.make('M', model=BatchTransport(after=wrong_type).adapter(),
            binding_changes={'orchestration': 'batch32-0.1.0'}).run()
        self.assertEqual((result['terminal'], result['reason']), ('failed_protocol', 'invalid_dispatch'))
        self.assertEqual(result['budget']['usage']['physical_tools'], 0)
