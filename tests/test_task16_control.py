"""Public control contract; no provider, private labels or algorithm mocks."""
import hashlib
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
TEMP = PROJECT / '.tmp/task16-execution'


class IndependentControl(unittest.TestCase):
    def wait_launcher(self, pid):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
        kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
        handle = kernel.OpenProcess(0x100000, False, pid)
        if handle:
            try:
                self.assertEqual(kernel.WaitForSingleObject(handle, 15000), 0)
            finally:
                kernel.CloseHandle(handle)

    def setUp(self):
        TEMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEMP)
        self.directory = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.budget = {'schema': 'task16-shared-budget/1', 'started_at_utc': time.time() - 5,
            'deadline_utc': time.time() + 100, 'dispatch_deadline_utc': time.time() + 80,
            'max_hours': 24, 'max_new_bytes': 10 * 1024**3, 'max_calls': 6944,
            'api_authorized': False, 'input_CNY_per_M': .045, 'output_CNY_per_M': .225}
        (self.directory / 'budget.json').write_text(json.dumps(self.budget), encoding='utf-8')

    def command(self, action, *args):
        result = subprocess.run([sys.executable, '-B', str(PROJECT / 'task16_control.py'), action,
            '--session', str(self.directory), *args], cwd=PROJECT, capture_output=True, text=True,
            encoding='utf-8', timeout=15)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result, json.loads(result.stdout)

    def fixture_plan(self, units):
        worker = self.directory / 'fixture_worker.py'
        worker.write_text('''import time
from pathlib import Path
def execute_unit(unit, session):
    started = time.time()
    time.sleep(unit.get("delay", 0))
    def send(body):
        if unit.get("crash_during_send"):
            raise SystemExit(9)
        if unit.get("uncertain"):
            raise TimeoutError("fixture timeout")
        return {"status":"completed", "output":["A"],
                "usage":{"input_tokens":100,"output_tokens":20}}
    reply = session.invoke({"input":unit["id"],"max_output_tokens":16}, send,
                           dependencies={"public_history":unit["root_id"]})
    marker = Path(__file__).with_suffix('.crashed')
    if unit.get("crash_after_success") and not marker.exists():
        marker.write_text('fixture crash after persisted response')
        raise SystemExit(9)
    return {"status":"ok", "reply":reply, "started":started, "finished":time.time()}
''', encoding='utf-8')
        def ref(path):
            return {'path': path.relative_to(PROJECT).as_posix(),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        plan = {'schema': 'task16-run-plan/1', 'kind': 'offline_fixture', 'namespace': 'fixture-v1',
            'worker': ref(worker), 'stages': [{'id': 'v00-main', 'category': 'model',
                'max_calls': 1184, 'units': units}]}
        plan_path = self.directory / 'run-plan.json'
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        reports = []
        for name in ('standards', 'spec'):
            report = self.directory / (name + '.md')
            report.write_text('PASS: offline public fixture only', encoding='utf-8')
            reports.append(ref(report) | {'axis': name, 'result': 'PASS'})
        seal = {'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            'code': [ref(PROJECT / 'task16_control.py')], 'reviews': reports}
        (self.directory / 'review-seal.json').write_text(json.dumps(seal), encoding='utf-8')

    def test_process_crash_after_success_reuses_reply_before_unit_was_saved(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37, 'crash_after_success': True}])
        _, stopped = self.command('start')
        self.assertEqual(stopped['status'], 'stopped')
        self.assertEqual(stopped['calls']['successful'], 1)
        self.assertEqual(stopped['progress']['completed_units'], 0)
        _, resumed = self.command('resume')
        self.assertEqual(resumed['status'], 'complete')
        self.assertEqual(resumed['calls']['attempts'], 1)

    def test_process_crash_during_send_leaves_intent_unresolved_after_resume(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37, 'crash_during_send': True}])
        _, stopped = self.command('start')
        self.assertEqual(stopped['calls']['attempts'], 1)
        _, resumed = self.command('resume')
        self.assertEqual(resumed['status'], 'blocked_unresolved')
        self.assertEqual(resumed['calls']['attempts'], 1)
        self.assertEqual(resumed['calls']['unresolved'], 1)
        self.assertEqual(resumed['progress']['unresolved_units'], 1)

    def test_uncertain_stage_finishes_other_roots_and_blocks_following_stages(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37, 'uncertain': True},
            {'id': 'u2-I1', 'root_id': 'u2', 'limit': 37}])
        plan_path = self.directory / 'run-plan.json'
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        plan['stages'].append({'id': 'q1', 'category': 'model', 'max_calls': 37,
            'units': [{'id': 'u1-Q1', 'root_id': 'u1', 'limit': 37}]})
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        seal_path = self.directory / 'review-seal.json'
        seal = json.loads(seal_path.read_text(encoding='utf-8'))
        seal['plan_sha256'] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        seal_path.write_text(json.dumps(seal), encoding='utf-8')
        _, stopped = self.command('start')
        self.assertEqual(stopped['status'], 'blocked_unresolved')
        self.assertEqual(stopped['calls']['attempts'], 2)
        self.assertEqual(stopped['progress']['completed_units'], 1)
        self.assertEqual(stopped['progress']['unresolved_units'], 1)
        _, resumed = self.command('resume')
        self.assertEqual(resumed['calls']['attempts'], 2)
        self.assertEqual(resumed['progress']['stages'][1]['completed'], 0)

    def test_second_start_cannot_replace_an_active_worker(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37, 'delay': 2}])
        command = [sys.executable, '-B', str(PROJECT / 'task16_control.py'), 'start',
            '--session', str(self.directory)]
        with subprocess.Popen(command, cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8') as running:
            for _ in range(50):
                _, state = self.command('status')
                if state.get('worker_active'):
                    break
                time.sleep(.05)
            original_worker = (self.directory / 'worker.json').read_bytes()
            self.command('start')
            self.assertEqual((self.directory / 'worker.json').read_bytes(), original_worker)
            running.communicate(timeout=15)
        _, state = self.command('status')
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['calls']['attempts'], 1)

    def test_changed_materials_get_a_new_request_identity(self):
        from task16_control import Session
        session = Session(self.directory, namespace='fixture', phase='v00-main', unit='u1', limit=37)
        sends = []

        def send(body):
            sends.append(body)
            return {'status': 'completed', 'usage': None}

        for version in (1, 1, 2):
            session.invoke({'input': 'same prompt'}, send, dependencies={'evidence_sha256': version})
        self.assertEqual(len(sends), 2)


    def test_two_roots_overlap_and_methods_within_each_root_remain_ordered(self):
        self.fixture_plan([{'id': root + '-' + method, 'root_id': root, 'limit': 37, 'delay': .3}
            for root in ('u1', 'u2') for method in ('B0', 'I1')])
        result, state = self.command('start')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(state['status'], 'complete')
        rows = [json.loads(p.read_text(encoding='utf-8'))['output']
            for p in (self.directory / 'units').glob('*.json') if not p.name.endswith('.receipt.json')]
        rows.sort(key=lambda row: row['started'])
        self.assertLess(rows[1]['started'], rows[0]['finished'])
        self.assertGreaterEqual(rows[2]['started'], rows[0]['finished'])
        self.assertEqual(state['calls']['attempts'], 4)

    def test_phase_limit_stops_other_roots_without_spending_remaining_global_budget(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37},
            {'id': 'u2-I1', 'root_id': 'u2', 'limit': 37}])
        plan_path = self.directory / 'run-plan.json'
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        plan['stages'][0]['max_calls'] = 1
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        seal_path = self.directory / 'review-seal.json'
        seal = json.loads(seal_path.read_text(encoding='utf-8'))
        seal['plan_sha256'] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        seal_path.write_text(json.dumps(seal), encoding='utf-8')
        self.command('start')
        _, state = self.command('status')
        self.assertEqual(state['calls']['attempts'], 1)
        self.assertLess(state['progress']['completed_units'], state['progress']['planned_units'])

    def test_status_separates_known_token_cost_unknown_usage_and_request_latency(self):
        from task16_control import Session
        session = Session(self.directory, namespace='fixture', phase='v00-main', unit='u1', limit=37)
        session.invoke({'input': 'known'}, lambda body: {'status': 'completed',
            'usage': {'input_tokens': 100, 'output_tokens': 20,
                'output_tokens_details': {'reasoning_tokens': 12}}}, dependencies={'v': 1})

        def unknown(body):
            raise TimeoutError('fixture only')

        with self.assertRaisesRegex(ValueError, 'task16_unresolved'):
            session.invoke({'input': 'unknown'}, unknown, dependencies={'v': 1})
        _, state = self.command('status')
        self.assertAlmostEqual(state['cost']['known_token_subtotal_CNY'], .000009)
        self.assertFalse(state['cost']['fully_known'])
        self.assertIsNone(state['cost']['cache_CNY_per_M'])
        self.assertIsNone(state['cost']['extra_multiplier'])
        self.assertEqual(state['usage']['unknown_requests'], 1)
        self.assertEqual(state['usage']['output_tokens'], 20)
        self.assertGreater(state['timing']['request_latency_sum_seconds'], 0)

    def test_status_rejects_a_changed_response_instead_of_reporting_complete(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37}])
        result, state = self.command('start')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(state['status'], 'complete')
        response = next((self.directory / 'calls').glob('*.response.json'))
        response.write_text('{"status":"completed","output":["changed"]}', encoding='utf-8')
        result, state = self.command('status')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(state['status'], 'rejected')
        self.assertEqual(state['reason'], 'task16_response_changed')

    def test_bounded_artifacts_reject_large_requests_and_preserve_large_reply_failure(self):
        from task16_control import Session
        session = Session(self.directory, namespace='fixture', phase='v00-main', unit='u1', limit=37)
        sends = []
        with self.assertRaisesRegex(ValueError, 'task16_request_size'):
            session.invoke({'input': 'x' * (128 * 1024)},
                lambda body: sends.append(body), dependencies={'v': 1})
        self.assertEqual(sends, [])
        with self.assertRaisesRegex(ValueError, 'task16_failed_reply_size'):
            session.invoke({'input': 'bounded'}, lambda body: {'status': 'completed',
                'output': 'x' * (256 * 1024), 'usage': {'input_tokens': 100, 'output_tokens': 20}},
                dependencies={'v': 1})
        _, state = self.command('status')
        self.assertEqual(state['calls']['attempts'], 1)
        self.assertEqual(state['calls']['failed'], 1)
        self.assertEqual(state['usage']['output_tokens'], 20)
        self.assertFalse(list((self.directory / 'calls').glob('*.response.json')))

    def test_staged_progress_survives_new_process_and_completed_units_are_reused(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37},
            {'id': 'u2-I1', 'root_id': 'u2', 'limit': 37}])
        original_budget = (self.directory / 'budget.json').read_bytes()
        result, state = self.command('start')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['progress']['completed_units'], 2)
        self.assertEqual(state['calls']['attempts'], 2)
        result, resumed = self.command('resume')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(resumed['status'], 'complete')
        self.assertEqual(resumed['calls']['attempts'], 2)
        self.assertEqual((self.directory / 'budget.json').read_bytes(), original_budget)

    def test_powershell_launcher_returns_while_worker_persists_and_is_queryable(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37, 'delay': 3}])
        script = PROJECT / '.scratch/task16-execution-v2-20261023/run-task16.ps1'
        launched = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script), '-Action', 'Start', '-SessionDir', str(self.directory)],
            capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(launched.returncode, 0, launched.stderr)
        launch = json.loads(launched.stdout)
        self.assertEqual(launch['status'], 'launched')
        self.addCleanup(self.wait_launcher, launch['supervisor_pid'])
        seen_running = False
        for _ in range(40):
            _, state = self.command('status')
            seen_running |= state.get('worker_active', False)
            if state['status'] == 'complete':
                break
            time.sleep(.1)
        self.assertTrue(seen_running)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['calls']['attempts'], 1)

    def test_stop_resume_preserves_completed_work_clock_and_waiting_time(self):
        self.fixture_plan([{'id': 'u1-B0', 'root_id': 'u1', 'limit': 37},
            {'id': 'u1-I1', 'root_id': 'u1', 'limit': 37, 'delay': 2}])
        original_budget = (self.directory / 'budget.json').read_bytes()
        command = [sys.executable, '-B', str(PROJECT / 'task16_control.py'), 'start',
            '--session', str(self.directory)]
        with subprocess.Popen(command, cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8') as running:
            for _ in range(60):
                _, state = self.command('status')
                if state.get('worker_active') and state['progress']['completed_units'] == 1:
                    break
                time.sleep(.05)
            result, stopping = self.command('stop')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(stopping['status'], 'stop_requested')
            running.communicate(timeout=15)
        _, paused = self.command('status')
        self.assertEqual(paused['progress']['completed_units'], 1)
        self.assertEqual(paused['calls']['attempts'], 1)
        time.sleep(.05)
        result, resumed = self.command('resume')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(resumed['status'], 'complete')
        self.assertEqual(resumed['calls']['attempts'], 2)
        self.assertGreater(resumed['timing']['model_seconds'], 0)
        self.assertGreater(resumed['timing']['waiting_seconds'], 0)
        self.assertEqual((self.directory / 'budget.json').read_bytes(), original_budget)

    def test_status_is_readonly_and_unimplemented_algorithm_is_not_ready(self):
        before = hashlib.sha256((self.directory / 'budget.json').read_bytes()).hexdigest()
        result, status = self.command('status')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(status['ready_for_live'])
        self.assertEqual(status['calls']['attempts'], 0)
        self.assertEqual(status['status'], 'not_ready')
        self.assertEqual(before, hashlib.sha256((self.directory / 'budget.json').read_bytes()).hexdigest())
        self.assertEqual({p.name for p in self.directory.iterdir()}, {'budget.json'})

    def test_successful_request_is_reused_by_a_new_session(self):
        from task16_control import Session
        sent = []

        def send(request):
            sent.append(request)
            return {'status': 'completed', 'output': ['A'],
                'usage': {'input_tokens': 100, 'output_tokens': 20}}

        first = Session(self.directory, namespace='fixture-v1', phase='b0-v00', unit='u1', limit=37)
        body = {'input': 'public history', 'max_output_tokens': 16}
        result = first.invoke(body, send, dependencies={'history': 'h1'})
        resumed = Session(self.directory, namespace='fixture-v1', phase='b0-v00', unit='u1', limit=37)
        self.assertEqual(resumed.invoke(body, send, dependencies={'history': 'h1'}), result)
        self.assertEqual(len(sent), 1)
        _, status = self.command('status')
        self.assertEqual(status['calls']['attempts'], 1)
        self.assertEqual(status['calls']['successful'], 1)

    def test_uncertain_send_remains_unresolved_and_resume_never_resends(self):
        from task16_control import Session
        session = Session(self.directory, namespace='fixture-v1', phase='b0-v00', unit='u1', limit=37)
        sent = []

        def timeout(request):
            sent.append(request)
            raise TimeoutError('private transport detail must not be persisted')

        body = {'input': 'public history', 'max_output_tokens': 16}
        with self.assertRaisesRegex(ValueError, 'task16_unresolved'):
            session.invoke(body, timeout, dependencies={'history': 'h1'})
        resumed = Session(self.directory, namespace='fixture-v1', phase='b0-v00', unit='u1', limit=37)
        with self.assertRaisesRegex(ValueError, 'unresolved_not_resent'):
            resumed.invoke(body, timeout, dependencies={'history': 'h1'})
        self.assertEqual(len(sent), 1)
        _, status = self.command('status')
        self.assertEqual(status['calls']['unresolved'], 1)

    def test_original_deadline_and_limits_reject_before_transport(self):
        from task16_control import Session
        for name, changes, unit_limit in (
                ('deadline', {'dispatch_deadline_utc': 1}, 37),
                ('calls', {'max_calls': 0}, 37),
                ('storage', {'max_new_bytes': 0}, 37),
                ('unit', {}, 0)):
            with self.subTest(name=name):
                directory = self.directory / name
                directory.mkdir()
                budget = self.budget | changes
                (directory / 'budget.json').write_text(json.dumps(budget), encoding='utf-8')
                session = Session(directory, namespace='fixture', phase='v00-main', unit='u1',
                    limit=unit_limit)
                sends = []
                with self.assertRaisesRegex(ValueError, 'task16_(dispatch_deadline|call_limit|storage_limit|unit_limit)'):
                    session.invoke({'input': name, 'max_output_tokens': 16},
                        lambda body: sends.append(body), dependencies={'history': 'public'})
                self.assertEqual(sends, [])
                self.assertFalse((directory / 'calls').exists())

    def test_returned_failure_is_terminal_and_never_retried_to_success(self):
        from task16_control import Session
        session = Session(self.directory, namespace='fixture', phase='v00-main', unit='u1', limit=37)
        sends = []

        def failed(request):
            sends.append(request)
            return {'status': 'failed', 'usage': None, 'error': 'public rejection'}

        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'task16_failed'):
                session.invoke({'input': 'public', 'max_output_tokens': 16}, failed,
                    dependencies={'history': 'h1'})
        self.assertEqual(len(sends), 1)
        _, state = self.command('status')
        self.assertEqual(state['calls']['failed'], 1)

    def test_start_and_resume_cannot_bypass_the_missing_algorithm_review_seal(self):
        for action in ('start', 'resume'):
            with self.subTest(action=action):
                result, state = self.command(action, '--confirm-live')
                self.assertEqual(result.returncode, 2)
                self.assertEqual(state['reason'], 'task16_live_not_ready')
                self.assertFalse((self.directory / 'calls').exists())
                self.assertFalse((self.directory / 'authorization.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
