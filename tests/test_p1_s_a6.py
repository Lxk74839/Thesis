"""PUBLIC quota/checkpoint fixtures; real D1 is never executed by tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_p1_s_a5 import control_module
from tests.test_p1_s_engineering import setUpModule

ROOT = Path(__file__).resolve().parents[1]
GRANT = 'S-COMPLETE-ONCE-20261021-A6'
RUN = 'P1-D1-V00-S-' + GRANT


class A6(unittest.TestCase):
    def test_real_1493_preflight_and_sender_chain_remain_nonexecuting(self):
        import p1_runtime as p1
        from tests.test_p1_s_deadline import AdvancingClock
        from recommendation_runner import RunStop
        cfg = json.loads((ROOT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
        cfg['authorization_id'] = cfg['model_binding']['engineering_authorization'] = GRANT
        cfg['limits']['S'].update(model_calls=12, request_output_tokens=91612, elapsed_ms=1643819)
        cfg['final_reserve']['S']['elapsed_ms'] = 145000
        cfg.update(storage_limit_bytes=128 * 1024**2, run_storage_limit_bytes=64 * 1024**2)
        parent = ROOT / '.tmp/recommendation-runtime/PUBLIC-A6-admission'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            root = Path(tmp)
            path = root / 'PUBLIC.config.json'
            path.write_text(json.dumps(cfg))
            guard = p1.P1StorageGuard(p1.OUTPUT, 128 * 1024**2, run_root=p1.OUTPUT / RUN,
                run_limit_bytes=64 * 1024**2)
            self.assertEqual(p1.prepare_p1(path, 'S', storage_guard=guard)['terminal'], 'ready')
            for key, value in (('model_calls', 13), ('request_output_tokens', 91613), ('elapsed_ms', 1643820)):
                bad = copy.deepcopy(cfg)
                bad['limits']['S'][key] = value
                path.write_text(json.dumps(bad))
                self.assertEqual(p1.prepare_p1(path, 'S', storage_guard=guard)['terminal'], 'not_started')
            path.write_text(json.dumps(cfg))
            self.assertIn('A6_run_storage_guard', p1.prepare_p1(path, 'S',
                storage_guard=p1.P1StorageGuard(p1.OUTPUT, 128 * 1024**2))['missing'])
            with p1.P1StorageGuard(root, 128 * 1024**2, run_root=root / RUN,
                    run_limit_bytes=64 * 1024**2) as active:
                assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={'run_id': RUN})
                run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=root)
                run._preflight()
                self.assertEqual(len(run.binding['C']), 1493)
                self.assertEqual(run.budget.usage['model_calls'], 0)
                clock = AdvancingClock()
                run.budget.clock, run.budget.started = clock, clock()
                calls = []
                def sentinel(text, *, deadline_ms):
                    wire = json.loads(text)
                    frame = json.loads(wire['input'][-1]['content'])['runtime']
                    self.assertEqual(len(frame['candidate_batches']), 1493)
                    self.assertLessEqual(len(text.encode()), 2 * 1024**2)
                    calls.append(deadline_ms)
                    raise OSError('PUBLIC_A6_transport_sentinel')
                run.model.transport = sentinel
                with self.assertRaises(RunStop):
                    run._role('需求解析', 'analysis', '需求解析')
                self.assertEqual(len(calls), 1)
                self.assertEqual(active.allowed['credentials'], 0)
                self.assertEqual(active.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})
                self.assertEqual(run.budget.final_reserve['elapsed_ms'], 145000)

    def test_A6_execution_time_is_added_after_five_old_attempts(self):
        control = control_module()
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as tmp:
            for attempt, seconds in (('A1', 15), ('A2', 16), ('A3', 15), ('A4', 44), ('A5', 46), ('A6', 10)):
                path = Path(tmp) / attempt
                path.mkdir()
                (path / 'execution-resources.jsonl').write_text(json.dumps({'seconds': seconds}) + '\n')
            self.assertEqual(control.execution_used(tmp), 146)

    def test_eight_historical_claims_remain_and_A6_has_12_local_20_shared_limit(self):
        control = control_module()
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as tmp:
            path = Path(tmp) / 'PUBLIC-shared.jsonl'
            old = ''.join(json.dumps({'run_id': 'PUBLIC-old', 'sequence': i + 1,
                'output_cap': 8192}) + '\n' for i in range(8)).encode()
            path.write_bytes(old)
            for _ in range(11):
                control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 8192}, RUN)
            with self.assertRaises(OSError):
                control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 8192}, RUN)
            control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1500}, RUN)
            with self.assertRaises(OSError):
                control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1}, RUN)
            self.assertTrue(path.read_bytes().startswith(old))
            self.assertEqual(len(control.requests(path)), 20)
            self.assertEqual(sum(r['output_cap'] for r in control.requests(path)), 157148)

    def test_complete_production_fixture_checks_dispatch_once_then_continues_or_stops(self):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from tests.test_fourrouter_production_protocol import reasoning
        from tests.test_fourrouter_message_selection import message
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget
        parent = ROOT / '.tmp/recommendation-runtime/PUBLIC-A6'
        parent.mkdir(parents=True, exist_ok=True)
        for failure in (None, 'JSON', 'contract'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(dir=parent) as tmp:
                fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
                http, kinds = RouterHTTPFixture(), []
                fixture.now[0] = 10000
                def transport(text, *, deadline_ms):
                    wire = json.loads(text)
                    kind = wire['text']['format']['name'].removeprefix('rsm_')
                    kinds.append(kind)
                    fixture.now[0] += 17
                    business = copy.deepcopy(wire)
                    business['input'] = [i for i in business['input'] if i.get('type') != 'reasoning'
                        and i.get('phase') != 'commentary']
                    for i in business['input']:
                        if i.get('type') == 'message':
                            i['content'] = ''.join(p['text'] for p in i['content'])
                    response = http(json.dumps(business), deadline_ms=deadline_ms)
                    response['body'].pop('usage')
                    response['body']['output'].insert(0, reasoning())
                    if kind == 'dispatch':
                        item = response['body']['output'][-1]
                        item.update(role='assistant', phase='final_answer', status='completed')
                        if failure == 'JSON':
                            item['content'][0]['text'] = '{"kind":PUBLIC broken'
                        elif failure == 'contract':
                            obj = json.loads(item['content'][0]['text'])
                            obj['data']['claim_ids'] = ['c2', 'c1']
                            item['content'][0]['text'] = json.dumps(obj)
                        response['body']['output'].insert(1, message('PUBLIC progress', 'commentary'))
                    return response
                model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
                    'engineering_authorization': GRANT, 'execution_authorized': True, 'pricing': None})
                run = fixture.make('S', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                    'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                    'authorization_id': GRANT, 'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
                limits = dict.fromkeys(SEngineeringBudget.resources, 100)
                limits.update(model_calls=12, request_output_tokens=91612, elapsed_ms=1643819, retries=0)
                reserve = dict.fromkeys(SEngineeringBudget.resources, 0)
                reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=145000)
                budget = SEngineeringBudget(run.binding, limits, reserve, clock=lambda: fixture.now[0],
                    journal_path=Path(tmp) / 'PUBLIC-budget.jsonl')
                run.budget = run.evidence.root_budget = model.root_budget = budget
                result = run.run()
                checkpoint = json.loads((run.output_root / 'dispatch-checkpoint.json').read_bytes())
                self.assertEqual(checkpoint['passed'], failure is None)
                self.assertEqual(checkpoint['business_output']['items'][-1]['item']['phase'], 'final_answer')
                self.assertLessEqual((run.output_root / 'dispatch-checkpoint.json').stat().st_size, 100 * 1024)
                self.assertEqual(kinds.count('dispatch'), 1)
                self.assertEqual(kinds[:3], ['analysis', 'analysis', 'dispatch'])
                self.assertEqual(len(kinds), 9 if failure is None else 3)
                self.assertEqual(result['terminal'], 'released' if failure is None else
                    'failed_model' if failure == 'JSON' else 'failed_protocol')
                self.assertIsNone(result['budget']['usage']['input_tokens'])
                self.assertIsNone(result['budget']['usage']['cost_microusd'])
                run.run()
                self.assertEqual(len(kinds), 9 if failure is None else 3)
                for private in ('PUBLIC INTERNAL REASONING', 'PUBLIC-OPAQUE-CIPHERTEXT'):
                    self.assertNotIn(private, json.dumps(checkpoint))
