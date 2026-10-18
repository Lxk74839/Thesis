"""Counter and CLI behaviors at public boundaries, with no supplier requests."""
import copy
import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest

from model_adapter import ModelAdapter
from tests.provider_fixtures import BINDING, PROJECT, case_directory, count_permit, export_catalog, request, save
from token_counting import InputCounter


class InputCountingTests(unittest.TestCase):
    def test_one_missing_count_keeps_the_whole_root_unknown_in_public_import(self):
        adapter = ModelAdapter(None, capability_binding=BINDING)
        first = adapter.prepare(request())
        other = request()
        other.update(request_id='PUBLIC-SECOND', attempt_id='PUBLIC-SECOND', max_output_tokens=1499)
        second = adapter.prepare(other)
        root = case_directory('partial-count-coverage')
        exported, path = export_catalog(root, [first, second])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        manifest = json.loads(path.read_bytes())
        counter = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0,
            sender=lambda body, **kw: {'status_code': 200, 'headers': {},
                                      'body': {'object': 'response.input_tokens', 'input_tokens': 100}})
        counter.count(first, authorization=count_permit(root, manifest))
        target = root / 'partial.json'
        proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'import', '--manifest', str(path),
            '--receipts', str(root / 'count-receipts.jsonl'), '--output', str(target)],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        report = json.loads(target.read_bytes())
        self.assertEqual(report['missing'], [second['prepared_id']])
        self.assertIsNone(report['per_root_input_tokens']['PUBLIC-RUN'])
        self.assertFalse(report['official_complete'])

    def test_self_rehashed_unmatched_tool_result_is_not_complete_input(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        prepared['wire_body']['input'].pop(2)
        prepared['count_body']['input'].pop(2)
        def digest(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        prepared['wire_utf8'] = json.dumps(prepared['wire_body'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        prepared['count_utf8'] = json.dumps(prepared['count_body'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        prepared['wire_bytes'] = len(prepared['wire_utf8'].encode())
        prepared['wire_sha256'], prepared['count_payload_sha256'] = digest(prepared['wire_body']), digest(prepared['count_body'])
        prepared['prepared_id'] = digest({k: prepared[k] for k in ('wire_sha256', 'count_payload_sha256',
            'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')})
        self.assertEqual(InputCounter('PUBLIC-PROJECT', fixture_count=100).count(
            prepared, authorization=None)['status'], 'invalid_prepared')

    def test_self_rehashed_server_state_fields_are_not_an_allowed_complete_request(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        prepared['wire_body']['conversation'] = 'PUBLIC-UNFROZEN-CONVERSATION'
        prepared['count_body']['conversation'] = 'PUBLIC-UNFROZEN-CONVERSATION'
        def digest(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        for prefix, key in (('wire', 'wire_body'), ('count', 'count_body')):
            prepared[prefix + '_utf8'] = json.dumps(prepared[key], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        prepared['wire_sha256'] = digest(prepared['wire_body'])
        prepared['count_payload_sha256'] = digest(prepared['count_body'])
        prepared['wire_bytes'] = len(prepared['wire_utf8'].encode('utf-8'))
        prepared['prepared_id'] = digest({k: prepared[k] for k in ('wire_sha256', 'count_payload_sha256',
            'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')})
        result = InputCounter('PUBLIC-PROJECT', fixture_count=100).count(prepared, authorization=None)
        self.assertEqual(result['status'], 'invalid_prepared')

    def test_duplicate_attempt_records_are_rejected_instead_of_collapsing_the_ledger(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('duplicate-count-ledger')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        counter = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0,
            sender=lambda body, **kw: {'status_code': 200, 'headers': {},
                                      'body': {'object': 'response.input_tokens', 'input_tokens': 100}})
        counter.count(prepared, authorization=count_permit(root, json.loads(path.read_bytes())))
        journal = root / 'count-journal.jsonl'
        first = journal.read_text().splitlines()[0]
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(first + '\n')
        self.assertEqual(InputCounter('PUBLIC-PROJECT', directory=root).count(
            prepared, authorization=None)['status'], 'invalid_receipt')

    def test_a_small_catalog_cannot_label_itself_as_full_T0_coverage(self):
        root = case_directory('fake-full-coverage')
        source = root / 'prepared.jsonl'
        source.write_text(json.dumps({'plan': {'schema_version': 'openai-count-plan-0.1.0',
            'scope': 'T0_controlled_catalog', 'project_id': 'PUBLIC-PROJECT',
            'roots': [{'run_id': 'PUBLIC-R', 'method': 'R'}], 'expected': []}}) + '\n', encoding='utf-8')
        target = root / 'manifest.json'
        proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'export',
            '--prepared', str(source), '--output', str(target)], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(target.exists())

    def test_empty_R_fixture_catalog_does_not_gain_official_count_provenance(self):
        root = case_directory('empty-R-catalog')
        source = root / 'prepared.jsonl'
        source.write_text(json.dumps({'plan': {'schema_version': 'openai-count-plan-0.1.0',
            'scope': 'public_fixture', 'project_id': 'PUBLIC-PROJECT',
            'roots': [{'run_id': 'PUBLIC-R', 'method': 'R'}], 'expected': []}}) + '\n', encoding='utf-8')
        manifest, target = root / 'manifest.json', root / 'import.json'
        for args in (['export', '--prepared', str(source), '--output', str(manifest)],
                     ['import', '--manifest', str(manifest), '--receipts', str(root / 'count-receipts.jsonl'), '--output', str(target)]):
            proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', *args],
                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        imported = json.loads(target.read_bytes())
        self.assertFalse(imported['official_complete'])
        self.assertEqual(imported['status'], 'imported_fixture')
        self.assertEqual(imported['per_root_input_tokens'], {'PUBLIC-R': 0})

    def test_unknown_count_outcome_holds_cost_and_stops_a_reopened_client(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('unknown-count-outcome')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        permit, sends = count_permit(root, json.loads(path.read_bytes())), []
        def sender(body, **kw):
            sends.append(body)
            raise TimeoutError('PUBLIC-UNKNOWN-OUTCOME')
        first = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0, sender=sender).count(prepared, authorization=permit)
        second = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0, sender=sender).count(prepared, authorization=permit)
        self.assertEqual(first['status'], 'count_failed')
        self.assertEqual(second['status'], 'count_stage_halted')
        self.assertEqual(second['held_unknown_microusd'], 3)
        self.assertEqual(len(sends), 1)
        rows = [json.loads(line) for line in (root / 'count-journal.jsonl').read_text().splitlines()]
        self.assertIsNone(rows[-1]['cost_microusd'])

    def test_two_count_clients_cannot_spend_the_same_single_attempt_slot(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('count-serial')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        permit = count_permit(root, json.loads(path.read_bytes()))
        sends, entered, release = [], threading.Event(), threading.Event()
        def clock():
            if not entered.is_set():
                entered.set()
                release.wait(2)
            return 0
        def sender(body, **kw):
            sends.append(body)
            return {'status_code': 200, 'headers': {}, 'body': {'object': 'response.input_tokens', 'input_tokens': 100}}
        def count():
            return InputCounter('PUBLIC-PROJECT', directory=root, clock=clock, sender=sender).count(prepared, authorization=permit)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(count)
            self.assertTrue(entered.wait(2))
            second = pool.submit(count)
            second_result = second.result(timeout=2)
            release.set()
            results = [first.result(timeout=2), second_result]
        self.assertEqual(len(sends), 1)
        self.assertEqual(sorted(r['status'] for r in results), ['count_inflight', 'counted'])

    def test_relabeling_fixture_receipt_and_result_does_not_make_it_official(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('forged-official')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        counter = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0,
            sender=lambda body, **kw: {'status_code': 200, 'headers': {},
                                      'body': {'object': 'response.input_tokens', 'input_tokens': 100}})
        receipt = counter.count(prepared, authorization=count_permit(root, json.loads(path.read_bytes())))
        receipt['basis'] = 'official_input_tokens'
        receipt.pop('receipt_id')
        receipt['receipt_id'] = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        (root / 'count-receipts.jsonl').write_text(json.dumps(receipt) + '\n', encoding='utf-8')
        rows = [json.loads(line) for line in (root / 'count-journal.jsonl').read_text().splitlines()]
        rows[0]['basis'] = 'official_input_tokens'
        rows[1]['receipt'] = receipt
        (root / 'count-journal.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
        result = InputCounter('PUBLIC-PROJECT', directory=root).count(prepared, authorization=None)
        self.assertEqual(result['status'], 'invalid_receipt')
        self.assertIsNone(result['input_tokens'])

    def test_count_http_boundary_has_one_fixed_post_with_an_explicit_fixture_connection(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('count-http-fixture')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        manifest, calls = json.loads(path.read_bytes()), []
        class Response:
            status = 200
            def getheaders(self):
                return [('x-request-id', 'PUBLIC-HTTP-COUNT')]
            def read(self, limit):
                calls.append(('read', limit))
                return b'{"object":"response.input_tokens","input_tokens":100}'
        class Connection:
            def __init__(self, host, timeout):
                calls.append(('connect', host, timeout))
            def request(self, method, path, body, headers):
                calls.append(('request', method, path, body, headers['Content-Type']))
            def getresponse(self):
                return Response()
            def close(self):
                calls.append(('close',))
        counter = InputCounter('PUBLIC-PROJECT', directory=root, https_factory=Connection,
                               credential='PUBLIC-FIXTURE-NOT-A-KEY', clock=lambda: 0)
        result = counter.count(prepared, authorization=count_permit(root, manifest))
        self.assertEqual(result['status'], 'counted')
        self.assertEqual(result['basis'], 'fixture')
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertEqual(calls[0], ('connect', 'api.openai.com', 30))
        self.assertEqual(calls[1], ('request', 'POST', '/v1/responses/input_tokens', prepared['count_utf8'].encode(), 'application/json'))
        self.assertEqual(calls[-1], ('close',))
        self.assertNotIn('PUBLIC-FIXTURE-NOT-A-KEY', (root / 'count-journal.jsonl').read_text())

    def test_public_count_cli_rejects_planning_caps_without_creating_an_attempt(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('count-cli-denied')
        exported, path = export_catalog(root, [prepared])
        self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
        permit_path, journal = root / 'planning.json', root / 'count-journal.jsonl'
        save(permit_path, {'enabled': True, 'scope': 'planning', 'max_calls': 108800, 'wall_seconds': 86400})
        proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'count', '--manifest', str(path),
            '--permit', str(permit_path), '--journal', str(journal)],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'], 'permission_denied')
        self.assertFalse(journal.exists())

    def test_public_import_keeps_fixture_origin_and_counts_every_original_reference(self):
        adapter = ModelAdapter(None, capability_binding=BINDING)
        first = adapter.prepare(request())
        other = request()
        other.update(run_id='PUBLIC-RUN-2', request_id='PUBLIC-REQUEST-2', attempt_id='PUBLIC-ATTEMPT-2',
                     session_id='PUBLIC-RUN-2:推荐管理')
        root = case_directory('catalog-import')
        proc, path = export_catalog(root, [first, adapter.prepare(other)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.loads(path.read_bytes())
        counter = InputCounter('PUBLIC-PROJECT', directory=root, clock=lambda: 0,
            sender=lambda body, **kw: {'status_code': 200, 'headers': {},
                                      'body': {'object': 'response.input_tokens', 'input_tokens': 100}})
        self.assertEqual(counter.count(first, authorization=count_permit(root, manifest))['status'], 'counted')
        target = root / 'import.json'
        proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'import', '--manifest', str(path),
            '--receipts', str(root / 'count-receipts.jsonl'), '--output', str(target)],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        imported = json.loads(target.read_bytes())
        self.assertEqual(imported['status'], 'imported_fixture')
        self.assertFalse(imported['official_complete'])
        self.assertEqual(imported['references'], 2)
        self.assertEqual(imported['per_root_input_tokens'], {'PUBLIC-RUN': 100, 'PUBLIC-RUN-2': 100})

    def test_explicit_fixture_permission_sends_full_count_body_once_and_persists_its_origin(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        root = case_directory('external-count-fixture')
        proc, path = export_catalog(root, [prepared])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.loads(path.read_bytes())
        sends = []
        def sender(body, *, deadline_ms):
            sends.append((body, deadline_ms))
            return {'status_code': 200, 'headers': {'x-request-id': 'PUBLIC-COUNT-ID'},
                    'body': {'object': 'response.input_tokens', 'input_tokens': 100}}
        counter = InputCounter('PUBLIC-PROJECT', directory=root, sender=sender, clock=lambda: 0)
        result = counter.count(prepared, authorization=count_permit(root, manifest))
        self.assertEqual(result['status'], 'counted')
        self.assertEqual(result['basis'], 'fixture')
        self.assertEqual(result['input_tokens'], 100)
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertEqual(sends, [(prepared['count_utf8'], 30000)])
        self.assertEqual(counter.count(prepared, authorization=None)['receipt_id'], result['receipt_id'])
        self.assertEqual(len(sends), 1)
        journal = [json.loads(line) for line in (root / 'count-journal.jsonl').read_text().splitlines()]
        self.assertEqual([r['kind'] for r in journal], ['intent', 'result'])
        self.assertEqual(journal[0]['held_microusd'], 3)
        self.assertEqual(journal[1]['cost_microusd'], 2)

    def test_public_export_deduplicates_identical_wire_without_losing_root_coverage(self):
        adapter = ModelAdapter(None, capability_binding=BINDING)
        first = adapter.prepare(request())
        other = request()
        other.update(run_id='PUBLIC-RUN-2', request_id='PUBLIC-REQUEST-2', attempt_id='PUBLIC-ATTEMPT-2',
                     session_id='PUBLIC-RUN-2:推荐管理')
        second = adapter.prepare(other)
        root = case_directory('catalog-export')
        proc, target = export_catalog(root, [first, second])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.loads(target.read_bytes())
        self.assertTrue(manifest['complete'])
        self.assertEqual(len(manifest['entries']), 1)
        self.assertEqual(len(manifest['references']), 2)
        self.assertEqual({r['run_id'] for r in manifest['references']}, {'PUBLIC-RUN', 'PUBLIC-RUN-2'})
        self.assertEqual(manifest['provider_requests_sent'], 0)

    def test_planning_caps_do_not_authorize_an_external_count(self):
        sends = []
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        counter = InputCounter('PUBLIC-PROJECT', sender=lambda *args: sends.append(args))
        result = counter.count(prepared, authorization={'enabled': True, 'scope': 'planning',
            'max_calls': 108800, 'wall_seconds': 86400})
        self.assertEqual(result['status'], 'permission_denied')
        self.assertIsNone(result['input_tokens'])
        self.assertEqual(sends, [])

    def test_changed_wire_or_wrong_project_cannot_reuse_a_prepared_count(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        changed = copy.deepcopy(prepared)
        changed['wire_body']['input'][0]['content'] = 'changed after preparation'
        self.assertEqual(InputCounter('PUBLIC-PROJECT', fixture_count=100).count(
            changed, authorization=None)['status'], 'invalid_prepared')
        self.assertEqual(InputCounter('OTHER-PROJECT', fixture_count=100).count(
            prepared, authorization=None)['status'], 'invalid_prepared')

    def test_literal_fixture_count_is_bound_to_full_prepared_request_and_never_official(self):
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        result = InputCounter('PUBLIC-PROJECT', fixture_count=100).count(prepared, authorization=None)
        self.assertEqual(result['status'], 'counted')
        self.assertEqual(result['input_tokens'], 100)
        self.assertEqual(result['basis'], 'fixture')
        self.assertEqual(result['wire_sha256'], prepared['wire_sha256'])
        self.assertEqual(result['count_payload_sha256'], prepared['count_payload_sha256'])
        self.assertIsNone(result['returned_model'])
        self.assertEqual(result['provider_requests_sent'], 0)

    def test_missing_offline_receipt_keeps_count_unknown_and_never_sends(self):
        sends = []
        prepared = ModelAdapter(None, capability_binding=BINDING).prepare(request())
        counter = InputCounter('PUBLIC-PROJECT', sender=lambda *a: sends.append(a))
        result = counter.count(prepared, authorization=None)
        self.assertEqual(result['status'], 'count_missing')
        self.assertIsNone(result['input_tokens'])
        self.assertEqual(sends, [])
