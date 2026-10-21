"""PUBLIC limit/marker fixtures; D1 is assembled only without HTTP or Key reads."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_p1_s_engineering import setUpModule

ROOT = Path(__file__).resolve().parents[1]
GRANT = 'S-COMPLETE-ONCE-20261021-A5'
RUN = 'P1-D1-V00-S-' + GRANT


def control_module():
    spec = importlib.util.spec_from_file_location('PUBLIC_A5_control',
        ROOT / '.scratch/ticket14-s-120-20261021/control.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A5(unittest.TestCase):
    def test_old_claim_markers_still_refuse_reuse_and_execution_time_keeps_all_attempts(self):
        spec = importlib.util.spec_from_file_location('PUBLIC_existing_S',
            ROOT / '.scratch/ticket14-s-engineering-20261020/run_once.py')
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as tmp:
            root = Path(tmp)
            for marker in ('execution-claim.json', 'execution-result.json', 'execution-resources.jsonl'):
                (root / marker).write_text('{}')
                with self.assertRaises(FileExistsError):
                    entry.ensure_first_execution(root, root / 'PUBLIC-attempt.json')
                (root / marker).unlink()
            (root / 'PUBLIC-attempt.json').write_text('{}')
            with self.assertRaises(FileExistsError):
                entry.ensure_first_execution(root, root / 'PUBLIC-attempt.json')
            for attempt, seconds in (('A1', 15), ('A2', 16), ('A3', 15), ('A4', 44), ('A5', 10)):
                (root / attempt).mkdir()
                (root / attempt / 'execution-resources.jsonl').write_text(json.dumps({'seconds': seconds}) + '\n')
            self.assertEqual(control_module().execution_used(root), 100)

    def test_real_1493_A5_preflight_and_actual_send_chain_are_fixture_only(self):
        import p1_runtime as p1
        from tests.test_p1_s_deadline import AdvancingClock
        from recommendation_runner import RunStop
        cfg = json.loads((ROOT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
        cfg['authorization_id'] = cfg['model_binding']['engineering_authorization'] = GRANT
        cfg['limits']['S'].update(model_calls=12, request_output_tokens=91612, elapsed_ms=1689869)
        cfg['final_reserve']['S']['elapsed_ms'] = 145000
        cfg.update(storage_limit_bytes=128 * 1024**2, run_storage_limit_bytes=64 * 1024**2)
        parent = ROOT / '.tmp/recommendation-runtime/PUBLIC-A5'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            root = Path(tmp)
            path = root / 'PUBLIC.config.json'
            path.write_text(json.dumps(cfg))
            admission_guard = p1.P1StorageGuard(p1.OUTPUT, 128 * 1024**2,
                run_root=p1.OUTPUT / RUN, run_limit_bytes=64 * 1024**2)
            self.assertEqual(p1.prepare_p1(path, 'S', storage_guard=admission_guard)['terminal'], 'ready')
            for key, value in (('model_calls', 13), ('request_output_tokens', 91613), ('elapsed_ms', 1689870)):
                bad = copy.deepcopy(cfg)
                bad['limits']['S'][key] = value
                path.write_text(json.dumps(bad))
                self.assertEqual(p1.prepare_p1(path, 'S', storage_guard=admission_guard)['terminal'], 'not_started')
            path.write_text(json.dumps(cfg))
            self.assertIn('A5_run_storage_guard', p1.prepare_p1(path, 'S',
                storage_guard=p1.P1StorageGuard(p1.OUTPUT, 128 * 1024**2))['missing'])
            with p1.P1StorageGuard(root, 128 * 1024**2, run_root=root / RUN,
                    run_limit_bytes=64 * 1024**2) as guard:
                assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={'run_id': RUN})
                run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=root)
                run._preflight()
                self.assertEqual(len(run.binding['C']), 1493)
                self.assertEqual(run.budget.usage['model_calls'], 0)
                clock = AdvancingClock()
                run.budget.clock, run.budget.started = clock, clock()
                calls = []
                def sentinel(text, *, deadline_ms):
                    from fourrouter_probe import _request_bytes
                    wire = json.loads(text)
                    frame = json.loads(wire['input'][-1]['content'])['runtime']
                    self.assertEqual(len(frame['candidate_batches']), 1493)
                    self.assertLessEqual(len(_request_bytes(wire, 2 * 1024**2)), 2 * 1024**2)
                    calls.append(deadline_ms)
                    raise OSError('PUBLIC_fixture_transport_sentinel')
                run.model.transport = sentinel
                with self.assertRaises(RunStop):
                    run._role('需求解析', 'analysis', '需求解析')
                self.assertEqual(len(calls), 1)
                self.assertEqual(guard.allowed['credentials'], 0)
                self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})
                self.assertEqual(run.budget.final_reserve['model_calls'], 1)
                self.assertEqual(run.budget.final_reserve['request_output_tokens'], 1500)
                self.assertEqual(run.budget.final_reserve['elapsed_ms'], 145000)

    def test_storage_enforces_shared_and_run_quota_without_touching_old_evidence(self):
        from p1_storage import P1StorageGuard
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as tmp:
            root = Path(tmp)
            expanded = P1StorageGuard(root, 128 * 1024**2, run_root=root / 'PUBLIC-A5', run_limit_bytes=64 * 1024**2)
            self.assertEqual(expanded.limit_bytes, 128 * 1024**2)
            old = root / 'PUBLIC-old.bin'
            old.write_bytes(b'x' * 15)
            guard = P1StorageGuard(root, 30, run_root=root / 'PUBLIC-A5', run_limit_bytes=10)
            with guard:
                (root / 'PUBLIC-A5').mkdir()
                (root / 'PUBLIC-A5/new.bin').write_bytes(b'y' * 8)
                with self.assertRaises(OSError):
                    with (root / 'PUBLIC-A5/new.bin').open('ab') as stream:
                        stream.write(b'zzz')
                with self.assertRaises(OSError):
                    (root / 'PUBLIC-other.bin').write_bytes(b'w' * 8)
            self.assertEqual(guard.charged_bytes, 23)
            self.assertEqual(guard.run_charged_bytes, 8)
            self.assertEqual(old.read_bytes(), b'x' * 15)

    def test_A5_retains_five_old_claims_and_enforces_both_new_limits(self):
        control = control_module()
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as tmp:
            ledger = Path(tmp) / 'PUBLIC-requests.jsonl'
            original = ''.join(json.dumps({'run_id': 'PUBLIC-old', 'sequence': i + 1,
                'output_cap': 8192}) + '\n' for i in range(5)).encode()
            ledger.write_bytes(original)
            for _ in range(11):
                control.claim_request(ledger, {'model': 'gpt-6-luna', 'max_output_tokens': 8192}, RUN)
            with self.assertRaises(OSError):
                control.claim_request(ledger, {'model': 'gpt-6-luna', 'max_output_tokens': 8192}, RUN)
            control.claim_request(ledger, {'model': 'gpt-6-luna', 'max_output_tokens': 1500}, RUN)
            with self.assertRaises(OSError):
                control.claim_request(ledger, {'model': 'gpt-6-luna', 'max_output_tokens': 1}, RUN)
            self.assertTrue(ledger.read_bytes().startswith(original))
            rows = control.requests(ledger)
            self.assertEqual(len(rows), 17)
            self.assertEqual(sum(r['output_cap'] for r in rows), 132572)

