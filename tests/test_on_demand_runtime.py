"""New on-demand public seams, using real local sessions and an external model double."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import os

from tests.runtime_fixtures import RuntimeFixture, ScriptedTransport
from tests.test_batched_recommendation import BatchTransport
from model_adapter import ModelAdapter
from token_counting import InputCounter
from tests.evidence_fixtures import EvidenceFixture, acquire_all

PROJECT = Path(__file__).resolve().parents[1]


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_plan(root, run, scope='public_fixture'):
    """One small dispatch plan; not a test100 planning result."""
    root.mkdir(parents=True, exist_ok=True)
    rows = {'tasks.jsonl': [{'task_key': 'PUBLIC-TASK', 'binding_id': 'PUBLIC-BINDING',
                            'method': run.binding['method'], 'repeat': 1, 'uses_model': run.binding['method'] != 'R'}],
        'user-scenarios.jsonl': [{'binding_id': 'PUBLIC-BINDING', 'root_task_id': 'PUBLIC-ROOT', 'view_id': 'PUBLIC-VIEW'}],
        'scenes.jsonl': [{'view_id': 'PUBLIC-VIEW', 'snapshot_id': run.binding['snapshot_id']} ]}
    components = {}
    for name, items in rows.items():
        raw = b''.join(wire(item) + b'\n' for item in items)
        (root / name).write_bytes(raw)
        components[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    plan = {'schema_version': 'ticket12-test100-on-demand-0.1.0', 'source_scope': scope,
        'components': components, 'execution_authorized': False,
        'model_binding': dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget'))}
    plan['plan_id'] = hashlib.sha256(wire(plan)).hexdigest()
    (root / 'plan.json').write_bytes(wire(plan) + b'\n')
    return root


def public_model(transport):
    counter = InputCounter('PUBLIC-ON-DEMAND', fixture_count=lambda prepared: len(wire({
        'messages': prepared['request']['messages'], 'tools': prepared['request']['tools']})))
    return ModelAdapter(transport, capability_binding={'execution_kind': 'on_demand_public',
        'model_id': None, 'provenance': 'fixture', 'project_id': 'PUBLIC-ON-DEMAND'}, counter=counter)


class DispatchBoundary(unittest.TestCase):
    def setUp(self):
        retain = os.environ.get('THESIS_ON_DEMAND_CASES')
        parent = Path(retain) if retain else PROJECT / '.tmp/recommendation-runtime'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=self._testMethodName + '-', dir=parent, delete=not bool(retain))
        if not retain:
            self.addCleanup(self.temp.cleanup)
        self.fixture = RuntimeFixture(self.temp.name)

    def make(self, method='R', model=None):
        return self.fixture.make(method, model=model, binding_changes={
            'schema_version': 'rsm-run-0.3.0', 'execution_kind': 'on_demand_public',
            'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})

    def test_public_rule_task_finishes_and_repeat_dispatch_reuses_terminal(self):
        from experiment_runner import run_task
        run = self.make()
        plan = write_plan(Path(self.temp.name) / 'plan', run)
        first = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        second = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual((first['terminal'], first['usage']['model_calls']), ('released', 0))
        self.assertEqual(second, first)
        self.assertEqual(first['delivered'], ['PUBLIC-A'])

    def test_real_scope_with_missing_configuration_never_reaches_an_injected_sender(self):
        from experiment_runner import run_task
        transport = ScriptedTransport()
        run = self.make('M', transport.adapter())
        plan = write_plan(Path(self.temp.name) / 'plan', run, scope='accepted_test_pool')
        result = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual(result['terminal'], 'configuration_required')
        self.assertEqual(set(result['missing']), {'model_id', 'channel', 'base_url', 'pricing', 'api_budget'})
        self.assertEqual(transport.requests, [])
        self.assertFalse((run.output_root / 'task.intent.json').exists())

    def test_M_constructs_only_actual_requests_with_no_old_model_default(self):
        from experiment_runner import run_task
        transport = BatchTransport()
        run = self.make('M', public_model(transport))
        plan = write_plan(Path(self.temp.name) / 'plan', run)
        result = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual((result['terminal'], result['usage']['model_calls']), ('released', 9))
        self.assertEqual(len(run.audit_view()['roles_completed']), 6)
        self.assertTrue(all(request['model_id'] is None for request in transport.requests))
        audit = json.loads(Path(result['audit_path']).read_bytes())
        self.assertEqual(len(audit['messages']), 9)
        self.assertTrue(all(set(message['request_ref']) == {'path', 'sha256', 'bytes'} for message in audit['messages']))
        self.assertTrue(all('messages' not in message.get('request', {}) for message in audit['messages']))
        self.assertEqual(len(list((run.output_root / 'trace').glob('request-*.json'))), 9)

    def test_fact_order_is_stable_when_the_model_reads_refs_in_reverse_order(self):
        def reverse_read(request, raw, context):
            for call in raw['message']['tool_requests']:
                if call['name'] == 'read_evidence':
                    call['arguments']['evidence_refs'].reverse()
        transport = ScriptedTransport(mutate=reverse_read)
        run = self.fixture.make('M', model=public_model(transport), binding_changes={
            'schema_version': 'rsm-run-0.3.0', 'execution_kind': 'on_demand_public',
            'plan_source_scope': 'public_fixture'})
        self.assertEqual(run.run()['terminal'], 'released')
        frames = [message['content']['runtime'] for request in transport.requests for message in request['messages']
                  if message['role'] == 'user' and isinstance(message['content'], dict) and 'runtime' in message['content']]
        frame = next(frame for frame in frames if frame['stage'] == '农产品画像')
        self.assertEqual([fact['citation']['target_id'] for fact in frame['facts']['PUBLIC-A']],
            ['BATCH-A', 'E-harvest', 'E-inspection', 'E-packaging', 'E-retail', 'E-storage', 'E-transport',
             'D-inspection_report', 'D-inspection_sample', 'D-retail_status'])

    def test_a_task_cannot_dispatch_another_roots_runtime(self):
        from experiment_runner import run_task
        run = self.make()
        run.binding['root_task_id'] = 'PUBLIC-OTHER-ROOT'
        plan = write_plan(Path(self.temp.name) / 'plan', run)
        with self.assertRaisesRegex(ValueError, 'public_task_binding_mismatch'):
            run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual(run.budget.audit_view()['usage']['model_calls'], 0)
        self.assertFalse((run.output_root / 'task.intent.json').exists())

    def test_known_retry_is_charged_to_the_same_root(self):
        def fail_once(request, raw, context):
            if request['attempt_id'].endswith(':0'):
                raw.update(finish_reason='error', error={'category': 'rate_limit'})
        transport = BatchTransport(mutate=fail_once)
        run = self.make('M', public_model(transport))
        result = run.run()
        self.assertEqual((result['terminal'], result['budget']['usage']['model_calls'],
                          result['budget']['usage']['retries']), ('released', 10, 1))
        self.assertEqual(len(transport.requests), 10)
        self.assertEqual(result['budget']['usage']['input_tokens'],
                         sum(message['response']['usage']['input_tokens'] for message in result['messages']))

    def test_unknown_usage_keeps_reservation_and_repeated_dispatch_does_not_retry(self):
        from experiment_runner import run_task
        def unknown(request, raw, context):
            raw['usage']['input_tokens'] = None
        transport = BatchTransport(mutate=unknown)
        run = self.make('M', public_model(transport))
        plan = write_plan(Path(self.temp.name) / 'plan', run)
        first = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual(first['terminal'], 'failed_model')
        self.assertEqual((first['usage']['model_calls'], first['usage']['retries']), (1, 0))
        self.assertGreater(run.audit_view()['budget']['held']['input_tokens'], 0)
        self.assertEqual(run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root), first)
        self.assertEqual(len(transport.requests), 1)

    def test_count_drift_preserves_raw_usage_and_stops_unsettled(self):
        def drift(request, raw, context):
            raw['usage']['input_tokens'] -= 1
        transport = BatchTransport(mutate=drift)
        run = self.make('M', public_model(transport))
        result = run.run()
        self.assertEqual((result['terminal'], len(transport.requests)), ('failed_model', 1))
        self.assertEqual(result['messages'][0]['response']['status'], 'usage_mismatch')
        self.assertGreater(result['budget']['held']['input_tokens'], 0)
        self.assertEqual(result['messages'][0]['response']['usage']['input_tokens'],
                         transport.requests[0]['input_token_upper_bound'] - 1)

    def test_prepared_identity_survives_JSON_reload_in_another_process(self):
        model = public_model(BatchTransport())
        request = {'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': 'on_demand_public',
            'request_id': 'PUBLIC-REQ', 'attempt_id': 'PUBLIC-REQ', 'run_id': 'PUBLIC-RUN',
            'session_id': 'PUBLIC-SESSION', 'role': '需求解析', 'reply_to': None, 'model_id': None,
            'messages': [{'role': 'user', 'content': {'z': 1, 'facts': [{'a': 1, 'b': 2}]}}],
            'tools': [], 'output_kind': 'analysis', 'output_schema': {'type': 'object', 'properties': {}},
            'max_output_tokens': 100}
        prepared = model.prepare(request)
        code = ('import json,sys; from model_adapter import ModelAdapter; '
            'm=ModelAdapter(None,capability_binding={"execution_kind":"on_demand_public","model_id":None,'
            '"provenance":"fixture","project_id":"PUBLIC-ON-DEMAND"}); '
            'print(m.prepare(json.load(sys.stdin))["prepared_id"])')
        child = subprocess.run([sys.executable, '-B', '-c', code], input=wire(request),
                               capture_output=True, cwd=PROJECT, check=True)
        self.assertEqual(child.stdout.decode().strip(), prepared['prepared_id'])
        request['messages'][0]['content']['z'] = 2
        self.assertNotEqual(model.prepare(request)['prepared_id'], prepared['prepared_id'])

    def test_ordinary_work_cannot_consume_the_final_model_reserve(self):
        transport = BatchTransport()
        run = self.fixture.make('M', model=public_model(transport), limits={'model_calls': 8}, binding_changes={
            'schema_version': 'rsm-run-0.3.0', 'execution_kind': 'on_demand_public',
            'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
        result = run.run()
        self.assertEqual((result['terminal'], result['budget']['usage']['model_calls']), ('incomplete_budget', 7))
        self.assertEqual(len(transport.requests), 7)
        self.assertFalse((run.output_root / 'publication.json').exists())

    def test_independent_check_accepts_a_nonempty_null_scope_but_rejects_missing_original(self):
        self.fixture.facts.revise('pass')
        run = self.make()
        result = run.run()
        self.assertEqual(result['terminal'], 'released')
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py'
        command = [sys.executable, '-B', str(checker), 'audit', result['audit_path']]
        checked = subprocess.run(command, cwd=PROJECT, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stdout.decode() + checked.stderr.decode())
        self.assertGreater(json.loads(checked.stdout)['null_scopes'], 0)
        broken = json.loads(Path(result['audit_path']).read_bytes())
        broken['evidence']['acquired']['candidates']['PUBLIC-A']['originals']['PUBLIC-MISSING'] = {'raw_utf8': None}
        bad_path = run.output_root / 'bad-audit.json'
        bad_path.write_bytes(wire(broken))
        rejected = subprocess.run([sys.executable, '-B', str(checker), 'audit', str(bad_path)],
                                  cwd=PROJECT, capture_output=True)
        self.assertEqual(rejected.returncode, 2)

    def test_quality_components_share_one_M_anchor_without_extra_model_work(self):
        self.fixture.quality()
        transport = BatchTransport()
        run = self.fixture.make('M', model=public_model(transport), arm='quality', prefix=2, binding_changes={
            'schema_version': 'rsm-run-0.3.0', 'execution_kind': 'on_demand_public',
            'plan_source_scope': 'public_fixture', 'orchestration': 'batch32-0.1.0'})
        result = run.run()
        self.assertEqual((result['terminal'], result['budget']['usage']['model_calls']), ('released', 9))
        self.assertEqual(set(result['components']), {'full', 'no_quality', 'mean_quality'})
        anchors = [component['anchor_sha256'] for component in result['components'].values()]
        self.assertEqual(len(set(anchors)), 1)
        self.assertEqual(result['components']['full']['anchor']['G'], result['G'])

    def test_S_and_M_keep_distinct_root_accounts_and_the_same_public_information(self):
        observations = []
        for method in ('S', 'M'):
            transport = BatchTransport()
            run = self.make(method, public_model(transport))
            result = run.run()
            self.assertEqual((result['terminal'], result['budget']['usage']['model_calls']), ('released', 9))
            self.assertEqual({request['role'] for request in transport.requests},
                             {'单智能体'} if method == 'S' else {'需求解析', '用户画像', '推荐管理', '生命周期追溯', '农产品画像', '推荐依据核验'})
            observations.append(result)
        self.assertEqual(observations[0]['G'], observations[1]['G'])
        self.assertEqual(observations[0]['binding']['C'], observations[1]['binding']['C'])
        self.assertEqual(set(observations[0]['budget']['reservations']) & set(observations[1]['budget']['reservations']), set())

    def test_an_unfinished_dispatch_intent_stops_before_any_model_or_evidence_work(self):
        from experiment_runner import run_task
        transport = BatchTransport()
        run = self.make('M', public_model(transport))
        plan = write_plan(Path(self.temp.name) / 'plan', run)
        manifest = json.loads((plan / 'plan.json').read_bytes())
        (run.output_root / 'task.intent.json').write_bytes(wire({'task_key': 'PUBLIC-TASK', 'plan_id': manifest['plan_id']}))
        result = run_task(plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root)
        self.assertEqual(result['terminal'], 'unresolved_attempt')
        self.assertEqual(transport.requests, [])
        self.assertEqual(run.audit_view()['budget']['usage']['physical_tools'], 0)

    def test_actual_requests_retain_the_prepared_output_schema(self):
        transport = BatchTransport()
        result = self.make('M', public_model(transport)).run()
        self.assertEqual(result['terminal'], 'released')
        self.assertTrue(all(request.get('output_schema', {}).get('type') == 'object' for request in transport.requests))

    def test_independent_audit_check_rejects_a_resealed_request_schema_change(self):
        run = self.make('M', public_model(BatchTransport()))
        result = run.run()
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py'
        valid = subprocess.run([sys.executable, '-B', str(checker), 'audit', result['audit_path']],
                               cwd=PROJECT, capture_output=True)
        self.assertEqual(valid.returncode, 0, valid.stdout.decode())
        audit = json.loads(Path(result['audit_path']).read_bytes())
        request = json.loads((PROJECT / audit['messages'][0]['request_ref']['path']).read_bytes())
        request['output_schema'] = {'type': 'object', 'properties': {'FORGED': {'type': 'string'}}}
        raw = wire(request) + b'\n'
        forged = run.output_root / 'trace' / ('request-' + hashlib.sha256(raw).hexdigest() + '.json')
        forged.write_bytes(raw)
        audit['messages'][0]['request_ref'] = {'path': forged.relative_to(PROJECT).as_posix(),
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        broken = run.output_root / 'bad-audit.json'
        broken.write_bytes(wire(audit))
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py'
        checked = subprocess.run([sys.executable, '-B', str(checker), 'audit', str(broken)],
                                 cwd=PROJECT, capture_output=True)
        self.assertEqual(checked.returncode, 2, checked.stdout.decode())
        self.assertEqual(json.loads(checked.stdout)['reason'], 'request_prepare_count_binding')


class AdditionalEvidenceBoundary(unittest.TestCase):
    def setUp(self):
        retain = os.environ.get('THESIS_ON_DEMAND_CASES')
        parent = Path(retain) if retain else PROJECT / '.tmp/recommendation-runtime'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=self._testMethodName + '-', dir=parent, delete=not bool(retain))
        if not retain:
            self.addCleanup(self.temp.cleanup)

    def facts(self, name='facts'):
        return EvidenceFixture(Path(self.temp.name) / name).normal()

    def assess(self, facts):
        session = facts.session()
        acquire_all(session)
        result = session.assess_current()['assessment']
        (facts.root / 'public-assessment.json').write_bytes(wire({'assessment': result, 'audit': session.audit_view()}) + b'\n')
        return result

    def test_V02_mismatched_original_is_pending(self):
        facts = self.facts()
        report = next(row for row in facts.rows['materials.jsonl'] if row['kind'] == 'inspection_report')
        report.update(parent_asin='OTHER-PARENT', sim_batch_id='OTHER-BATCH', event_id='OTHER-EVENT')
        next(row for row in facts.registrations if row['target_id'] == report['evidence_id'])['content_sha256'] = hashlib.sha256(wire(report)).hexdigest()
        facts.seal()
        result = self.assess(facts)
        self.assertEqual(result['evidence_state'], 'Pending')
        self.assertIn('object_mismatch', [row['reason'] for row in result['rejected']])

    def test_V04_wrong_registration_issuer_is_pending(self):
        facts = self.facts()
        next(row for row in facts.registrations if row['target_id'] == 'D-inspection_report')['issuer_id'] = 'SIM-RETAIL'
        facts.seal()
        self.assertEqual(self.assess(facts)['evidence_state'], 'Pending')

    def test_V08_revoked_pass_is_pending(self):
        self.assertEqual(self.assess(self.facts().revoke())['evidence_state'], 'Pending')

    def test_V10_legal_new_pass_is_supported(self):
        self.assertEqual(self.assess(self.facts().revise('pass'))['evidence_state'], 'Supported')

    def test_V11_denied_report_does_not_become_supported(self):
        facts = self.facts()
        facts.policy['read_denials'] = [{'principal_id': 'SIM-VERIFIER', 'target_kind': 'material',
            'target_id': 'D-inspection_report', 'version': 1}]
        facts.seal()
        self.assertEqual(self.assess(facts)['evidence_state'], 'Pending')

    def test_V13_missing_and_conflicting_objects_are_reported_separately(self):
        missing = self.facts('missing')
        missing.rows['materials.jsonl'] = [row for row in missing.rows['materials.jsonl'] if row['kind'] != 'inspection_report']
        missing.seal()
        conflict = self.facts('conflict')
        report = copy.deepcopy(next(row for row in conflict.rows['materials.jsonl'] if row['kind'] == 'inspection_report'))
        report['evidence_id'] = 'D-independent-report'
        report['facts']['conclusion'] = 'fail'
        conflict.add('materials.jsonl', report)
        conflict.register_all()
        conflict.seal()
        self.assertEqual([self.assess(facts)['evidence_state'] for facts in (missing, conflict)], ['Pending', 'Conflict'])

    def test_V14_conflict_and_expiry_remain_conflict(self):
        facts = self.facts()
        report = copy.deepcopy(next(row for row in facts.rows['materials.jsonl'] if row['kind'] == 'inspection_report'))
        report['evidence_id'] = 'D-independent-report'
        report['facts']['conclusion'] = 'fail'
        facts.add('materials.jsonl', report)
        next(row for row in facts.rows['materials.jsonl'] if row['kind'] == 'retail_status')['valid_to_ms'] = 900
        facts.register_all()
        facts.seal()
        self.assertEqual(self.assess(facts)['evidence_state'], 'Conflict')

    def test_V15_new_refutation_and_expiry_are_refuted(self):
        facts = self.facts().revise('fail')
        next(row for row in facts.rows['materials.jsonl'] if row['kind'] == 'retail_status')['valid_to_ms'] = 900
        facts.register_all()
        facts.seal()
        self.assertEqual(self.assess(facts)['evidence_state'], 'Refuted')


if __name__ == '__main__' and sys.argv[1:] == ['legacy-batch-regressions']:
    from tests.test_batched_recommendation import BatchedRecommendationTests
    class ScopedBatchRegression(BatchedRecommendationTests):
        def setUp(self):
            parent = PROJECT / '.tmp/recommendation-runtime/test100-legacy-regressions' / os.environ['THESIS_BATCH_CHECK_LABEL']
            parent.mkdir(parents=True, exist_ok=True)
            self.case_root = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=parent))
            self.fixture = RuntimeFixture(self.case_root)
    # Reuse the original test bodies and assertions, changing only the filesystem fixture root.
    suite = unittest.TestSuite(ScopedBatchRegression(name) for name in (
        'test_four_quality_candidates_have_six_roles_and_nine_actual_calls',
        'test_normal_work_cannot_spend_the_final_model_slot'))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())

