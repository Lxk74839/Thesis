"""Exercise real restricted tools on public facts, and inject only provider IO."""
import tempfile
import unittest
from pathlib import Path

from evidence_access import PROJECT
from tests.runtime_fixtures import RuntimeFixture


class CompactTools(unittest.TestCase):
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
