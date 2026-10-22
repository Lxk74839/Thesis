"""Formal public seams. No supplier network, credentials or private test labels."""
import json
from pathlib import Path
import tempfile
import unittest


def setUpModule():
    from tests.test_p1_wiring import setUpModule as offline_boundary
    offline_boundary()


class FormalPreparation(unittest.TestCase):
    def test_task_key_resolves_original_test_user_without_creating_requests(self):
        from formal_runtime import prepare_task, PLAN, PLAN_ID
        from experiment_runner import _task_plan
        _, _, rows = _task_plan(PLAN)
        key = rows['tasks.jsonl'][1]['task_key']
        ready = prepare_task(key, validate_code=False)
        self.assertEqual(ready['assembly']['plan_id'], PLAN_ID)
        self.assertEqual(ready['assembly']['binding']['plan_source_scope'], 'accepted_test_pool')
        self.assertFalse(ready['started'])
        self.assertEqual(ready['provider_requests_sent'], 0)
        self.assertNotIn('development_authorization', ready['assembly']['binding'])
        with self.assertRaisesRegex(ValueError, 'unknown_or_duplicate_task_key'):
            prepare_task('7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874', validate_code=False)

    def test_formal_run_reaches_production_prepare_invoke_and_keeps_model_failure(self):
        from formal_runtime import prepare_task, PLAN
        from experiment_runner import _task_plan
        from p1_runtime import build_runtime
        _, _, rows = _task_plan(PLAN)
        key = rows['tasks.jsonl'][1]['task_key']
        ready = prepare_task(key, validate_code=False)
        parent = Path(__file__).resolve().parents[1] / '.tmp/recommendation-runtime'
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            run = build_runtime(ready['assembly'], ready['configuration'], 'S', counter=None, output_root=Path(tmp))
            calls = []
            def supplier_failure(wire, *, deadline_ms):
                calls.append(json.loads(wire))
                return {'http_status': 503, 'body': {}}
            run.model.transport = supplier_failure
            result = run.run()
            self.assertEqual(result['terminal'], 'failed_model', result.get('reason'))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]['model'], 'gpt-6-luna')
            self.assertEqual(result['release_scope'], 'formal_test100')
            self.assertEqual(result['binding']['task_key'], key)
            self.assertNotIn('pilot_id', result['binding'])

    def test_formal_Q_uses_actual_tools_profiles_and_one_anchor_with_a_fixture_supplier(self):
        from formal_runtime import prepare_task, PLAN
        from experiment_runner import _task_plan
        from p1_runtime import build_runtime
        from tests.test_p1_wiring import RouterHTTPFixture
        _, _, rows = _task_plan(PLAN)
        scene = next(s for s in rows['scenes.jsonl'] if s['label'] == 'Q1')
        links = {b['binding_id'] for b in rows['user-scenarios.jsonl'] if b['view_id'] == scene['view_id']}
        key = next(t['task_key'] for t in rows['tasks.jsonl'] if t['binding_id'] in links)
        ready = prepare_task(key, validate_code=False)
        http = RouterHTTPFixture()
        def supplier(wire, *, deadline_ms):
            body = json.loads(wire)
            frame = json.loads(body['input'][-1]['content'])['runtime'] if 'role' in body['input'][-1] else None
            envelope = http(wire, deadline_ms=deadline_ms)
            output = envelope['body']['output'][0]
            if frame and output['type'] == 'message':
                part = output['content'][0]
                reply = json.loads(part['text'])
                if frame['stage'] == '农产品画像' and isinstance(reply['data']['observations'], list):
                    reply['data']['observations'] = {o['candidate_id']: {k: v for k, v in o.items() if k != 'candidate_id'}
                        for o in reply['data']['observations']}
                if frame.get('bound_draft_contract'):
                    for item in reply['data']['items']:
                        bundle = next(k for k, row in frame['citation_catalog'].items()
                            if row['candidate_id'] == item['parent_asin'] and 'member_ids' in row)
                        for reason in item['reasons']:
                            reason['citations'] = [bundle]
                    reply['data'].update(frame['draft_identifiers'])
                part['text'] = json.dumps(reply, ensure_ascii=False)
            return envelope
        parent = Path(__file__).resolve().parents[1] / '.tmp/recommendation-runtime'
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            run = build_runtime(ready['assembly'], ready['configuration'], 'M', counter=None, output_root=Path(tmp))
            run.model.transport = supplier
            result = run.run()
            self.assertEqual(result['terminal'], 'released', result.get('reason'))
            self.assertEqual(len(http.wires), 16)
            self.assertEqual(len(result['G']), 32)
            self.assertEqual(set(result['roles_completed']), {'需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验'})
            anchors = [v['anchor_sha256'] for v in result['components'].values()]
            self.assertEqual(len(set(anchors)), 1)


class FormalContinuation(unittest.TestCase):
    def test_formal_sender_requires_the_granted_guard_before_reading_credentials(self):
        from provider_fourrouter import make_sender
        sender = make_sender(clock=lambda: 0, max_request_bytes=2 * 1024**2,
            formal_configuration_id='PUBLIC')
        with self.assertRaisesRegex(OSError, 'formal_sender_guard_required'):
            sender('{"model":"gpt-6-luna"}', deadline_ms=1000)

    def test_durable_send_intents_count_failures_and_resume_never_reissues_a_task(self):
        from formal_experiment import RunLedger
        tasks = [{'task_key': 'PUBLIC-A', 'uses_model': True}, {'task_key': 'PUBLIC-B', 'uses_model': True}]
        cfg = {'configuration_id': 'PUBLIC', 'run_model_calls': 2, 'generate_limit': 4}
        with tempfile.TemporaryDirectory() as tmp:
            ledger = RunLedger(Path(tmp), cfg, tasks)
            ledger.claim_task('PUBLIC-A')
            body = {'model': 'gpt-6-luna', 'max_output_tokens': 8192}
            ledger.claim_request('PUBLIC-A', body)
            ledger.finish_task('PUBLIC-A', {'terminal': 'failed_model'})
            with self.assertRaisesRegex(FileExistsError, 'task_already_claimed'):
                ledger.claim_task('PUBLIC-A')
            ledger.claim_task('PUBLIC-B')
            ledger.claim_request('PUBLIC-B', body)
            ledger.claim_request('PUBLIC-B', body)
            with self.assertRaisesRegex(OSError, 'generation_limit'):
                ledger.claim_request('PUBLIC-B', body)
            resumed = RunLedger(Path(tmp), cfg, tasks)
            resumed.recover_interrupted()
            self.assertEqual(resumed.status()['generations_reserved'], 3)
            self.assertEqual(resumed.status()['terminals'], {'failed_model': 1, 'unresolved_attempt': 1})
            self.assertEqual(resumed.pending(), [])

    def test_unconfirmed_session_cannot_start_or_read_labels(self):
        from formal_experiment import require_authorization, main
        from formal_runtime import load_config
        from p1_storage import P1StorageGuard
        self.assertEqual(main(['run']), 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(OSError, 'formal_start_confirmation_required'):
                require_authorization(load_config(validate_code=False), root / 'missing.json')
            for name in ('private', 'evaluation', 'joint-reference', 'sim-reference'):
                source = root / name / 'PUBLIC.json'
                source.parent.mkdir()
                if name != 'private':
                    source.write_text('{}')
            with P1StorageGuard(root / 'output', 128 * 1024**2, formal=True) as guard:
                for name in ('private', 'evaluation', 'joint-reference', 'sim-reference'):
                    with self.assertRaises(OSError):
                        (root / name / 'PUBLIC.json').read_bytes()
                self.assertEqual(guard.attempts['evaluation'], 3)  # private is denied by the outer offline hook first.


class FormalEvaluation(unittest.TestCase):
    def test_unsealed_failure_is_counted_without_fabricating_a_publication(self):
        from tests.test_live_integration import LiveIntegration, store
        from experiment_io import load_evaluation_inputs
        from experiment_evaluation import score_task, summarize
        case = LiveIntegration()
        case.setUp()
        try:
            sources = case.evaluation_sources()
            ref = store(case.root / 'failed-result.json', {'task_key': 'PUBLIC-TASK',
                'plan_id': case.manifest['plan_id'], 'started': True, 'terminal': 'failed_protocol',
                'run_id': 'PUBLIC', 'audit_path': None, 'usage': None})
            plan, observations = load_evaluation_inputs(case.plan, execution_index={'PUBLIC-TASK': ref}, reference_sources=sources)
            selected = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
            score = score_task(**selected)
            self.assertEqual((score['status'], score['secondary']['failure'], score['metrics']['10']['HR']), ('failed', 1, 0))
            summary = summarize(plan, [score_task(**o) for o in observations])
            self.assertEqual(summary['counts']['executed_failed'], 1)
        finally:
            case.tearDown()

    def test_formal_evaluation_rejects_a_public_plan_before_private_labels(self):
        from tests.test_live_integration import LiveIntegration
        from experiment_io import load_evaluation_inputs, _read, _public_path
        case = LiveIntegration()
        case.setUp()
        try:
            sources = case.evaluation_sources() | {'scope': 'accepted_formal_evaluation'}
            with self.assertRaisesRegex(ValueError, 'formal_evaluation_binding'):
                load_evaluation_inputs(case.plan, execution_index={}, reference_sources=sources,
                    read_artifact=_read, resolve_artifact=_public_path, formal=True)
        finally:
            case.tearDown()


class FormalProcess(unittest.TestCase):
    def test_job_contains_child_and_watchdog_ends_an_unresponsive_worker(self):
        import sys
        from formal_process import run_process
        parent = Path(__file__).resolve().parents[1] / '.tmp'
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            target = Path(tmp)
            okay = run_process([sys.executable, '-B', '-c',
                "import sys; assert sys.stdin.buffer.readline() == b'GO\\n'; print('PUBLIC')"],
                target / 'success.txt', cwd=parent, seconds=5, memory_bytes=256 * 1024**2)
            self.assertEqual(okay['exit_code'], 0)
            stopped = run_process([sys.executable, '-B', '-c',
                'import sys,time; sys.stdin.buffer.readline(); time.sleep(5)'],
                target / 'watchdog.txt', cwd=parent, seconds=.3, memory_bytes=256 * 1024**2)
            self.assertEqual((stopped['exit_code'], stopped['stop_reason']), (124, 'watchdog'))


if __name__ == '__main__':
    unittest.main()
