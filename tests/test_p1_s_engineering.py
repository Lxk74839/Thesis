"""Only PUBLIC execution; real D1 assembly/preflight never invokes a model."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import p1_runtime as p1

PACKAGE = p1.PROJECT / '.scratch/ticket14-s-engineering-20261020'


def setUpModule():
    def offline(event, args):
        if event.startswith(('socket.', 'http.client.', 'subprocess.')):
            raise OSError('R_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            parts = {p.lower() for p in Path(os.fsdecode(args[0])).parts}
            if parts & {'.secrets', 'private', 'evaluation', 'gold'}:
                raise OSError('R_credentials_forbidden' if '.secrets' in parts else 'R_evaluation_forbidden')
    sys.addaudithook(offline)


class SEngineering(unittest.TestCase):
    def test_model_mismatch_and_malformed_usage_stop_after_first_attempt(self):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget, AUTHORIZATION
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-engineering-tests'
        parent.mkdir(parents=True, exist_ok=True)
        for failure in ('model', 'usage', 'http'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(dir=parent) as tmp:
                fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
                http = RouterHTTPFixture()
                def broken(text, **kwargs):
                    reply = http(text, **kwargs)
                    if failure == 'http':
                        reply['http_status'] = 302
                    else:
                        reply['body'][failure] = 'OTHER' if failure == 'model' else {'input_tokens': -1}
                    return reply
                model = ModelAdapter(broken, capability_binding=FIXTURE_BINDING | {
                    'engineering_authorization': AUTHORIZATION, 'execution_authorized': True, 'pricing': None})
                run = fixture.make('S', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                    'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                    'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
                cfg = json.loads((PACKAGE / 's.config.json').read_bytes())
                budget = SEngineeringBudget(run.binding, cfg['limits']['S'], cfg['final_reserve']['S'],
                    clock=lambda: fixture.now[0], journal_path=Path(tmp) / 'engineering-budget.jsonl')
                run.budget = run.evidence.root_budget = model.root_budget = budget
                result = run.run()
                self.assertEqual(result['terminal'], 'failed_model')
                self.assertEqual(len(http.wires), 1)
                self.assertIsNone(result['publication_path'])

    def test_real_1493_S_nonexecuting_preflight_and_precise_source(self):
        from recommendation_runner import RunStop
        from p1_engineering import AUTHORIZATION
        cfg = json.loads((PACKAGE / 's.config.json').read_bytes())
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-engineering-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            with p1.P1StorageGuard(tmp, 64 * 1024**2) as guard:
                assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={
                    'run_id': 'P1-D1-V00-S-' + AUTHORIZATION})
                run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=Path(tmp))
                with patch.object(run, 'run', side_effect=AssertionError('nonexecuting')):
                    run._preflight()
                self.assertEqual(len(run.binding['C']), 1493)
                self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})
                self.assertEqual(run.budget.usage['model_calls'], 0)
                for key, value in (('authorization_id', 'R-FROZEN-RETRY-20261020'),
                        ('view_id', 'q-other'), ('task_key', p1.TASK_KEYS['M'])):
                    changed = copy.deepcopy(run.binding)
                    changed[key] = value
                    self.assertIsNotNone(p1.frozen_snapshot_error(changed, assembly['snapshot_ref']))

    def test_engineering_budget_reserves_final_call_and_output_capacity(self):
        from p1_engineering import SEngineeringBudget
        cfg = json.loads((PACKAGE / 's.config.json').read_bytes())
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-engineering-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            binding = {'method': 'S', 'run_id': 'PUBLIC-budget', 'root_task_id': 'PUBLIC-root',
                'fixture': 'public_runtime_adapter'}
            budget = SEngineeringBudget(binding, cfg['limits']['S'], cfg['final_reserve']['S'],
                clock=lambda: 0, journal_path=Path(tmp) / 'budget.jsonl')
            for n in range(11):
                hold = budget.reserve({'kind': 'model'}, {'model_calls': 1, 'request_output_tokens': 8192}, phase='work', retry_of=None)
                self.assertEqual(hold['status'], 'reserved')
                budget.settle(hold['reservation_id'], {'status': 'ok', 'usage': {'model_calls': 1}})
            denied = budget.reserve({'kind': 'model'}, {'model_calls': 1, 'request_output_tokens': 8192}, phase='work', retry_of=None)
            self.assertEqual(denied['status'], 'budget_exhausted')
            final = budget.reserve({'kind': 'model'}, {'model_calls': 1, 'request_output_tokens': 1500}, phase='final', retry_of=None)
            self.assertEqual(final['status'], 'reserved')
            budget.settle(final['reservation_id'], {'status': 'ok', 'usage': {'model_calls': 1}})
            self.assertEqual(budget.usage['model_calls'], 12)
            self.assertEqual(budget.usage['request_output_tokens'], 91612)
            self.assertIsNone(budget.audit_view()['usage']['output_tokens'])

    def test_guard_opens_only_authorized_credential_and_exact_sender_worker(self):
        from p1_engineering import AUTHORIZATION
        guard = p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2)
        guard.active = True
        key_path = p1.PROJECT / '.secrets/4router.json'
        with self.assertRaises(OSError):
            guard._audit('open', (str(key_path), 'r', 0))
        guard.authorize_S(AUTHORIZATION)
        with self.assertRaises(OSError):
            guard._audit('socket.connect', ())
        guard.credential_read = key_path
        guard._audit('open', (str(key_path), 'r', 0))  # audit only; never open/read the file
        with self.assertRaises(OSError):
            guard._audit('open', (str(p1.PROJECT / '.secrets/other.json'), 'r', 0))
        with self.assertRaises(OSError):
            guard._audit('open', (str(p1.PROJECT / 'data/private/evaluation.jsonl'), 'r', 0))
        guard.sender_active = True
        command = [sys.executable, '-B', str(p1.PROJECT / 'fourrouter_probe.py'), '_http_once']
        guard._audit('subprocess.Popen', (sys.executable, command, None, None))
        with self.assertRaises(OSError):
            guard._audit('subprocess.Popen', (sys.executable, ['other'], None, None))
        guard.active = False

    def test_PUBLIC_without_usage_completes_original_S_with_unknown_metering(self):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.test_p1_wiring import FIXTURE_BINDING, RouterHTTPFixture
        from model_adapter import ModelAdapter
        from p1_engineering import SEngineeringBudget, AUTHORIZATION
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-engineering-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp)).candidates(['PUBLIC-A', 'PUBLIC-B'])
            http = RouterHTTPFixture()
            def absent(text, **kwargs):
                result = http(text, **kwargs)
                result['body'].pop('usage')
                return result
            cap = FIXTURE_BINDING | {'engineering_authorization': AUTHORIZATION,
                'execution_authorized': True, 'pricing': None}
            model = ModelAdapter(absent, capability_binding=cap)
            run = fixture.make('S', model=model, binding_changes={'schema_version': 'rsm-run-0.4.0',
                'execution_kind': 'fourrouter_responses', 'project_id': 'PUBLIC-P1',
                'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
            cfg = json.loads((PACKAGE / 's.config.json').read_bytes())
            budget = SEngineeringBudget(run.binding, cfg['limits']['S'], cfg['final_reserve']['S'],
                clock=lambda: fixture.now[0], journal_path=Path(tmp) / 'engineering-budget.jsonl')
            run.budget = run.evidence.root_budget = model.root_budget = budget
            result = run.run()
            self.assertEqual(result['terminal'], 'released', result.get('reason'))
            self.assertEqual(len(http.wires), 9)
            self.assertFalse(result['budget']['usage_exact'])
            self.assertIsNone(result['budget']['usage']['input_tokens'])
            self.assertIsNone(result['budget']['usage']['cost_microusd'])
            self.assertTrue(all(m['request']['count_receipt_id'] is None for m in result['messages']))
            self.assertEqual(result['messages'][-1]['request']['max_output_tokens'], 1500)
            self.assertTrue(all(m['response']['usage_diagnostic']['state'] == 'field_absent' for m in result['messages']))

    def test_exact_S_grant_needs_no_M_or_unknown_token_budget(self):
        cfg = json.loads((PACKAGE / 's.config.json').read_bytes())
        guard = p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2)
        ready = p1.prepare_p1(PACKAGE / 's.config.json', 'S', storage_guard=guard)
        self.assertEqual(ready['terminal'], 'ready', ready)
        self.assertIsNone(cfg['limits']['M'])
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-engineering-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            path = Path(tmp) / 'denied.json'
            for mutate in (
                lambda c: c.update(authorized_task_keys=[p1.TASK_KEYS['R']]),
                lambda c: c.update(authorization_id='OTHER'),
                lambda c: c['model_binding'].pop('engineering_authorization'),
                lambda c: c.update(execution_authorized=False),
            ):
                denied = copy.deepcopy(cfg)
                mutate(denied)
                path.write_text(json.dumps(denied), encoding='utf-8')
                with patch('p1_runtime.assemble_task', side_effect=AssertionError('assembly forbidden')):
                    result = p1.execute_p1(path, 'S', storage_guard=guard)
                self.assertEqual(result['terminal'], 'not_started')
                self.assertFalse(result['started'])
                self.assertEqual(result['provider_requests_sent'], 0)


if __name__ == '__main__':
    unittest.main()
