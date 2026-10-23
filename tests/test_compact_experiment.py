"""Exercise real restricted tools on public facts, and inject only provider IO."""
import tempfile
import unittest
import json
import time
from unittest.mock import patch
from pathlib import Path

from evidence_access import PROJECT
from tests.runtime_fixtures import RuntimeFixture


class CompactTools(unittest.TestCase):
    def test_public_full_scene_run_and_resume_reuses_seven_profile_calls(self):
        from compact_experiment import execute, store_json, file_ref
        from evidence_access import digest, encoded
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            root = Path(temp)
            normal = RuntimeFixture(root / 'normal').candidates(['PUBLIC-A', 'PUBLIC-B'])
            quality = RuntimeFixture(root / 'quality').quality()
            catalog = [{'parent_asin': 'PUBLIC-A', 'crop': 'rice', 'title': 'Rice Grain'},
                       {'parent_asin': 'PUBLIC-B', 'crop': 'rice', 'title': 'Rice Flour'}]
            mapping = [{'parent_asin': p, 'sim_batch_id': b} for p, b in zip(normal.parents, normal.batches)]
            for name, rows in (('catalog', catalog), ('mapping', mapping)):
                (root / (name + '.jsonl')).write_bytes(b''.join(encoded(r) + b'\n' for r in rows))
            history = [{'parent_asin': 'PUBLIC-B', 'text': 'I prefer flour', 'rating': 5}]
            source = {'root_task_id': 'PUBLIC-U', 'history': history, 'H_sha256': digest(encoded(history)),
                'C_sha256': digest(encoded(normal.parents)),
                'base_scores_sha256': digest(encoded(list(zip(normal.parents, [.6, .4]))))}
            store_json(root / 'root.json', source)
            store_json(root / 'candidates.json', {'root_task_id': 'PUBLIC-U', 'C': normal.parents, 'b': [.6, .4]})
            tables = {'root-references.jsonl': [{'root_task_id': 'PUBLIC-U',
                'root_ref': file_ref(root / 'root.json'), 'candidate_ref': file_ref(root / 'candidates.json')}],
                'user-scenarios.jsonl': [], 'scenes.jsonl': [], 'tasks.jsonl': []}
            for label in [f'V{i:02d}' for i in range(16)] + ['Q1', 'Q2']:
                facts = quality.facts if label.startswith('Q') else normal.facts
                snapshot = json.loads((PROJECT / facts.snapshot_ref['path']).read_bytes())
                tables['scenes.jsonl'].append({'view_id': label, 'label': label,
                    'snapshot': facts.snapshot_ref, 'snapshot_id': snapshot['snapshot_id'],
                    'arm': 'quality' if label.startswith('Q') else 'necessary'})
                tables['user-scenarios.jsonl'].append({'binding_id': label, 'root_task_id': 'PUBLIC-U', 'view_id': label})
                tables['tasks.jsonl'].extend({'task_key': label + '-' + m, 'binding_id': label, 'method': m}
                    for m in (('M',) if label.startswith('Q') else ('R', 'S', 'M')))
            plan = {'sources': {'catalog': file_ref(root / 'catalog.jsonl'),
                                'candidate_map': file_ref(root / 'mapping.jsonl')}}
            cfg = {'configuration_id': 'public', 'users': ['PUBLIC-U'], 'plan_directory': 'unused',
                'max_calls': 7, 'max_new_bytes': 16 * 1024**2, 'max_hours': 1, 'alpha': .5,
                'counts': {'scenarios': 18, 'tasks': 50}}
            requests = []
            def provider(request):
                requests.append(request)
                option = 'h0:form' if request['role'] in ('单智能体', '推荐依据核验') else 'h0:crop'
                return {'selections': [{'option_id': option, 'weight': 1}],
                    'issues': ['History explicitly prefers flour'] if option == 'h0:form' else []}
            with (patch('compact_experiment.OUTPUT', root / 'output'),
                  patch('compact_experiment.load_config', return_value=cfg),
                  patch('experiment_runner._task_plan', return_value=(root, plan, tables))):
                completed = execute(confirm=True, provider=provider)
                self.assertEqual(completed['completed_task_rows'], 50)
                self.assertEqual(len(requests), 7)
                self.assertNotIn('evidence_summary', str(requests))
                row = json.loads((root / 'output/tasks/V00-M.json').read_bytes())
                self.assertEqual(row['topK'][0], 'PUBLIC-B')
                self.assertEqual(row['components']['no_feedback']['topK'][0], 'PUBLIC-A')
                again = execute(confirm=True, provider=lambda request: self.fail('unnecessary resend'))
                self.assertEqual(again['completed_task_rows'], 50)
                self.assertEqual(again['actual_profile_attempts'], 7)

    def test_evaluation_checks_shared_deadline_and_storage_before_private_references(self):
        from compact_evaluation import evaluate
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            root = Path(temp)
            cfg = {'configuration_id': 'public', 'max_new_bytes': 4096, 'max_hours': 24}
            (root / 'authorization.json').write_text(json.dumps({'configuration_id': 'public'}))
            for expired, expected in ((True, 'compact_deadline'), (False, 'compact_storage_limit')):
                (root / 'started.json').write_text(json.dumps({'deadline': time.time() + (-1 if expired else 60)}))
                (root / 'large.bin').write_bytes(b'x' * (0 if expired else 4096))
                with (patch('compact_evaluation.OUTPUT', root),
                      patch('compact_evaluation.load_config', return_value=cfg),
                      patch('compact_evaluation.source_references', side_effect=AssertionError('private source reached')),
                      self.assertRaisesRegex(ValueError, expected)):
                    evaluate()

    def test_changed_cached_evidence_or_profile_is_rejected_before_reuse(self):
        from compact_experiment import ProfileCalls
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            store = ProfileCalls(Path(temp), provider=lambda request: {'selections': [], 'issues': []})
            cache = Path(temp) / 'scene.json'
            store.write(cache, {'eligible': False, 'principal_id': 'SIM-VERIFIER'})
            cache.write_text(json.dumps({'eligible': True, 'principal_id': 'WRONG'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'compact_artifact_changed'):
                store.read(cache)

    def test_quality_scene_reuses_the_existing_stock_calculation(self):
        from compact_experiment import collect_scene
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            fixture = RuntimeFixture(Path(temp)).quality()
            observed = collect_scene(fixture.facts.snapshot_ref,
                [{'parent_asin': p, 'sim_batch_id': b} for p, b in zip(fixture.parents, fixture.batches)], quality=True)
            stock = observed['candidates']['PUBLIC-A']['stock']
            self.assertEqual(stock, {'supported': True, 'value': 75, 'quality': .6})

    def test_model_generation_limit_stops_before_external_call(self):
        from compact_experiment import ProfileCalls
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            calls = []
            def provider(request):
                calls.append(request)
                return {'selections': [], 'issues': []}
            store = ProfileCalls(Path(temp), provider=provider, max_calls=1)
            store({'role': '用户画像', 'context': {}})
            with self.assertRaisesRegex(ValueError, 'compact_call_limit'):
                store({'role': '推荐管理', 'context': {}})
            self.assertEqual(len(calls), 1)

    def test_new_quality_protocol_uses_independent_heldout_target(self):
        from experiment_evaluation import score_task
        from tests.test_experiment_evaluation import example
        task, execution, reference = example(scene='Q1')
        scored = score_task(task, execution, reference, component_protocol='personalized')
        self.assertEqual(scored['status'], 'scored')
        self.assertAlmostEqual(scored['metrics']['10']['NDCG_P'], .6309297535714575)
        reference['target'] = 'd'
        changed = score_task(task, execution, reference, component_protocol='personalized')
        self.assertEqual(changed['metrics']['10']['HR'], 0)

    def test_profile_call_is_reused_and_interrupted_send_is_never_retried(self):
        from compact_experiment import ProfileCalls
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            calls = []
            def provider(request):
                calls.append(request)
                return {'selections': [], 'issues': []}
            store = ProfileCalls(Path(temp), provider=provider, max_calls=2)
            request = {'role': '用户画像', 'context': {'history': []}}
            self.assertEqual(store(request), store(request))
            self.assertEqual(len(calls), 1)
            def interrupted(request):
                raise RuntimeError('interrupted_before_receipt')
            interrupted_store = ProfileCalls(Path(temp), provider=interrupted, max_calls=2)
            with self.assertRaises(RuntimeError):
                interrupted_store({'role': '推荐管理', 'context': {}})
            with self.assertRaisesRegex(ValueError, 'unresolved_profile_attempt'):
                store({'role': '推荐管理', 'context': {}})

    def test_shared_scene_uses_real_materials_and_rejects_wrong_batch(self):
        from compact_experiment import collect_scene
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as temp:
            fixture = RuntimeFixture(Path(temp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
            for row in fixture.facts.rows['materials.jsonl']:
                if row['parent_asin'] == 'PUBLIC-B' and row['kind'] == 'inspection_report':
                    row['sim_batch_id'] = 'WRONG-BATCH'
            fixture.seal()
            collected = collect_scene(fixture.facts.snapshot_ref,
                [{'parent_asin': p, 'sim_batch_id': b} for p, b in zip(fixture.parents, fixture.batches)])
            self.assertTrue(collected['candidates']['PUBLIC-A']['eligible'])
            self.assertFalse(collected['candidates']['PUBLIC-B']['eligible'])


if __name__ == '__main__':
    unittest.main()
