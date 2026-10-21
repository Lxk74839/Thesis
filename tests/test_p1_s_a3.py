"""Synthetic PUBLIC complete S, not a replay or real D1 execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_p1_s_engineering import setUpModule

GRANT = 'S-COMPLETE-ONCE-20261021-A3'


def config():
    from evidence_access import PROJECT
    cfg = json.loads((PROJECT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
    cfg['authorization_id'] = cfg['model_binding']['engineering_authorization'] = GRANT
    cfg['limits']['S'].update(model_calls=10, request_output_tokens=81920, elapsed_ms=1749082)
    cfg['final_reserve']['S']['elapsed_ms'] = 145000
    return cfg


class A3S(unittest.TestCase):
    def test_shared_execution_includes_A3_and_never_refunds_previous_attempts(self):
        from evidence_access import PROJECT
        spec = importlib.util.spec_from_file_location('A3_control',
            PROJECT / '.scratch/ticket14-s-120-20261021/control.py')
        control = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(control)
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as tmp:
            for attempt, seconds in (('A1', 15), ('A2', 16), ('A3', 42)):
                directory = Path(tmp) / attempt
                directory.mkdir()
                (directory / 'execution-resources.jsonl').write_text(json.dumps({'seconds': seconds}) + '\n')
            self.assertEqual(control.execution_used(tmp), 73)

    def test_complete_PUBLIC_S_uses_production_reasoning_tools_and_opaque_continuation(self):
        from evidence_access import PROJECT
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget
        parent = PROJECT / '.tmp/recommendation-runtime/PUBLIC-A3'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
            fixture.now[0] = 10000
            http, wires = RouterHTTPFixture(), []
            def transport(text, *, deadline_ms):
                wire = json.loads(text)
                wires.append(wire)
                self.assertTrue(0 < deadline_ms - fixture.now[0] <= 120000)
                fixture.now[0] += 23
                # External synthetic provider understands native metadata; old fixture
                # scripting needs only the business history to choose its next reply.
                business = copy.deepcopy(wire)
                business['input'] = [i for i in business['input'] if i.get('type') != 'reasoning']
                for index, item in enumerate(business['input']):
                    if item.get('type') == 'message':
                        business['input'][index] = {'role': 'assistant', 'content': item['content'][0]['text']}
                reply = http(json.dumps(business), deadline_ms=deadline_ms)
                reply['body'].pop('usage')
                reply['body']['output'].insert(0, {'type': 'reasoning', 'id': 'PUBLIC-rs-' + str(len(wires)),
                    'summary': [{'type': 'summary_text', 'text': 'PUBLIC synthetic summary'}],
                    'content': [{'type': 'reasoning_text', 'text': 'PUBLIC synthetic private reasoning'}],
                    'encrypted_content': 'PUBLIC-OPAQUE-A3', 'status': 'completed'})
                return reply
            cfg = config()
            model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
                'engineering_authorization': GRANT, 'execution_authorized': True, 'pricing': None})
            run = fixture.make('S', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1', 'authorization_id': GRANT,
                'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
            budget = SEngineeringBudget(run.binding, cfg['limits']['S'], cfg['final_reserve']['S'],
                clock=lambda: fixture.now[0], journal_path=Path(tmp) / 'A3-budget.jsonl')
            run.budget = run.evidence.root_budget = model.root_budget = budget
            result = run.run()
            self.assertEqual(result['terminal'], 'released', result.get('reason'))
            self.assertEqual(len(wires), 9)
            followups = [w for w in wires if any(i.get('type') == 'function_call_output' for i in w['input'])]
            self.assertTrue(followups)
            self.assertTrue(all(any(i.get('encrypted_content') == 'PUBLIC-OPAQUE-A3'
                for i in w['input']) for w in followups))
            self.assertEqual(wires[-1]['max_output_tokens'], 1500)
            self.assertLessEqual(sum(w['max_output_tokens'] for w in wires), 81920)
            self.assertIsNone(result['budget']['usage']['input_tokens'])
            self.assertIsNone(result['budget']['usage']['cost_microusd'])
            self.assertFalse(result['budget']['usage_exact'])
            archived = json.dumps(result)
            self.assertNotIn('PUBLIC-OPAQUE-A3', archived)
            self.assertNotIn('PUBLIC synthetic private reasoning', archived)

    def test_A3_real_1493_prepare_and_preflight_never_execute_or_read_credentials(self):
        import p1_runtime as p1
        parent = p1.PROJECT / '.tmp/recommendation-runtime/PUBLIC-A3'
        parent.mkdir(parents=True, exist_ok=True)
        cfg = config()
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            path = Path(tmp) / 'PUBLIC-A3.config.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            ready = p1.prepare_p1(path, 'S', storage_guard=p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2))
            self.assertEqual(ready['terminal'], 'ready', ready)
            with p1.P1StorageGuard(tmp, 64 * 1024**2) as guard:
                assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={
                    'run_id': 'P1-D1-V00-S-' + GRANT})
                run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=Path(tmp))
                run._preflight()
                self.assertEqual(len(run.binding['C']), 1493)
                self.assertEqual(run.budget.usage['model_calls'], 0)
                self.assertEqual(guard.allowed['credentials'], 0)
                self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})
                self.assertEqual(run.budget.final_reserve['model_calls'], 1)
                self.assertEqual(run.budget.final_reserve['request_output_tokens'], 1500)
                self.assertEqual(run.budget.final_reserve['elapsed_ms'], 145000)


if __name__ == '__main__':
    unittest.main()
