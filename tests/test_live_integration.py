"""Handwritten PUBLIC integration evidence; real sources are assembly-only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.runtime_fixtures import RuntimeFixture

PROJECT = Path(__file__).resolve().parents[1]


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(wire(value)).hexdigest()


def store(path, value):
    raw = wire(value) + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def store_lines(path, rows):
    raw = b''.join(wire(row) + b'\n' for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_ref(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class LiveIntegration(unittest.TestCase):
    def setUp(self):
        parent = PROJECT / '.tmp/recommendation-runtime/liveA'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=self._testMethodName + '-', dir=parent, delete=False)
        self.root = Path(self.temp.name)
        self.fixture = RuntimeFixture(self.root)
        self.fixture.history = [{'parent_asin': 'PUBLIC-HISTORY', 'review_text': 'earlier rice', 'rating': 5}]
        self.root_id, self.view_id = 'PUBLIC-ROOT', 'PUBLIC-VIEW'
        self.scene = {'label': 'V00', 'view_id': self.view_id, 'arm': 'necessary',
            'snapshot_id': self.fixture.facts.snapshot['snapshot_id'], 'snapshot': self.fixture.facts.snapshot_ref}
        self.task = {'task_key': 'PUBLIC-TASK', 'binding_id': 'PUBLIC-BINDING', 'method': 'R', 'repeat': 1, 'uses_model': False}
        self.plan = self.root / 'plan'
        self.record = {'fixture': True, 'run_id': 'PUBLIC-ASSEMBLED-RUN',
            'limits': dict.fromkeys(('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'), 0) |
                {'candidates': 100, 'logical_tools': 1000, 'physical_tools': 1000, 'retries': 2, 'elapsed_ms': 600000},
            'final_reserve': dict.fromkeys(('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd',
                'candidates', 'physical_tools', 'retries'), 0) | {'logical_tools': 1, 'elapsed_ms': 1000}}
        self.write_plan()

    def write_plan(self, scope='public_fixture'):
        self.safe_root = {'root_task_id': self.root_id, 'history': self.fixture.history,
            'H_sha256': sha(self.fixture.history), 'C_sha256': sha(self.fixture.parents),
            'base_scores_sha256': sha(list(zip(self.fixture.parents, self.fixture.scores))),
            'score_version': 'PUBLIC-SCORE'}
        self.candidates = {'root_task_id': self.root_id, 'C': self.fixture.parents,
            'b': self.fixture.scores, 'batches': self.fixture.batches, 'background_statistics': [{}]}
        self.view = {'root_task_id': self.root_id, **self.scene, 'material_version': 'PUBLIC-MATERIAL-1',
            'principal_id': 'SIM-VERIFIER', 'verify_at_ms': 1000, 'request_profile_id': 'PUBLIC-R1-R5',
            'request': {'design_text': 'PUBLIC R1 AND R5', 'necessary_clauses': [{'clause_id': 'c1'}, {'clause_id': 'c2'}]},
            'C_sha256': self.safe_root['C_sha256'], 'H_sha256': self.safe_root['H_sha256'],
            'base_scores_sha256': self.safe_root['base_scores_sha256'], 'K': 10}
        root_ref = store(self.root / 'sources/roots.jsonl', self.safe_root) | {'offset': 0, 'line': 1}
        candidate_ref = store(self.root / 'sources/candidates.jsonl', self.candidates) | {'offset': 0, 'line': 1}
        view_ref = store(self.root / 'sources/views.jsonl', self.view) | {'offset': 0, 'line': 1}
        catalog_ref = store(self.root / 'sources/catalog.jsonl', {'parent_asin': 'PUBLIC-A', 'title': 'rice', 'crop': 'rice'})
        map_ref = store(self.root / 'sources/map.jsonl', {'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A'})
        rows = {'tasks.jsonl': self.task, 'root-references.jsonl': {'root_task_id': self.root_id,
            'root_ref': root_ref, 'candidate_ref': candidate_ref, **{k: self.safe_root[k] for k in (
                'C_sha256', 'H_sha256', 'base_scores_sha256')}}, 'scenes.jsonl': self.scene,
            'user-scenarios.jsonl': {'binding_id': 'PUBLIC-BINDING', 'root_task_id': self.root_id,
                'view_id': self.view_id, 'existing_binding_ref': view_ref},
            'sample-users.jsonl': {'root_task_id': self.root_id}}
        components = {name: {k: v for k, v in store(self.plan / name, value).items() if k != 'path'}
                      for name, value in rows.items()}
        self.manifest = {'schema_version': 'ticket12-test100-on-demand-0.1.0', 'source_scope': scope,
            'sources': {'catalog': catalog_ref, 'candidate_map': map_ref}, 'components': components,
            'execution_authorized': False, 'model_binding': dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget'))}
        self.manifest['plan_id'] = sha(self.manifest)
        store(self.plan / 'plan.json', self.manifest)

    def test_readonly_assembly_maps_history_scores_and_input_fingerprint(self):
        from experiment_runner import assemble_task
        result = assemble_task(self.plan, 'PUBLIC-TASK', execution_record=self.record)
        self.assertEqual(result['status'], 'assembled')
        self.assertEqual(result['binding']['base_scores'], [.9])
        payload = json.loads(result['initial_messages'][0]['content'])
        self.assertEqual(payload['H'], [{'parent_asin': 'PUBLIC-HISTORY', 'review_text': 'earlier rice', 'rating': 5}])
        self.assertNotIn('history', payload)
        self.assertEqual(result['binding']['necessary_clauses'], ['c1', 'c2'])
        self.assertEqual(result['snapshot_ref'], self.fixture.facts.snapshot_ref)
        self.assertEqual(payload['input_fingerprint'], sha({k: v for k, v in payload.items() if k != 'input_fingerprint'}))
        self.assertFalse((self.plan / 'budget.jsonl').exists())
        self.assertEqual(result['model_binding'], dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget')))

    def reseal_component(self, name, value):
        self.manifest['components'][name] = {k: v for k, v in store(self.plan / name, value).items() if k != 'path'}
        self.manifest.pop('plan_id')
        self.manifest['plan_id'] = sha(self.manifest)
        store(self.plan / 'plan.json', self.manifest)

    def test_altered_principal_is_rejected_during_assembly(self):
        from experiment_runner import assemble_task
        self.view['principal_id'] = 'PUBLIC-ATTACKER'
        view_ref = store(self.root / 'sources/views.jsonl', self.view) | {'offset': 0, 'line': 1}
        self.reseal_component('user-scenarios.jsonl', {'binding_id': 'PUBLIC-BINDING', 'root_task_id': self.root_id,
            'view_id': self.view_id, 'existing_binding_ref': view_ref})
        with self.assertRaisesRegex(ValueError, 'permission_binding_mismatch'):
            assemble_task(self.plan, 'PUBLIC-TASK', execution_record=self.record)

    def test_public_reference_cannot_read_outside_public_sources(self):
        from experiment_runner import assemble_task
        refs = json.loads((self.plan / 'root-references.jsonl').read_bytes())
        refs['root_ref'] = {'path': str(PROJECT / 'AGENTS.md'), 'bytes': 1, 'sha256': '0'*64}
        self.reseal_component('root-references.jsonl', refs)
        with self.assertRaisesRegex(ValueError, 'fixture_source_scope_mismatch'):
            assemble_task(self.plan, 'PUBLIC-TASK', execution_record=self.record)

    def make_assembled(self, model=None):
        from experiment_runner import assemble_task
        assembly = assemble_task(self.plan, 'PUBLIC-TASK', execution_record=self.record)
        run = self.fixture.make(self.task['method'], model=model, binding_changes=assembly['binding'],
            limits=self.record['limits'], final_reserve=self.record['final_reserve'])
        return assembly, run

    def test_assembled_public_task_runs_once_with_its_exact_safe_input(self):
        from experiment_runner import run_task
        assembly, run = self.make_assembled()
        first = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual((first['terminal'], first['delivered']), ('released', ['PUBLIC-A']))
        self.assertEqual(run.initial_messages, assembly['initial_messages'])
        second = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual(second, first)
        self.assertEqual(first['provider_requests_sent'], 0)

    def test_actual_acquisitions_are_sealed_once_and_referenced_by_task_and_audit(self):
        from experiment_runner import run_task
        _, run = self.make_assembled()
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        ref = result['acquired_ref']
        raw = (PROJECT / ref['path']).read_bytes()
        acquired = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
        self.assertEqual(acquired, run.evidence.audit_view()['acquired'])
        self.assertIn('raw_utf8', next(iter(acquired['candidates']['PUBLIC-A']['originals'].values())))
        audit = json.loads(Path(result['audit_path']).read_bytes())
        self.assertEqual(audit['acquired_ref'], ref)
        files = list((run.output_root / 'trace').glob('acquired-*.json'))
        self.assertEqual(len(files), 1)
        stamp = files[0].stat().st_mtime_ns
        run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual(files[0].stat().st_mtime_ns, stamp)

    def evaluation_sources(self):
        scenes, relations, joint_states, scenario_states = [], [], [], []
        for label in [f'V{i:02d}' for i in range(16)] + ['Q1', 'Q2']:
            scene = self.scene | {'label': label, 'view_id': self.view_id if label == self.scene['label'] else 'PUBLIC-VIEW-' + label,
                                  'arm': 'quality' if label.startswith('Q') else 'necessary'}
            view = self.view | scene
            view_ref = store(self.root / ('sources/view-' + label + '.jsonl'), view) | {'offset': 0, 'line': 1}
            scenes.append(scene)
            relations.append({'binding_id': 'PUBLIC-BINDING' if label == self.scene['label'] else 'PUBLIC-BINDING-' + label,
                'root_task_id': self.root_id, 'view_id': scene['view_id'], 'existing_binding_ref': view_ref})
            joint_states.append({'view': scene['view_id'], 'snapshot': scene['snapshot_id'], 'profile': 'PUBLIC-R1-R5',
                'material_version': view['material_version'], 'parent': 'PUBLIC-A', 'batch': 'BATCH-A',
                'candidate_state': 'Supported', 'eligible': True})
            scenario_states.append({'view_id': scene['view_id'], 'snapshot_id': scene['snapshot_id'],
                'request_profile_id': 'PUBLIC-R1-R5', 'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A',
                'candidate_state': 'Supported', 'eligible': True})
        for name, rows in (('scenes.jsonl', scenes), ('user-scenarios.jsonl', relations)):
            self.manifest['components'][name] = {k: v for k, v in store_lines(self.plan / name, rows).items() if k != 'path'}
        self.manifest.pop('plan_id')
        self.manifest['plan_id'] = sha(self.manifest)
        store(self.plan / 'plan.json', self.manifest)
        return {'scope': 'public_fixture', 'preference': store_lines(self.root / 'references/preference.jsonl',
                    [{'root': self.root_id, 'target_parent': 'PUBLIC-A', 'group': 'dev'}]),
                'joint_states': store_lines(self.root / 'references/joint.jsonl', joint_states),
                'scenario_states': store_lines(self.root / 'references/scenarios.jsonl', scenario_states),
                'fixed_S': ['PUBLIC-A']}

    def test_public_artifacts_and_native_reference_rows_reach_score_task(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from experiment_evaluation import score_task, summarize
        references = self.evaluation_sources()
        _, run = self.make_assembled()
        run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        plan, observations = load_evaluation_inputs(self.plan,
            execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')}, reference_sources=references)
        observed = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
        scored = score_task(**observed)
        self.assertEqual((scored['status'], scored['metrics']['1']['SJ_NDCG']), ('scored', 1.0))
        self.assertEqual(observed['execution']['G'], ['PUBLIC-A'])
        self.assertEqual(observed['execution']['usage']['basis'], 'synthetic_fixture_units')
        summary = summarize(plan, [score_task(**o) for o in observations])
        self.assertEqual((summary['status'], summary['counts']['not_started']), ('incomplete', 49))
        self.assertEqual(len(observations), 50)
        self.assertIsNone(summary['comparisons']['C1']['estimate'])

    def test_changed_audit_bytes_are_not_accepted_as_actual_observation(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        references = self.evaluation_sources()
        _, run = self.make_assembled()
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        audit = json.loads(Path(result['audit_path']).read_bytes())
        audit['cursor'] = 0
        store(Path(result['audit_path']), audit)
        with self.assertRaisesRegex(ValueError, 'artifact_binding_mismatch'):
            load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                   reference_sources=references)

    def test_evaluation_reads_shared_view_rows_and_added_scene_templates(self):
        from experiment_io import load_evaluation_inputs
        references = self.evaluation_sources()
        relations = [json.loads(raw) for raw in (self.plan / 'user-scenarios.jsonl').read_bytes().splitlines()]
        views = [json.loads(Path(row['existing_binding_ref']['path']).read_bytes()) for row in relations]
        shared = self.root / 'sources/shared-views.jsonl'
        store_lines(shared, [{'unused': 'PUBLIC first row'}] + views)
        offset = len(wire({'unused': 'PUBLIC first row'}) + b'\n')
        for line, (row, view) in enumerate(zip(relations, views), 2):
            raw = wire(view) + b'\n'
            row['existing_binding_ref'] = {'path': str(shared), 'offset': offset, 'line': line,
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            offset += len(raw)
        template = relations[0]['existing_binding_ref']
        for index in (2, 4, 8, 10, 11, 13, 14, 15):
            relations[index].pop('existing_binding_ref')
            relations[index]['request_template_ref'] = template
        relations[2].pop('request_template_ref')  # accepted frozen rows may use the V00 fallback
        self.manifest['components']['user-scenarios.jsonl'] = {
            k: v for k, v in store_lines(self.plan / 'user-scenarios.jsonl', relations).items() if k != 'path'}
        self.manifest.pop('plan_id')
        self.manifest['plan_id'] = sha(self.manifest)
        store(self.plan / 'plan.json', self.manifest)
        plan, observations = load_evaluation_inputs(self.plan, execution_index={}, reference_sources=references)
        self.assertEqual((len(plan['scenes']), len(observations)), (18, 50))
        added = next(o for o in observations if o['task']['scene'] == 'V02')
        self.assertEqual((added['task']['view_id'], added['task']['request_profile_id']),
                         ('PUBLIC-VIEW-V02', 'PUBLIC-R1-R5'))

    def test_M_external_double_keeps_fixture_provenance_through_scoring(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from experiment_evaluation import score_task
        from tests.runtime_fixtures import ScriptedTransport
        from tests.test_on_demand_runtime import public_model
        self.task.update(method='M', uses_model=True)
        self.record['limits'].update(model_calls=1000, input_tokens=10000000, output_tokens=10000000, cost_microusd=10000000)
        self.record['final_reserve'].update(model_calls=1, input_tokens=100000, output_tokens=100000)
        self.write_plan()
        references = self.evaluation_sources()
        transport = ScriptedTransport()
        _, run = self.make_assembled(public_model(transport))
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual((result['terminal'], result['delivered']), ('released', ['PUBLIC-A']))
        self.assertTrue(transport.requests)
        self.assertTrue(all(r['model_id'] is None for r in transport.requests))
        self.assertTrue(all(m['provenance'] == 'on_demand_public_fixture' for m in run.state['messages']))
        _, observations = load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                                reference_sources=references)
        observed = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
        self.assertEqual(score_task(**observed)['metrics']['10']['SJ_NDCG'], 1.0)
        self.assertEqual(observed['execution']['usage']['input_tokens'], sum(m['response']['usage']['input_tokens'] for m in run.state['messages']))
        self.assertEqual(result['provider_requests_sent'], 0)
        store(PROJECT / '.scratch/ticket14-live-integration-20261020/public-example.json', {
            'scope': 'public_fixture_only', 'plan': file_ref(self.plan / 'plan.json'),
            'execution_index': {'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
            'reference_sources': references, 'task_score': score_task(**observed),
            'real_recommendations': 0, 'real_evaluations': 0, 'provider_requests_sent': 0})

    def test_frozen_development_tasks_are_assembly_only_even_with_fixture_permission(self):
        from experiment_runner import assemble_task, run_task
        from experiment_io import load_evaluation_inputs
        pilot = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/pilot'
        manifest = json.loads((pilot / 'manifest.json').read_bytes())
        tasks = [json.loads(raw) for raw in (pilot / 'tasks.jsonl').read_bytes().splitlines()]
        self.assertEqual([t['task_key'] for t in tasks], [
            '7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874',
            'a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4',
            '4fc09c3d2c7a0ad10bf5af864479975fc62c3d12c7b4f8b8f476094651a9694e',
            '5f6174e27e713189c45fcfd348cb1a22758bf3098bf7baecab10c8eaed10ece8',
            '1f32a41c58c91b83aa5b31d4bfb654a9defb348721569c8f28d5dc1e2177a291',
            'e1606ef935844cd2324ed4dce4b946ef887171413632bf9ca28996d0ac442b6b',
            '158c0644067e77ecfa3435163d9d07789bf0925c09028a540065a68129630a86',
            '9a373be927071c842734a0a2b03bc79b133b04cb06dbe8394910da9ec7ed39c8'])
        proof = json.loads((pilot / 'membership.json').read_bytes())
        self.assertEqual((proof['split'], proof['formal_overlap']), ('dev', 0))
        self.assertEqual(manifest['model_binding'], dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget')))
        assembly = assemble_task(pilot, tasks[0]['task_key'], execution_record=self.record)
        self.assertEqual(assembly['binding']['execution_kind'], 'unbound_stage_A')
        self.assertEqual(assembly['terminal'], 'configuration_required')
        output = self.root / 'forbidden-real-run'
        result = run_task(pilot, tasks[0]['task_key'], runtime=object(), output_root=output, execution_record=self.record)
        self.assertEqual((result['terminal'], result['started'], result['provider_requests_sent']), ('configuration_required', False, 0))
        self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, 'stage_A_real_evaluation_forbidden'):
            load_evaluation_inputs(pilot, execution_index={}, reference_sources={})

    def test_development_membership_and_parent_plan_are_required_sources(self):
        from experiment_runner import assemble_task
        pilot = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/pilot'
        copied = self.root / 'forged-pilot'
        copied.mkdir()
        manifest = json.loads((pilot / 'manifest.json').read_bytes())
        for name in manifest['components']:
            (copied / name).write_bytes((pilot / name).read_bytes())
        proof = json.loads((pilot / 'membership.json').read_bytes())
        proof['split'] = 'test'
        manifest['membership_ref'] = store(copied / 'membership.json', proof)
        manifest.pop('pilot_id')
        manifest['pilot_id'] = sha(manifest)
        store(copied / 'manifest.json', manifest)
        key = json.loads((copied / 'tasks.jsonl').read_bytes().splitlines()[0])['task_key']
        with self.assertRaisesRegex(ValueError, 'development_membership_mismatch'):
            assemble_task(copied, key)

    def test_Q_components_use_the_single_actual_M_acquisition(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from experiment_evaluation import score_task
        from tests.runtime_fixtures import ScriptedTransport
        from tests.test_on_demand_runtime import public_model
        self.fixture.quality(parents=('PUBLIC-A',), scores=[.9])
        self.scene.update(label='Q1', arm='quality', snapshot=self.fixture.facts.snapshot_ref,
                          snapshot_id=self.fixture.facts.snapshot['snapshot_id'])
        self.task.update(method='M', uses_model=True)
        self.record['limits'].update(model_calls=1000, input_tokens=10000000, output_tokens=10000000, cost_microusd=10000000)
        self.record['final_reserve'].update(model_calls=1, input_tokens=100000, output_tokens=100000)
        self.record['prefix_limit'] = 1
        self.record['fusion'] = {'schema_version': 'fusion-binding-0.1.0', 'task_id': self.root_id,
            'C': ['PUBLIC-A'], 'C_sha256': sha(['PUBLIC-A']), 'H_sha256': sha(self.fixture.history),
            'base_scores': [.9], 'base_score_version': 'PUBLIC-SCORE', 'base_score_sha256': sha([['PUBLIC-A', .9]]),
            'snapshot_id': self.scene['snapshot_id'], 'verify_at_ms': 1000, 'principal_id': 'SIM-VERIFIER',
            'contract_sha256': sha(self.fixture.facts.rules), 'K': 10, 'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
            'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
        self.write_plan()
        references = self.evaluation_sources()
        _, run = self.make_assembled(public_model(ScriptedTransport()))
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual(result['terminal'], 'released')
        _, observations = load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                                reference_sources=references)
        observed = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
        score = score_task(**observed)
        self.assertEqual(score['status'], 'scored', score.get('error'))
        self.assertEqual({m: c['SJ_C'] for m, c in score['components'].items()},
                         {'full': 1.0, 'no_quality': 1.0, 'mean_quality': 1.0})
        self.assertEqual(observed['execution']['acquired'], run.evidence.audit_view()['acquired'])
        self.assertEqual(score['quality']['mean_denominator'], 1)
        store(PROJECT / '.scratch/ticket14-live-integration-20261020/public-Q-example.json', {
            'scope': 'public_fixture_only', 'task_score': score, 'acquired_ref': result['acquired_ref'],
            'execution': file_ref(run.output_root / 'task.json'), 'provider_requests_sent': 0})

    def test_unresolved_intent_is_not_a_missing_or_zero_scored_execution(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from experiment_evaluation import score_task
        references = self.evaluation_sources()
        _, run = self.make_assembled()
        intent = store(run.output_root / 'task.intent.json', {'task_key': 'PUBLIC-TASK', 'plan_id': self.manifest['plan_id']})
        self.assertEqual(run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root,
                                 execution_record=self.record)['terminal'], 'unresolved_attempt')
        _, observations = load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': intent}, reference_sources=references)
        score = score_task(**next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK'))
        self.assertEqual(score['execution_state'], 'unresolved')
        self.assertIsNone(score['metrics']['10']['SJ_NDCG'])
        self.assertFalse((run.output_root / 'audit.json').exists())

    def test_missing_actual_A_is_not_recovered_from_sources_or_references(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        references = self.evaluation_sources()
        _, run = self.make_assembled()
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        receipt_count = len(run.evidence.receipts)
        (PROJECT / result['acquired_ref']['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                   reference_sources=references)
        self.assertEqual(len(run.evidence.receipts), receipt_count)

    def test_missing_scheduled_execution_is_pipeline_error_and_other_slots_are_not_started(self):
        from experiment_io import load_evaluation_inputs
        from experiment_evaluation import score_task, summarize
        references = self.evaluation_sources()
        plan, observations = load_evaluation_inputs(self.plan, execution_index={}, reference_sources=references)
        summary = summarize(plan, [score_task(**o) for o in observations])
        self.assertEqual(summary['counts']['pipeline_errors'], 1)
        self.assertEqual(summary['counts']['not_started'], 49)
        self.assertEqual(summary['status'], 'incomplete')
        self.assertIsNone(summary['comparisons']['C1']['estimate'])

    def test_independent_reference_with_wrong_batch_cannot_be_used(self):
        from experiment_io import load_evaluation_inputs
        references = self.evaluation_sources()
        rows = [json.loads(raw) for raw in Path(references['joint_states']['path']).read_bytes().splitlines()]
        rows[0]['batch'] = 'PUBLIC-WRONG-BATCH'
        references['joint_states'] = store_lines(Path(references['joint_states']['path']), rows)
        with self.assertRaisesRegex(ValueError, 'independent_reference_binding_mismatch'):
            load_evaluation_inputs(self.plan, execution_index={}, reference_sources=references)

    def test_failed_model_preserves_unknown_usage_without_retry_or_zero_fill(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from experiment_evaluation import score_task
        from tests.runtime_fixtures import ScriptedTransport
        from tests.test_on_demand_runtime import public_model
        self.task.update(method='M', uses_model=True)
        self.record['limits'].update(model_calls=1000, input_tokens=10000000, output_tokens=10000000, cost_microusd=10000000)
        self.record['final_reserve'].update(model_calls=1, input_tokens=100000, output_tokens=100000)
        self.write_plan()
        references = self.evaluation_sources()
        def unknown_usage(request, raw, context):
            raw['usage']['input_tokens'] = None
        transport = ScriptedTransport(mutate=unknown_usage)
        _, run = self.make_assembled(public_model(transport))
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual(result['terminal'], 'failed_model')
        self.assertEqual(len(transport.requests), 1)
        _, observations = load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                                reference_sources=references)
        score = score_task(**next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK'))
        self.assertEqual((score['execution_state'], score['metrics']['10']['SJ_NDCG']), ('failed', 0))
        self.assertIsNone(score['usage']['input_tokens'])

    def test_A_guard_blocks_real_reference_reads_outside_writes_and_network(self):
        import socket
        self.assertTrue(os.environ.get('THESIS_LIVE_A_PACKAGE'))
        with self.assertRaisesRegex(OSError, 'live_A_real_evaluation_or_unapproved_read_forbidden'):
            (PROJECT / 'data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/preference-reference.jsonl').read_bytes()
        with self.assertRaisesRegex(OSError, 'write_outside_outputs'):
            (PROJECT / 'live-A-forbidden.txt').write_text('PUBLIC')
        with self.assertRaisesRegex(OSError, 'network_forbidden'):
            socket.create_connection(('127.0.0.1', 1), timeout=.1)

    def test_count_drift_keeps_unknown_totals_and_known_attempt_subtotal(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from tests.runtime_fixtures import ScriptedTransport
        from tests.test_on_demand_runtime import public_model
        self.task.update(method='M', uses_model=True)
        self.record['limits'].update(model_calls=1000, input_tokens=10000000, output_tokens=10000000, cost_microusd=10000000)
        self.record['final_reserve'].update(model_calls=1, input_tokens=100000, output_tokens=100000)
        self.write_plan()
        references = self.evaluation_sources()
        def drift(request, raw, context):
            if request['request_id'].endswith(':1'):
                raw['usage']['input_tokens'] -= 1
        transport = ScriptedTransport(mutate=drift)
        _, run = self.make_assembled(public_model(transport))
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        self.assertEqual((result['terminal'], len(transport.requests)), ('failed_model', 2))
        self.assertEqual(run.state['messages'][1]['response']['status'], 'usage_mismatch')
        self.assertIsNotNone(run.state['messages'][1]['response']['usage']['input_tokens'])
        _, observations = load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                                reference_sources=references)
        usage = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')['execution']['usage']
        self.assertIsNone(usage['input_tokens'])
        self.assertIsNone(usage['output_tokens'])
        self.assertIsNone(usage['cost_microusd'])
        self.assertEqual(usage['known_subtotal'], run.state['messages'][0]['response']['usage'])

    def test_evaluation_requires_each_actual_request_and_response_trace(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        from tests.runtime_fixtures import ScriptedTransport
        from tests.test_on_demand_runtime import public_model
        self.task.update(method='M', uses_model=True)
        self.record['limits'].update(model_calls=1000, input_tokens=10000000, output_tokens=10000000, cost_microusd=10000000)
        self.record['final_reserve'].update(model_calls=1, input_tokens=100000, output_tokens=100000)
        self.write_plan()
        references = self.evaluation_sources()
        _, run = self.make_assembled(public_model(ScriptedTransport()))
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        audit = json.loads(Path(result['audit_path']).read_bytes())
        for key in ('request_ref', 'response_ref'):
            with self.subTest(trace=key):
                path = PROJECT / audit['messages'][0][key]['path']
                raw = path.read_bytes()
                path.unlink()
                with self.assertRaises(FileNotFoundError):
                    load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': file_ref(run.output_root / 'task.json')},
                                           reference_sources=references)
                path.write_bytes(raw)

    def test_success_requires_same_run_final_commit_and_audit_settlement(self):
        from experiment_io import load_evaluation_inputs
        from experiment_runner import run_task
        references = self.evaluation_sources()
        _, run = self.make_assembled()
        result = run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=self.record)
        journal_path = PROJECT / result['budget_ref']['path']
        original = [json.loads(raw) for raw in journal_path.read_bytes().splitlines()]
        for operation in ('final', 'commit', 'seal_audit'):
            with self.subTest(missing_settlement=operation):
                reservation = next(r['reservation_id'] for r in original if r.get('operation') == operation)
                changed = [r for r in original if not (r.get('reservation_id') == reservation and r['status'] == 'settled')]
                altered = result | {'budget_ref': store_lines(journal_path, changed)}
                task_ref = store(run.output_root / 'task.json', altered)
                with self.assertRaisesRegex(ValueError, 'settlement_binding_mismatch'):
                    load_evaluation_inputs(self.plan, execution_index={'PUBLIC-TASK': task_ref}, reference_sources=references)

    def test_added_scene_uses_exact_snapshot_and_original_request_template(self):
        from experiment_runner import assemble_task
        template = json.loads((self.plan / 'user-scenarios.jsonl').read_bytes())['existing_binding_ref']
        self.scene.update(label='V02', view_id='PUBLIC-ADDED-VIEW')
        self.reseal_component('scenes.jsonl', self.scene)
        self.reseal_component('user-scenarios.jsonl', {'binding_id': 'PUBLIC-BINDING', 'root_task_id': self.root_id,
            'view_id': 'PUBLIC-ADDED-VIEW', 'request_template_ref': template})
        assembly = assemble_task(self.plan, 'PUBLIC-TASK', execution_record=self.record)
        self.assertEqual(assembly['binding']['view_id'], 'PUBLIC-ADDED-VIEW')
        self.assertEqual(assembly['binding']['snapshot_id'], self.fixture.facts.snapshot['snapshot_id'])
        self.assertEqual(assembly['binding']['necessary_clauses'], ['c1', 'c2'])

    def test_dispatch_cannot_use_a_different_budget_from_the_assembly_record(self):
        from experiment_runner import run_task
        _, run = self.make_assembled()
        changed = copy.deepcopy(self.record)
        changed['limits']['candidates'] = 1
        with self.assertRaisesRegex(ValueError, 'assembled_runtime_budget_mismatch'):
            run_task(self.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=changed)
        self.assertFalse((run.output_root / 'task.intent.json').exists())

    def test_missing_fixture_budget_is_explicit_configuration_required(self):
        from experiment_runner import assemble_task
        result = assemble_task(self.plan, 'PUBLIC-TASK', execution_record={'fixture': True})
        self.assertEqual(result['status'], 'configuration_required')
        self.assertEqual(set(result['missing']), {'run_id', 'limits', 'final_reserve'})


if __name__ == '__main__':
    unittest.main()
