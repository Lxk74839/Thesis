"""PUBLIC fixtures with advancing time, never replayed private responses."""
import json
from pathlib import Path
import tempfile
import unittest
import importlib.util

from tests.test_p1_s_engineering import setUpModule

GRANT = 'S-COMPLETE-ONCE-20261021-A1'


class LongS(unittest.TestCase):
    def test_exact_new_grant_real_1493_preflight_is_nonexecuting(self):
        import p1_runtime as p1
        from evidence_access import PROJECT
        cfg = json.loads((PROJECT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
        cfg['authorization_id'] = cfg['model_binding']['engineering_authorization'] = GRANT
        cfg['limits']['S']['elapsed_ms'] = 1780000
        cfg['final_reserve']['S']['elapsed_ms'] = 145000
        parent = PROJECT / '.tmp/recommendation-runtime/PUBLIC-s120'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            with p1.P1StorageGuard(tmp, 64 * 1024**2) as guard:
                assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={
                    'run_id': 'P1-D1-V00-S-' + GRANT})
                run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=Path(tmp))
                run._preflight()
                self.assertEqual(len(run.binding['C']), 1493)
                self.assertEqual(run.budget.usage['model_calls'], 0)
                self.assertEqual(guard.allowed['credentials'], 0)
                self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})

    def test_two_attempts_cannot_reset_the_shared_12_call_ledger(self):
        from evidence_access import PROJECT
        spec = importlib.util.spec_from_file_location('S120_control', PROJECT / '.scratch/ticket14-s-120-20261021/control.py')
        control = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(control)
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as tmp:
            path = Path(tmp) / 'PUBLIC-requests.jsonl'
            for n in range(12):
                control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1500},
                    'PUBLIC-A1' if n < 3 else 'PUBLIC-A2')
            with self.assertRaises(OSError):
                control.claim_request(path, {'model': 'gpt-6-luna', 'max_output_tokens': 1500}, 'PUBLIC-A2')
            self.assertEqual(len(control.requests(path)), 12)

    def test_original_S_returns_after_45_seconds_without_old_30_second_cutoff(self):
        result, windows = self.run_with_delay(45000)
        self.assertEqual(result['terminal'], 'released', result.get('reason'))
        self.assertEqual(len(windows), 9)
        self.assertTrue(all(45000 < window <= 120000 for window in windows))
        self.assertEqual(result['messages'][-1]['request']['max_output_tokens'], 1500)

    def test_expired_120_second_response_stops_without_retry(self):
        result, windows = self.run_with_delay(120001)
        self.assertEqual(result['terminal'], 'incomplete_deadline')
        self.assertEqual(len(windows), 1)
        self.assertIsNone(result['publication_path'])

    def test_sender_receives_120_seconds_and_expired_send_is_rejected(self):
        from evidence_access import PROJECT
        from provider_fourrouter import make_sender
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp') as tmp:
            credential = Path(tmp) / 'PUBLIC-credential.json'
            credential.write_text('{"api_key":"PUBLIC-ONLY"}')
            now, calls = [1000], []
            def http(endpoint, request, key, timeout, **kwargs):
                calls.append(timeout)
                now[0] += 45000
                return {'http_status': 200, 'body': None}
            sender = make_sender(clock=lambda: now[0], max_request_bytes=2097152,
                credential_path=credential, http_sender=http, http_timeout_seconds=120)
            sender('{"model":"gpt-6-luna"}', deadline_ms=121000)
            self.assertEqual(calls, [120])
            with self.assertRaises(TimeoutError):
                sender('{"model":"gpt-6-luna"}', deadline_ms=now[0] - 1)
            self.assertEqual(len(calls), 1)

    def run_with_delay(self, delay):
        from evidence_access import PROJECT
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget
        parent = PROJECT / '.tmp/recommendation-runtime/PUBLIC-s120'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
            fixture.now[0] = 10000
            http, windows = RouterHTTPFixture(), []
            def transport(text, *, deadline_ms):
                windows.append(deadline_ms - fixture.now[0])
                fixture.now[0] += delay
                return http(text, deadline_ms=deadline_ms)
            model = ModelAdapter(transport, capability_binding=FIXTURE_BINDING | {
                'engineering_authorization': GRANT, 'execution_authorized': True, 'pricing': None})
            run = fixture.make('S', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                'authorization_id': GRANT, 'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
            cfg = json.loads((PROJECT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
            cfg['limits']['S']['elapsed_ms'] = 1780000
            cfg['final_reserve']['S']['elapsed_ms'] = 145000
            budget = SEngineeringBudget(run.binding, cfg['limits']['S'], cfg['final_reserve']['S'],
                clock=lambda: fixture.now[0], journal_path=Path(tmp) / 'long-budget.jsonl')
            run.budget = run.evidence.root_budget = model.root_budget = budget
            result = run.run()
            return result, windows

