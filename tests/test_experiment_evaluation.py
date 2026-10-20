"""Public handwritten evaluation examples; never real experiment results."""
import copy
import hashlib
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


def example(scene='V00', method='M', user='PUBLIC-U1'):
    task = {'task_key': user + ':' + scene + ':' + method, 'root_task_id': user,
        'view_id': 'opaque-' + scene, 'scene': scene, 'method': method, 'repeat': 1,
        'material_version': 'PUBLIC-SIM-v1', 'snapshot_id': 'PUBLIC-snapshot-' + scene,
        'request_profile_id': 'R1_AND_R5_SIM_Q1_ON_SALE', 'principal_id': 'PUBLIC-verifier',
        'verify_at_ms': 1000, 'C': ['a', 'b', 'c', 'd'], 'batches': ['ba', 'bb', 'bc', 'bd'],
        'H_sha256': '1' * 64, 'base_scores_sha256': '2' * 64, 'fixed_S': ['a']}
    binding = {k: copy.deepcopy(task[k]) for k in ('root_task_id', 'view_id', 'material_version',
        'snapshot_id', 'request_profile_id', 'principal_id', 'verify_at_ms', 'C', 'batches',
        'H_sha256', 'base_scores_sha256')}
    reference = {'binding': binding, 'target': 'b',
        'states': {'a': 'Supported', 'b': 'Supported', 'c': 'Refuted', 'd': 'Pending'},
        'source_ref': {'path': 'PUBLIC-handwritten-reference', 'sha256': '3' * 64, 'line': 1}}
    execution = {'task_key': task['task_key'], 'binding': copy.deepcopy(binding),
        'started': True, 'terminal': 'released', 'delivered': ['a', 'b'], 'G': ['a', 'b'],
        'gate_passed': True, 'publication_verified': True, 'complete_C': False,
        'assessments': {'a': 'Supported', 'b': 'Supported'},
        'usage': {'basis': 'public_synthetic', 'model_calls': 2, 'input_tokens': 12,
                  'output_tokens': 3, 'logical_tools': 5, 'physical_tools': 2, 'retries': 1,
                  'cost_microusd': None}}
    if method == 'R':
        execution['usage'].update(model_calls=0, input_tokens=0, output_tokens=0, retries=0)
    return task, execution, reference


def public_wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def public_digest(value):
    return hashlib.sha256(public_wire(value)).hexdigest()


def quality_example(scene='Q1', user='PUBLIC-U1'):
    task, execution, reference = example(scene=scene, user=user)
    task['base_scores'] = [.9, .6, 1, 0]
    task['base_scores_sha256'] = public_digest(list(zip(task['C'], task['base_scores'])))
    for binding in (execution['binding'], reference['binding']):
        binding['base_scores_sha256'] = task['base_scores_sha256']
    reference['states'] = dict.fromkeys(task['C'], 'Supported')
    rows = [dict(parent_asin=p, z=1, m=m, q=q, C={'numerator': 1, 'denominator': 1},
                 A={'numerator': 2, 'denominator': 2}, T=t,
                 citations={'retail_stock': {'evidence_id': 'retail-' + p, 'pointer': '/facts/stock_units'}})
            for p, m, q, t in (('a', .75, .6, .2), ('b', 1, .9, .8), ('c', 0, .6, .2), ('d', 0, .6, .2))]
    # Handwritten normal-v1 objects/registrations; no production generator or reference oracle.
    stages = ('harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail')
    kinds = ('inspection_sample', 'inspection_report', 'retail_status', 'transport_dispatch', 'transport_receipt')
    policy = {'policy_id': 'PUBLIC-policy', 'registrar_id': 'PUBLIC-registry', 'read_principal_id': task['principal_id'],
        'issuers': [{'issuer_id': 'PUBLIC-issuer', 'may_create_batch': True,
                     'event_stages': list(stages), 'material_kinds': list(kinds)}],
        'read_scope': {'scope': 'current_snapshot_only', 'target_kinds': ['batch','event','material'], 'material_kinds': list(kinds)}}
    candidates, scope_hashes = {}, {}
    for row in rows:
        parent, batch = row['parent_asin'], 'b'+row['parent_asin']
        common = {'source': 'SIM', 'parent_asin': parent, 'sim_batch_id': batch, 'version': 1}
        objects = [{**common, 'schema_version': 'sim-batch-1.0.0', 'issuer_id': 'PUBLIC-issuer', 'created_at_ms': 1}]
        for index, stage in enumerate(stages):
            objects.append({**common, 'schema_version': 'sim-event-1.0.0', 'event_id': parent+'-'+stage,
                'stage': stage, 'actor_id': 'PUBLIC-issuer', 'event_start_ms': 10+20*index,
                'event_end_ms': 11+20*index,
                'predecessor_event_ids': [parent+'-'+stages[index-1]] if index else []})
        sample = 'sample-'+parent
        for kind, stage, issued, facts in (
            ('inspection_sample', 'inspection', 72, {'sample_id': sample, 'sampled_at_ms': 70}),
            ('inspection_report', 'inspection', 76, {'sample_id': sample, 'test_scope': ['SIM-Q1'],
                'test_started_at_ms': 73, 'test_completed_at_ms': 74, 'conclusion': 'pass'}),
            ('retail_status', 'retail', 112, {'stock_units': int(row['m']*100), 'location_id': 'shop',
                'unit': 'SIM_PACK', 'status': 'on_sale', 'observed_at_ms': 111}),
            ('transport_dispatch', 'transport', 92, {'transport_segment_id': 'segment-'+parent,
                'from_location_id': 'warehouse', 'to_location_id': 'shop', 'quantity_units': 100,
                'unit': 'SIM_PACK', 'departed_at_ms': 90}),
            ('transport_receipt', 'transport', 102, {'transport_segment_id': 'segment-'+parent,
                'from_location_id': 'warehouse', 'to_location_id': 'shop', 'quantity_units': 100,
                'unit': 'SIM_PACK', 'arrived_at_ms': 100, 'handover_status': 'accepted'})):
            material = {**common, 'schema_version': 'sim-material-1.0.0', 'kind': kind,
                'evidence_id': ('retail-' if kind == 'retail_status' else kind+'-')+parent,
                'issuer_id': 'PUBLIC-issuer', 'event_id': parent+'-'+stage, 'issued_at_ms': issued,
                'temporal_mode': 'current_assertion' if kind == 'retail_status' else 'historical_fact', 'facts': facts}
            if kind == 'retail_status':
                material.update(valid_from_ms=0, valid_to_ms=5000 if parent == 'b' else 1250)
            objects.append(material)
        regs, originals = [], {}
        for item in objects:
            typ = item['schema_version'].split('-')[1]
            identity = item[{'batch': 'sim_batch_id', 'event': 'event_id', 'material': 'evidence_id'}[typ]]
            reg = {'target_kind': typ, 'target_id': identity, 'version': 1, 'parent_asin': parent,
                'sim_batch_id': batch, 'event_id': item.get('event_id'), 'issuer_id': 'PUBLIC-issuer',
                'source': 'SIM', 'receipt_status': 'accepted', 'registrar_id': 'PUBLIC-registry',
                'registry_backend': 'local_sim_registry', 'registered_at_ms': item.get('issued_at_ms', item.get('event_end_ms', 1))+1,
                'content_sha256': public_digest(item)}
            regs.append(reg)
            originals[identity] = {'raw_utf8': public_wire(item).decode(), 'registration': reg}
        scope_hashes[parent] = public_digest(regs)
        candidates[parent] = {'enumeration_complete': True, 'registrations': [{'record': r} for r in regs], 'originals': originals}
    rules = {'attribute':'retail_stock','source':'experiment_design','weight':1,'stock_scale':100,
        'C_slots':['retail_status'],'A_checks':['same_parent_batch','same_location_unit'],
        'main_alpha':.5,'main_beta':[.25,.5,.25],'alpha_grid':[.25,.5,.75],
        'beta_T_grid':[.25,.5,.75],'score_decimals':12}
    policy_raw = public_wire(policy)+b'\n'
    snapshot = {'schema_version': 'quality-snapshot-0.1.0', 'source': 'SIM', 'protocol_version': 'quality-preference-protocol-0.1.0',
        'verify_at_ms': 1000, 'sealed_at_ms': 900 if scene == 'Q1' else 901, 'policy_id': 'PUBLIC-policy',
        'read_principal_id': task['principal_id'], 'rules': rules, 'contract_sha256': public_digest(rules),
        'scope_sha256': scope_hashes, 'components': {'policy.json': {'sha256': hashlib.sha256(policy_raw).hexdigest()},
            'actions.jsonl': {'records': 0, 'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()}}}
    snapshot['snapshot_id'] = 'qf_'+hashlib.sha256(b'Thesis-quality-fusion:snapshot\0'+public_wire(snapshot)).hexdigest()
    task['snapshot_id'] = snapshot['snapshot_id']
    task['fusion'] = {'schema_version': 'fusion-binding-0.1.0', 'task_id': user, 'C': task['C'],
        'C_sha256': public_digest(task['C']), 'H_sha256': task['H_sha256'], 'base_scores': task['base_scores'],
        'base_score_version': 'public-worked-example', 'base_score_sha256': task['base_scores_sha256'],
        'snapshot_id': task['snapshot_id'], 'verify_at_ms': 1000, 'principal_id': task['principal_id'],
        'contract_sha256': snapshot['contract_sha256'], 'K': 10, 'alpha': .5, 'beta': [.25,.5,.25], 'mode': 'full',
        'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
    for binding in (execution['binding'], reference['binding']):
        binding['snapshot_id'] = task['snapshot_id']
    acquired = {'binding': {'root_task_id': user, 'snapshot_id': task['snapshot_id'],
        'principal_id': task['principal_id'], 'verify_at_ms': 1000},
        'candidate_binding': {'C': task['C'], 'base_scores': task['base_scores']}, 'candidates': candidates,
        'context': {'snapshot': {'raw_utf8': public_wire(snapshot).decode()}, 'policy': {'raw_utf8': policy_raw.decode()},
                    'actions_scope': {'raw_utf8': ''}},
        'assessments': {p: {'eligible': True, 'evidence_state': 'Supported', 'advance_allowed': True} for p in ('a', 'b')}}
    anchor = {'run_id': task['task_key'], 'root_task_id': user, 'snapshot_id': task['snapshot_id'],
        'A_sha256': public_digest(acquired), 'G': ['a', 'b'], 'C_sha256': public_digest(task['C']),
        'base_score_sha256': task['base_scores_sha256'], 'H_sha256': task['H_sha256'],
        'repeat_id': 1, 'cursor': 4, 'stop_reason': 'fixed_candidate_prefix', 'terminal': 'released',
        'fusion_sha256': public_digest(task['fusion'])}
    execution.update(delivered=['b', 'a'], acquired=acquired, cursor=4, stop_reason='fixed_candidate_prefix')
    execution['components'] = {mode: {'anchor': copy.deepcopy(anchor), 'anchor_sha256': public_digest(anchor),
        'status': 'computed', 'G': ['a', 'b'], 'candidates': copy.deepcopy(rows),
        'order': order, 'topK': order, 'mean_quality': {'value': .675, 'denominator': 4}}
        for mode, order in (('full', ['b', 'a']), ('no_quality', ['a', 'b']), ('mean_quality', ['a', 'b']))}
    return task, execution, reference


def public_plan(users=('PUBLIC-U1', 'PUBLIC-U2')):
    main = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12')
    scenes = [f'V{i:02d}' for i in range(16)] + ['Q1', 'Q2']
    observations = []
    for user in users:
        for scene in scenes:
            for method in (('M',) if scene.startswith('Q') else ('R', 'S', 'M')):
                task, execution, reference = quality_example(scene, user) if scene.startswith('Q') else example(scene, method, user)
                if scene.startswith('V'):
                    reference['states'] = dict.fromkeys(task['C'], 'Supported')
                    execution.update(G=task['C'][:], assessments=dict.fromkeys(task['C'], 'Supported'))
                    execution['delivered'] = (['b'] if method == 'M' else ['a', 'c', 'b'] if method == 'S'
                                              else ['a', 'c', 'd']) if user == 'PUBLIC-U1' else (
                                              ['a', 'c', 'b'] if method == 'R' else ['a', 'c', 'd'])
                    if scene not in main:
                        execution['delivered'] = ['b'] if method == 'R' else ['a', 'c', 'd']
                if user == 'PUBLIC-U2' and method == 'M':
                    execution['terminal'] = 'failed_model'
                observations.append({'task': task, 'execution': execution, 'reference': reference})
    plan = {'source_scope': 'public_fixture', 'plan_id': 'PUBLIC-HANDWRITTEN-v1', 'users': list(users),
        'scenes': scenes, 'tasks': [r['task'] for r in observations],
        'applicability': {u: dict.fromkeys(scenes, True) for u in users},
        'cohorts': {'U8': list(users), 'UQ': list(users)},
        'model_binding': dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget'))}
    return plan, observations


class GuardBoundary(unittest.TestCase):
    def test_guard_binds_evaluation_package(self):
        self.assertEqual(os.environ.get('THESIS_EVALUATION_PACKAGE'), str(
            PROJECT / '.scratch/test100-evaluation-20261020/package.json'))

    def test_guard_denies_real_data_outside_writes_and_network(self):
        with self.assertRaisesRegex(OSError, 'evaluation_real_data_read_forbidden'):
            (PROJECT/'data/recommendation-runtime-audit/ticket12-100x18/plan/plan.json').read_bytes()
        with self.assertRaisesRegex(OSError, 'write_outside_outputs'):
            (PROJECT/'.tmp/evaluation-unauthorized.txt').write_text('must not be written')
        with socket.socket() as channel:
            with self.assertRaisesRegex(OSError, 'network_forbidden'):
                channel.connect(('127.0.0.1', 9))

    def test_existing_root_budget_assertions_with_scoped_fixture_root(self):
        from tests import test_root_budget as legacy
        previous = legacy.PROJECT
        try:
            legacy.PROJECT = PROJECT/'.tmp/recommendation-runtime/eval100-scoped-legacy'
            (legacy.PROJECT/'.tmp/recommendation-runtime').mkdir(parents=True, exist_ok=True)
            suite = unittest.TestSuite(legacy.RootBudgetTests(name) for name in (
                'test_unknown_tokens_keep_their_hold_and_block_new_work',
                'test_tool_and_model_retries_use_the_same_two_attempt_allowance'))
            result = unittest.TestResult()
            suite.run(result)
            self.assertEqual(result.testsRun, 2)
            self.assertTrue(result.wasSuccessful(), repr(result.errors + result.failures))
        finally:
            legacy.PROJECT = previous


class TaskScores(unittest.TestCase):
    def test_public_hand_calculated_joint_and_preference_score(self):
        from experiment_evaluation import score_task
        result = score_task(*example())
        self.assertEqual(result['status'], 'scored')
        self.assertAlmostEqual(result['metrics']['10']['SJ_NDCG'], 0.6309297535714575)
        self.assertEqual(result['metrics']['1']['HR'], 0)
        self.assertEqual(result['metrics']['10']['HR'], 1)

    def test_whole_list_gate_cannot_hide_invalid_tail(self):
        from experiment_evaluation import score_task
        task, execution, reference = example()
        execution['delivered'] = ['c', 'b', 'a']
        result = score_task(task, execution, reference)
        self.assertAlmostEqual(result['metrics']['10']['NDCG_P'], 0.6309297535714575)
        self.assertAlmostEqual(result['metrics']['10']['EG_NDCG'], 0.6309297535714575)
        self.assertEqual(result['metrics']['10']['SJ_NDCG'], 0)
        execution['delivered'] = ['b', 'a', 'c']
        self.assertEqual(score_task(task, execution, reference)['metrics']['1']['SJ_NDCG'], 0)
        for illegal in (['b', 'b'], ['b', 'OUTSIDE']):
            execution['delivered'] = illegal
            self.assertEqual(score_task(task, execution, reference)['metrics']['10']['NDCG_P'], 0)

    def test_not_started_failure_reference_na_and_missing_record_are_distinct(self):
        from experiment_evaluation import score_task
        task, execution, reference = example()
        execution.update(started=False, terminal='not_started')
        pending = score_task(task, execution, reference)
        self.assertEqual(pending['status'], 'not_started')
        self.assertIsNone(pending['metrics']['10']['SJ_NDCG'])
        execution.update(started=True, terminal='incomplete_deadline')
        failed = score_task(task, execution, reference)
        self.assertEqual(failed['execution_state'], 'failed')
        self.assertEqual(failed['metrics']['10']['SJ_NDCG'], 0)
        reference['states']['b'] = 'Refuted'
        na = score_task(task, execution, reference)
        self.assertEqual((na['na_reason'], na['execution_state']), ('Refuted', 'failed'))
        self.assertIsNone(na['metrics']['10']['SJ_NDCG'])
        self.assertEqual(na['metrics']['10']['NDCG_P'], 0)
        missing = score_task(task, None, reference)
        self.assertEqual(missing['status'], 'pipeline_error')
        self.assertEqual(missing['error'], 'missing_execution_record')

    def test_unresolved_execution_keeps_known_usage_without_a_score(self):
        from experiment_evaluation import score_task
        task, execution, reference = example()
        execution.update(terminal='unresolved_attempt')
        execution['usage']['output_tokens'] = None
        result = score_task(task, execution, reference)
        self.assertIsNone(result['metrics']['10']['SJ_NDCG'])
        self.assertEqual(result['usage']['model_calls'], 2)
        self.assertEqual(result['usage']['retries'], 1)
        self.assertIsNone(result['usage']['output_tokens'])

    def test_wrong_reference_or_execution_binding_is_pipeline_error(self):
        from experiment_evaluation import score_task
        for mutation in ('snapshot', 'missing_state', 'execution_key', 'unknown_terminal'):
            task, execution, reference = example()
            if mutation == 'snapshot':
                reference['binding']['snapshot_id'] = 'OTHER'
            elif mutation == 'missing_state':
                del reference['states']['d']
            elif mutation == 'execution_key':
                execution['task_key'] = 'OTHER'
            else:
                execution['terminal'] = 'MADE-UP'
            result = score_task(task, execution, reference)
            self.assertEqual(result['status'], 'pipeline_error', mutation)
            self.assertIsNone(result['metrics']['10']['SJ_NDCG'])

    def test_empty_proof_coverage_and_unassessed_are_reported(self):
        from experiment_evaluation import score_task
        task, execution, reference = example()
        result = score_task(task, execution, reference)
        self.assertEqual(result['secondary']['qualified_coverage'], 1)
        self.assertEqual(result['secondary']['fill'], 0.2)
        self.assertEqual(result['secondary']['necessary_satisfied'], 1)
        self.assertEqual(result['confusion']['other']['Refuted']['Unassessed'], 1)
        self.assertIsNone(result['recall']['fixed_S']['Conflict'])
        reference['states'] = dict.fromkeys(task['C'], 'Refuted')
        execution.update(terminal='valid_empty', delivered=[], G=[], complete_C=True,
                         assessments=dict.fromkeys(task['C'], 'Refuted'))
        empty = score_task(task, execution, reference)
        self.assertEqual(empty['secondary']['necessary_satisfied'], 1)
        self.assertIsNone(empty['secondary']['violation_item_rate'])
        self.assertIsNone(empty['secondary']['qualified_coverage'])
        execution['complete_C'] = False
        self.assertEqual(score_task(task, execution, reference)['secondary']['necessary_satisfied'], 0)

    def test_contradictory_valid_empty_cannot_get_preference_credit(self):
        from experiment_evaluation import score_task
        task, execution, reference = example()
        execution.update(terminal='valid_empty', delivered=['b'])
        result = score_task(task, execution, reference)
        self.assertEqual(result['metrics']['10']['HR'], 0)
        self.assertEqual(result['metrics']['10']['NDCG_P'], 0)
        self.assertEqual(result['metrics']['10']['SJ_NDCG'], 0)
        self.assertEqual(result['execution_state'], 'failed')

    def test_quality_uses_actual_M_anchor_and_full_C_mean(self):
        from experiment_evaluation import score_task
        result = score_task(*quality_example())
        self.assertEqual(result['components']['full']['SJ_C'], 1)
        self.assertAlmostEqual(result['components']['no_quality']['SJ_C'], 0.6309297535714575)
        self.assertEqual(result['quality']['mean_denominator'], 4)
        self.assertAlmostEqual(result['quality']['mean_q'], .675)
        self.assertEqual(result['quality']['G'], ['a', 'b'])

    def test_quality_accepts_batch_and_event_originals_without_kind(self):
        from experiment_evaluation import score_task
        task, execution, reference = quality_example()
        originals = execution['acquired']['candidates']['a']['originals']
        self.assertNotIn('kind', json.loads(originals['ba']['raw_utf8']))
        self.assertNotIn('kind', json.loads(originals['a-harvest']['raw_utf8']))
        result = score_task(task, execution, reference)
        self.assertEqual(result['status'], 'scored', result.get('error'))
        self.assertEqual(result['quality']['mean_denominator'], 4)

    def test_quality_failure_is_shared_and_reference_cannot_supply_missing_facts(self):
        from experiment_evaluation import score_task
        task, execution, reference = quality_example()
        execution['delivered'] = ['a', 'b']
        mismatch = score_task(task, execution, reference)
        self.assertEqual([r['SJ_C'] for r in mismatch['components'].values()], [0, 0, 0])
        self.assertEqual(mismatch['execution_state'], 'failed')
        execution['terminal'] = 'failed_model'
        failed = score_task(task, execution, reference)
        self.assertEqual([r['SJ_C'] for r in failed['components'].values()], [0, 0, 0])
        task, execution, reference = quality_example()
        del execution['acquired']['candidates']['c']
        self.assertEqual(score_task(task, execution, reference)['status'], 'pipeline_error')

    def test_quality_control_metadata_cannot_change_factors_or_mean_denominator(self):
        from experiment_evaluation import score_task
        for mutation in ('mean_denominator', 'control_factor'):
            task, execution, reference = quality_example()
            if mutation == 'mean_denominator':
                execution['components']['mean_quality']['mean_quality']['denominator'] = 2
            else:
                execution['components']['no_quality']['candidates'][0]['q'] = .8
            self.assertEqual(score_task(task, execution, reference)['status'], 'pipeline_error')

    def test_component_z_cannot_remove_actual_support_from_mean(self):
        from experiment_evaluation import score_task
        task, execution, reference = quality_example()
        for component in execution['components'].values():
            candidate = next(r for r in component['candidates'] if r['parent_asin'] == 'c')
            candidate.update(z=0, q=0, m=0)
            component['mean_quality'] = {'value': .7, 'denominator': 3}
        self.assertEqual(score_task(task, execution, reference)['status'], 'pipeline_error')

    def test_quality_G_is_a_fixed_set_and_cannot_be_expanded(self):
        from experiment_evaluation import score_task
        task, execution, reference = quality_example()
        execution['G'] = ['b', 'a']
        for component in execution['components'].values():
            component['anchor']['G'] = ['b', 'a']
            component['anchor_sha256'] = public_digest(component['anchor'])
        self.assertEqual(score_task(task, execution, reference)['components']['full']['SJ_C'], 1)
        task, execution, reference = quality_example()
        execution['G'].append('c')
        self.assertEqual(score_task(task, execution, reference)['status'], 'pipeline_error')
        task, execution, reference = quality_example()
        del execution['acquired']['candidates']['c']
        for component in execution['components'].values():
            component['anchor']['A_sha256'] = public_digest(execution['acquired'])
            component['anchor_sha256'] = public_digest(component['anchor'])
        self.assertEqual(score_task(task, execution, reference)['error'], 'quality_unacquired_fact')


class Summaries(unittest.TestCase):
    def test_user_paired_means_keep_failures_and_fixed_scene_weights(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertEqual(result['comparisons']['C1']['n'], 2)
        self.assertAlmostEqual(result['comparisons']['C1']['estimate'], .25)
        self.assertAlmostEqual(result['comparisons']['C2']['estimate'], .25)
        self.assertAlmostEqual(result['comparisons']['C3']['estimate'], .18453512321427125)
        self.assertEqual(result['sample_sufficiency'], 'not_claimed')
        self.assertNotIn('planned_n_not_met', json.dumps(result))

    def test_missing_and_unstarted_tasks_keep_fixed_cohort_and_null_estimate(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        scores = [score_task(**r) for r in observations]
        missing = [r for r in scores if r['task_key'] != 'PUBLIC-U1:V00:M']
        result = summarize(plan, missing)
        self.assertEqual((result['status'], result['comparisons']['C1']['n']), ('incomplete', 2))
        self.assertIsNone(result['comparisons']['C1']['estimate'])
        self.assertEqual(result['counts']['missing_records'], 1)
        self.assertEqual(len(result['task_scores']), 100)
        observations[0]['execution'].update(started=False, terminal='not_started')
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertIsNone(result['comparisons']['C2']['estimate'])
        self.assertEqual(result['counts']['not_started'], 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            summarize(plan, scores + scores[:1])

    def test_F2_paired_intervals_use_fixed_seeds_and_shared_indices(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertEqual(result['comparisons']['C1']['interval'], [0, .5])
        self.assertEqual(result['comparisons']['C2']['interval'], [-.5, 1])
        self.assertEqual(result['resampling']['U8']['seed'], 20261016)
        self.assertEqual(result['resampling']['UQ']['seed'], 20261017)
        self.assertEqual(result['resampling']['U8']['B'], 50000)
        self.assertEqual(result['comparisons']['C1']['index_sha256'], result['comparisons']['C2']['index_sha256'])
        self.assertNotEqual(result['resampling']['U8']['index_sha256'], result['resampling']['UQ']['index_sha256'])
        self.assertEqual(result['resampling']['U8']['quantile'], 'type7')

    def test_small_or_degenerate_intervals_do_not_claim_sufficiency(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan(('PUBLIC-U1',))
        small = summarize(plan, [score_task(**r) for r in observations])
        self.assertIsNone(small['comparisons']['C1']['interval'])
        self.assertEqual(small['family_status'], 'not_fully_estimated')
        plan, observations = public_plan()
        for row in observations:
            if row['task']['root_task_id'] == 'PUBLIC-U2' and row['task']['scene'] in ('V00','V01','V03','V05','V06','V07','V09','V12'):
                method = row['task']['method']
                row['execution'].update(terminal='released', delivered=['b'] if method == 'M' else ['a','c','b'] if method == 'S' else ['a','c','d'])
        degenerate = summarize(plan, [score_task(**r) for r in observations])
        self.assertEqual(degenerate['comparisons']['C1']['interval'], [.5, .5])
        self.assertTrue(degenerate['comparisons']['C1']['degenerate'])
        self.assertEqual(degenerate['sample_sufficiency'], 'not_claimed')

    def test_scene_groups_and_usage_count_actual_tasks_once_with_unknowns(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        next(r for r in observations if r['task']['task_key'] == 'PUBLIC-U2:Q1:M')['execution']['usage']['input_tokens'] = None
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertEqual(len(result['scenes']), 50)
        extra = next(r for r in result['scenes'] if (r['scene'], r['method']) == ('V02', 'M'))
        self.assertEqual((extra['group'], extra['planned'], extra['SJ_NDCG']), ('additional8', 2, 0))
        quality = next(r for r in result['scenes'] if r['scene'] == 'Q1')
        self.assertEqual(quality['group'], 'quality')
        self.assertEqual(quality['components']['full'], .5)
        usage = result['usage']['public_synthetic']
        self.assertEqual(usage['model_calls']['total'], 136)
        self.assertIsNone(usage['input_tokens']['total'])
        self.assertEqual((usage['input_tokens']['known_subtotal'], usage['input_tokens']['unknown_tasks']), (804, 1))
        self.assertIsNone(result['cost']['total_microusd'])
        self.assertEqual(result['counts']['planned_tasks'], 100)

    def test_reference_NA_fixes_cohort_and_supplemental_weight_mass(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        plan['applicability']['PUBLIC-U2']['V01'] = False
        plan['cohorts']['U8'] = ['PUBLIC-U1']
        for row in observations:
            if row['task']['root_task_id'] == 'PUBLIC-U2' and row['task']['scene'] == 'V01':
                row['reference']['states']['b'] = 'Pending'
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertEqual(result['comparisons']['C1']['n'], 1)
        self.assertEqual(result['comparisons']['C3']['n'], 2)
        self.assertAlmostEqual(result['comparisons']['C1']['estimate'], .5)
        user = next(r for r in result['users'] if r['root_task_id'] == 'PUBLIC-U2')
        self.assertEqual(user['conditional_weight_mass'], .875)
        self.assertEqual(user['conditional_original8']['R'], .5)
        self.assertEqual(result['counts']['reference_NA'], 3)

    def test_missing_usage_has_no_complete_total_for_known_basis(self):
        from experiment_evaluation import score_task, summarize
        plan, observations = public_plan()
        next(r for r in observations if r['task']['task_key'] == 'PUBLIC-U1:Q1:M')['execution']['usage'] = None
        result = summarize(plan, [score_task(**r) for r in observations])
        self.assertIsNone(result['usage']['public_synthetic']['model_calls']['total'])
        self.assertEqual(result['usage_unattributed_tasks'], 1)
        self.assertEqual(result['usage']['public_synthetic']['model_calls']['known_subtotal'], 134)


class PublicCLI(unittest.TestCase):
    def setUp(self):
        parent = PROJECT / '.tmp/experiment-evaluation'
        parent.mkdir(exist_ok=True)
        retain = bool(os.environ.get('THESIS_EVALUATION_RETAIN'))
        self.temp = tempfile.TemporaryDirectory(prefix='public-cli-', dir=parent, delete=not retain)
        self.root = Path(self.temp.name)
        if not retain:
            self.addCleanup(self.temp.cleanup)

    def fixture(self):
        plan, observations = public_plan()
        refs = {}
        for name, data in (('plan', plan), ('observations', observations)):
            path = self.root / (name + '.json')
            raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            path.write_bytes(raw)
            refs[name] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        manifest = {'schema_version': 'public-evaluation-fixture-0.1.0', 'source_scope': 'public_fixture', **refs}
        path = self.root / 'fixture.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return path

    def invoke(self, manifest, output=None):
        return subprocess.run([sys.executable, '-B', str(PROJECT/'.scratch/ticket12-budget-20261018/diagnostics/run_check.py'),
            '--storage-child', str(PROJECT/'experiment_evaluation.py'), '--fixture-manifest', str(manifest),
            '--output-root', str(output or self.root/'output')], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')

    def test_public_cli_writes_bound_fixture_outputs(self):
        result = self.invoke(self.fixture())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response['status'], 'public_fixture_complete')
        self.assertTrue(response['fixture_only'])
        self.assertEqual(response['real_evaluations'], 0)
        manifest = json.loads((self.root/'output/manifest.json').read_bytes())
        self.assertEqual(set(manifest['components']), {'task-scores.jsonl','user-pairs.jsonl','scene-summary.jsonl','summary.json'})
        for name, ref in manifest['components'].items():
            raw = (self.root/'output'/name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
        summary = json.loads((self.root/'output/summary.json').read_bytes())
        self.assertAlmostEqual(summary['comparisons']['C1']['estimate'], .25)
        before = (self.root/'output/summary.json').read_bytes()
        again = self.invoke(self.root/'fixture.json')
        self.assertEqual(again.returncode, 2)
        self.assertEqual((self.root/'output/summary.json').read_bytes(), before)

    def test_cli_publishes_incomplete_status_for_missing_execution(self):
        path = self.fixture()
        manifest = json.loads(path.read_bytes())
        observations = json.loads((self.root/'observations.json').read_bytes())
        observations[0]['execution'] = None
        raw = json.dumps(observations).encode()
        (self.root/'observations.json').write_bytes(raw)
        manifest['observations'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        path.write_text(json.dumps(manifest), encoding='utf-8')
        result = self.invoke(path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'public_fixture_incomplete', result.stdout)
        summary = json.loads((self.root/'output/summary.json').read_bytes())
        self.assertIsNone(summary['comparisons']['C2']['estimate'])

    def test_cli_rejects_real_scope_damaged_binding_and_outside_path(self):
        for mutation in ('scope', 'digest', 'duplicate', 'outside'):
            path = self.fixture()
            manifest = json.loads(path.read_bytes())
            output = self.root/'output'
            if mutation == 'scope':
                manifest['source_scope'] = 'real_test100'
            elif mutation == 'digest':
                manifest['plan']['sha256'] = '0'*64
            elif mutation == 'duplicate':
                observations = json.loads((self.root/'observations.json').read_bytes())
                raw = json.dumps(observations + observations[:1]).encode()
                (self.root/'observations.json').write_bytes(raw)
                manifest['observations'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            else:
                output = PROJECT/'.tmp/not-public-evaluation'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            result = self.invoke(path, output)
            self.assertEqual(result.returncode, 2, mutation)
            self.assertEqual(json.loads(result.stdout)['status'], 'public_fixture_failed')
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
