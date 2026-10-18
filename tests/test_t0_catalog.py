"""T0-A public CLI behavior; public data never establishes development acceptance."""
import json
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def setUp(self):
        scratch = PROJECT / '.tmp/ticket12-t0'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def cli(self, authorization, output='catalog'):
        return subprocess.run([sys.executable, '-B', '-m', 't0_catalog', 'prepare',
            '--authorization', str(authorization), '--output', str(self.work / output)],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')

    def save(self, name, value, raw=False):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if raw else (json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n').encode())
        return {'path': path.relative_to(PROJECT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'bytes': path.stat().st_size}

    def public_authorization(self):
        key = b'PUBLIC-IDENTITY-KEY-32-BYTES-ONLY!'
        roots = [hmac.new(key, b'preference-task-1.0.1\0' + u.encode(), hashlib.sha256).hexdigest()
                 for u in ('PUBLIC-DEV-A', 'PUBLIC-DEV-B', 'PUBLIC-TEST')]
        def rows(values):
            return b''.join((json.dumps(v, ensure_ascii=False, sort_keys=True) + '\n').encode() for v in values)
        accounts = [{'user_id': u, 'split': s} for u, s in
                    [('PUBLIC-DEV-A', 'dev'), ('PUBLIC-DEV-B', 'dev'), ('PUBLIC-TEST', 'test')]]
        model_roots = [{'root_task_id': r, 'history': [{'text': 'PUBLIC rice'}],
            'seen_parent_asins': ['PUBLIC-SEEN'], 'history_cutoff_exclusive_ms': 100,
            'candidate_count': 0, 'C_sha256': hashlib.sha256(b'[]').hexdigest(),
            'H_sha256': hashlib.sha256(b'[{"text":"PUBLIC rice"}]').hexdigest(),
            'base_scores_sha256': hashlib.sha256(b'[]').hexdigest()} for r in roots[:2]]
        # A non-selected body is deliberately not JSON-decodable. The nested/escaped IDs are decoys.
        decoy = ('{"root_task_id":"' + roots[2] + '","history":NaN,"nested":{"root_task_id":"'
                 + roots[0] + '"},"text":"\\\"root_task_id\\\":\\\"' + roots[1] + '\\\""}\n').encode()
        sources = {'accounts': self.save('sources/accounts.jsonl', rows(accounts), True),
            'identity_key': self.save('sources/id-key.bin', key, True),
            'model_roots': self.save('sources/roots.jsonl', rows(model_roots) + decoy, True),
            'model_candidates': self.save('sources/candidates.jsonl', rows([
                {'root_task_id': r, 'C': [], 'b': [], 'batches': [], 'background_statistics': []} for r in roots[:2]]) + decoy, True),
            'model_catalog': self.save('sources/catalog.jsonl', b'', True),
            'view_bindings': self.save('sources/views.jsonl', rows([
                {'root_task_id': r, 'label': 'PUBLIC-V00', 'arm': 'necessary',
                 'request': {'design_text': 'PUBLIC SIM', 'necessary_clauses': ['R1', 'R5']}}
                for r in roots[:2]]) + decoy, True)}
        contract = self.save('PUBLIC-contract.md', b'PUBLIC synthetic catalog test\n', True)
        human = self.save('PUBLIC-confirmation.md', b'PUBLIC test only\n', True)
        acceptance = self.save('PUBLIC-acceptance.json', {'status': 'public_catalog_test'})
        auth = {'schema_version': 't0-a-authorization-0.1.0', 'approved': True, 'scope': 'public_catalog_test',
            'contract': contract, 'human_confirmation': human,
            'base': '88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a', 'candidate': 'PUBLIC',
            'program_acceptance': acceptance, 'sources': sources, 'budget_candidate': 'B02-A+B03',
            'resource_ledger': 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl',
            'api_limits': {'count': 0, 'generate': 0, 'other': 0}}
        self.save('authorization.json', auth)
        return self.work / 'authorization.json', auth, roots

    def test_missing_confirmation_preserves_incomplete_diagnostic(self):
        result = self.cli(self.work / 'missing.json')
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads((self.work / 'catalog/run.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'T0_A_incomplete')
        self.assertFalse(report['complete'])
        self.assertEqual(report['provider_api_calls'], {'count': 0, 'generate': 0, 'other': 0})
        self.assertEqual(report['reasons'], ['authorization_unavailable'])

    def test_public_catalog_selects_only_original_dev_top_level_ids(self):
        authorization, auth, ids = self.public_authorization()
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        catalog = json.loads((self.work / 'catalog/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['scope'], 'public_catalog_test')
        self.assertEqual(catalog['acceptance_kind'], 'public_synthetic_only')
        plans = [json.loads(line) for line in (self.work / 'catalog/roots.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual({p['root_task_id'] for p in plans}, set(ids[:2]))
        self.assertEqual(len(plans), 6)
        self.assertNotIn(ids[2], (self.work / 'catalog/roots.jsonl').read_text(encoding='utf-8'))
        self.assertNotIn('PUBLIC-DEV-A', (self.work / 'catalog/roots.jsonl').read_text(encoding='utf-8'))

    def test_catalog_prepare_is_native_complete_but_cannot_invoke(self):
        from model_adapter import ModelAdapter
        from tests.provider_fixtures import request, MODEL
        sent = []
        class CounterTrap:
            def count(self, *args, **kwargs):
                raise AssertionError('catalog must not count')
        adapter = ModelAdapter(lambda *a, **kw: sent.append(a), capability_binding={
            'execution_kind': 't0_development_catalog', 'model_id': MODEL,
            'provenance': 'synthetic', 'project_id': 'UNBOUND-T0-DEV-CATALOG'}, counter=CounterTrap())
        req = request()
        for key in ('input_token_upper_bound', 'deadline_ms', 'reservation_id'):
            req.pop(key)
        req.update(schema_version='rsm-model-prepare-0.1.0', execution_kind='t0_development_catalog')
        prepared = adapter.prepare(req)
        self.assertEqual(prepared['status'], 'prepared')
        self.assertIsNone(prepared['input_tokens'])
        self.assertEqual(prepared['wire_body']['model'], MODEL)
        self.assertEqual(prepared['wire_body']['input'][0], {'role': 'system', 'content': '公开协议\nSIM'})
        self.assertEqual(prepared['wire_body']['input'][-1], {'type': 'function_call_output',
            'call_id': 'PUBLIC-CALL', 'output': '{"entries":[],"next_cursor":null}'})
        self.assertEqual(prepared['count_body'], {k: v for k, v in prepared['wire_body'].items()
            if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')})
        for value in (req, {**req, 'schema_version': 'rsm-model-request-0.3.0',
                           'prepared_id': prepared['prepared_id'], 'count_receipt_id': 'fixture'}):
            self.assertEqual(adapter.invoke(value)['status'], 'preflight_denied')
        self.assertEqual(sent, [])

    def test_catalog_requests_keep_history_and_real_clauses_without_host_metadata(self):
        authorization, auth, ids = self.public_authorization()
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        requests = [json.loads(line) for line in (self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(requests)
        first = next(r for r in requests if r['method'] == 'M')
        prepared = json.loads((self.work / 'catalog/objects' / (first['prepared_id'] + '.json')).read_text(encoding='utf-8'))
        wire = prepared['wire_body']
        original = json.loads(wire['input'][1]['content'])
        self.assertEqual(original['H'], [{'text': 'PUBLIC rice'}])
        self.assertEqual(original['seen_parent_asins'], ['PUBLIC-SEEN'])
        self.assertEqual(original['history_cutoff_exclusive_ms'], 100)
        self.assertEqual(original['request']['necessary_clauses'], ['R1', 'R5'])
        self.assertNotIn('history', original)
        self.assertNotIn('PUBLIC-V00', prepared['wire_utf8'])
        self.assertNotIn('PUBLIC-DEV', prepared['wire_utf8'])
        self.assertIsNone(prepared['input_tokens'])

    def test_indexed_source_reuses_io_but_evidence_dispatch_still_meters_each_session(self):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.provider_fixtures import case_directory
        from evidence_access import LocalEvidenceSource
        fixture = RuntimeFixture(case_directory('t0-index'))
        source = LocalEvidenceSource(fixture.facts.snapshot_ref, indexed=True)
        observations = []
        for _ in range(2):
            runtime = fixture.make('R', source_type=lambda ref: source)
            page = runtime.evidence.dispatch('list_evidence', {'cursor': None})
            read = runtime.evidence.dispatch('read_evidence', {'evidence_refs': [e['evidence_ref'] for e in page['entries']]})
            denied = runtime.evidence.dispatch('read_evidence', {'evidence_refs': ['PUBLIC-UNKNOWN']})
            self.assertEqual(denied['status'], 'access_denied')
            self.assertEqual(page['receipt']['usage_delta']['physical_tools'], 1)
            self.assertEqual(read['receipt']['usage_delta']['physical_tools'], 1)
            self.assertEqual(read['receipt']['usage_delta']['logical_tools'], len(page['entries']))
            observations.append(([i['raw_utf8'] for i in read['items']], source.setup.copy()))
        self.assertTrue(observations[0][0])
        self.assertEqual(observations[0], observations[1])

    def with_facts(self, auth, fixture, ids, arm='necessary'):
        from evidence_access import encoded, digest
        candidates = [{'root_task_id': r, 'C': fixture.parents, 'b': fixture.scores,
            'batches': fixture.batches, 'background_statistics': [{'parent_asin': p, 'PUBLIC': 1} for p in fixture.parents]}
            for r in ids[:2]]
        old = [json.loads(line) for line in (self.work / 'sources/roots.jsonl').read_text().splitlines()[:2]]
        for row in old:
            row.update(candidate_count=len(fixture.parents), C_sha256=digest(encoded(fixture.parents)),
                base_scores_sha256=digest(encoded(list(zip(fixture.parents, fixture.scores)))))
        def rows(values):
            return b''.join(encoded(v) + b'\n' for v in values)
        auth['sources']['model_roots'] = self.save('sources/roots.jsonl', rows(old), True)
        auth['sources']['model_candidates'] = self.save('sources/candidates.jsonl', rows(candidates), True)
        auth['sources']['model_catalog'] = self.save('sources/catalog.jsonl', rows([
            {'parent_asin': p, 'title': 'PUBLIC rice'} for p in fixture.parents]), True)
        auth['sources']['view_bindings'] = self.save('sources/views.jsonl', rows([
            {'root_task_id': r, 'label': 'PUBLIC-V00', 'arm': arm, 'snapshot': fixture.facts.snapshot_ref,
             'snapshot_id': fixture.facts.snapshot['snapshot_id'], 'principal_id': 'SIM-VERIFIER', 'verify_at_ms': 1000,
             'request': {'design_text': 'PUBLIC SIM', 'necessary_clauses': ['c1', 'c2']}}
            for r in ids[:2]]), True)
        self.save('authorization.json', auth)

    def test_necessary_plan_stops_at_tenth_and_all_methods_keep_cold_item_accounting(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts').candidates(
            ['PUBLIC-' + str(i).zfill(2) for i in range(11)], [1 - i / 20 for i in range(11)])
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plans = [json.loads(line) for line in (self.work / 'catalog/roots.jsonl').read_text(encoding='utf-8').splitlines()]
        for plan in plans:
            self.assertEqual(plan['processed'], fixture.parents[:10])
            self.assertEqual(plan['stop_reason'], 'first_10_qualified')
            self.assertEqual(plan['C_count'], 11)
            self.assertEqual([s['candidate_id'] for s in plan['steps'] if s['operation'] == 'assess_current'], fixture.parents[:10])
            self.assertFalse(any(s['candidate_id'] == fixture.parents[10] for s in plan['steps']))
            self.assertGreaterEqual(plan['planned_cold_usage']['physical_tools'], 20)
            self.assertGreater(plan['planned_cold_usage']['logical_tools'], 40)
        dependencies = (self.work / 'catalog/dependencies.jsonl').read_text(encoding='utf-8')
        self.assertNotIn(fixture.parents[10], dependencies)

    def test_declared_trace_has_six_roles_read_continuation_repairs_feedback_and_no_R_wire(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        requests = [json.loads(line) for line in (self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()]
        rows = [r for r in requests if r['root_task_id'] == ids[0] and r['method'] == 'M']
        self.assertEqual(len(rows), 13)
        self.assertEqual({r['semantic_role'] for r in rows}, {'需求解析', '用户画像', '推荐管理', '生命周期追溯', '农产品画像', '推荐依据核验'})
        self.assertEqual(sum(r['script_response']['status'] == 'format_error' for r in rows), 2)
        self.assertEqual([r['stage'] for r in rows if r['output_kind'] == 'draft'], ['draft', 'revision'])
        acquisitions = [r for r in rows if r['output_kind'] == 'acquire']
        self.assertEqual(len(acquisitions), 2)
        self.assertEqual(acquisitions[0]['script_response']['message']['tool_requests'][0]['name'], 'acquire_batch')
        second = json.loads((self.work / 'catalog/objects' / (acquisitions[1]['prepared_id'] + '.json')).read_text(encoding='utf-8'))
        tool = next(i for i in second['wire_body']['input'] if i.get('type') == 'function_call_output')
        self.assertEqual(json.loads(tool['output'])['processed'], ['PUBLIC-A'])
        profile = next(r for r in rows if r['semantic_role'] == '农产品画像')
        self.assertEqual([o['candidate_id'] for o in profile['script_response']['message']['content']['data']['observations']], ['PUBLIC-A'])
        self.assertFalse(any(r['method'] == 'R' for r in requests))
        self.assertTrue(all(r['effective_role'] == '单智能体' for r in requests if r['method'] == 'S'))
        self.assertTrue(all(r['provenance'] == 'synthetic' and r['input_tokens'] is None for r in requests))

    def test_public_sources_cannot_be_relabelled_as_accepted_development(self):
        authorization, auth, _ = self.public_authorization()
        auth.update(scope='development_catalog_only', candidate='a' * 40,
            resource_ledger='data/recommendation-runtime-audit/ticket12-t0/resource-ledger.jsonl')
        self.save('authorization.json', auth)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 2)
        report = json.loads((self.work / 'catalog/run.json').read_text(encoding='utf-8'))
        self.assertTrue(report['reasons'])
        self.assertFalse((self.work / 'catalog/roots.jsonl').exists())

    def test_catalog_totals_bind_all_original_requests_objects_bytes_and_unknown_tokens(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        target = self.work / 'catalog'
        coverage = json.loads((target / 'coverage.json').read_text(encoding='utf-8'))
        refs = [json.loads(line) for line in (target / 'requests.jsonl').read_text(encoding='utf-8').splitlines()]
        objects = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (target / 'objects').iterdir()}
        self.assertEqual((coverage['plans'], coverage['N'], coverage['U']), (6, 52, len(objects)))
        self.assertEqual(coverage['by_method'], {'R': 2, 'S': 2, 'M': 2})
        self.assertEqual(coverage['original_wire_bytes'], sum(len(objects[r['prepared_id']]['wire_utf8'].encode()) for r in refs))
        self.assertEqual(coverage['original_count_payload_bytes'], sum(len(objects[r['prepared_id']]['count_utf8'].encode()) for r in refs))
        self.assertEqual(coverage['unique_wire_bytes'], sum(len(p['wire_utf8'].encode()) for p in objects.values()))
        self.assertEqual(coverage['missing_objects'], 0)
        self.assertIsNone(coverage['complete_input_tokens'])
        self.assertIsNone(coverage['actual_output_tokens'])
        plans = [json.loads(line) for line in (target / 'roots.jsonl').read_text(encoding='utf-8').splitlines()]
        for plan in plans:
            self.assertEqual(plan['budget_candidate']['limits']['model_calls'], 0 if plan['method'] == 'R' else 17)
            self.assertEqual(plan['budget_candidate']['final_reserve']['model_calls'], 0 if plan['method'] == 'R' else 1)
            self.assertIsNone(plan['execution_budget'])
            self.assertFalse(plan['execution_authorized'])
            if plan['method'] != 'R':
                self.assertEqual(plan['sum_requested_output_caps'], 12 * 8192 + 1500)
                self.assertIsNone(plan['dynamic_budget_admission'])

    def test_quality_catalog_crosses_the_32_window_with_all_profiles_and_seventeen_slots(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts').quality(
            ['PUBLIC-' + str(i).zfill(2) for i in range(33)], [1 - i / 100 for i in range(33)])
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids, arm='quality')
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        target = self.work / 'catalog'
        plans = [json.loads(line) for line in (target / 'roots.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(all(len(p['processed']) == 33 for p in plans))
        self.assertTrue(all(p['request_count'] == (0 if p['method'] == 'R' else 17) for p in plans))
        refs = [json.loads(line) for line in (target / 'requests.jsonl').read_text(encoding='utf-8').splitlines()]
        profiles = [r for r in refs if r['root_task_id'] == ids[0] and r['method'] == 'M' and r['stage'] == '农产品画像']
        self.assertEqual([len(r['script_response']['message']['content']['data']['observations']) for r in profiles], [32, 1])
        self.assertTrue(all(r['quality'] is not None for p in profiles for r in p['script_response']['message']['content']['data']['observations']))

    def test_recompute_checks_content_without_a_second_catalog_or_overwriting_original(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        target = self.work / 'catalog'
        before = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob('*') if p.is_file() and not p.is_relative_to(target / 'checks') and p.name != 'run.json'}
        result = subprocess.run([sys.executable, '-B', '-m', 't0_catalog', 'prepare',
            '--authorization', str(authorization), '--output', str(target), '--recompute-digests'],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((target / 'checks/reproduction.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'stable_content_reproduced')
        self.assertTrue(report['match'])
        self.assertEqual(before, {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob('*') if p.is_file() and not p.is_relative_to(target / 'checks') and p.name != 'run.json'})
        self.assertFalse((target / 'reproduction/roots.jsonl').exists())

    def test_existing_native_run_wire_is_identical_when_prepared_with_the_same_explicit_messages(self):
        from tests.runtime_fixtures import RuntimeFixture
        from tests.provider_fixtures import BINDING, MODEL, NativeScriptedSender, case_directory
        from token_counting import InputCounter
        from model_adapter import ModelAdapter
        sender = NativeScriptedSender()
        model = ModelAdapter(sender, capability_binding=BINDING, counter=InputCounter('PUBLIC-PROJECT', fixture_count=100))
        fixture = RuntimeFixture(case_directory('t0-composer-parity'))
        result = fixture.make('M', model=model, binding_changes={'schema_version': 'rsm-run-0.2.0',
            'execution_kind': 'openai_native_fixture', 'orchestration': 'batch32-0.1.0', 'project_id': 'PUBLIC-PROJECT'},
            limits={'input_tokens': 1000, 'output_tokens': 20000, 'cost_microusd': 100000},
            final_reserve={'input_tokens': 100, 'output_tokens': 1500, 'cost_microusd': 6825}).run()
        self.assertEqual(result['terminal'], 'released', result['reason'])
        catalog = ModelAdapter(None, capability_binding={'execution_kind': 't0_development_catalog',
            'model_id': MODEL, 'project_id': 'UNBOUND-T0-DEV-CATALOG', 'provenance': 'synthetic'})
        for original, wire in zip(result['messages'], sender.wires):
            logical = {k: v for k, v in original['request'].items() if k not in
                ('input_token_upper_bound', 'deadline_ms', 'reservation_id', 'prepared_id', 'count_receipt_id')}
            logical.update(schema_version='rsm-model-prepare-0.1.0', execution_kind='t0_development_catalog')
            prepared = catalog.prepare(logical)
            self.assertEqual(prepared['status'], 'prepared')
            self.assertEqual(prepared['wire_body'], wire)
            self.assertEqual(prepared['count_utf8'], original['request']['prepared_id'] and
                next(p['prepared']['count_utf8'] for p in result['preparations']
                     if p['prepared']['prepared_id'] == original['request']['prepared_id']))

    def test_resource_stop_preserves_incomplete_and_never_replaces_an_existing_output(self):
        authorization, _, _ = self.public_authorization()
        result = subprocess.run([sys.executable, '-B', '-m', 't0_catalog', 'prepare',
            '--authorization', str(authorization), '--output', str(self.work / 'catalog')], cwd=PROJECT,
            capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'THESIS_RESOURCE_DEADLINE_UNIX': '0'})
        self.assertEqual(result.returncode, 2)
        target = self.work / 'catalog/run.json'
        original = target.read_bytes()
        self.assertEqual(json.loads(original)['reasons'], ['resource_closeout_required'])
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(target.read_bytes(), original)

    def test_oversize_wire_is_preserved_in_full_and_marks_partial_instead_of_truncating(self):
        from evidence_access import encoded, digest
        authorization, auth, ids = self.public_authorization()
        roots = [json.loads(line) for line in (self.work / 'sources/roots.jsonl').read_text().splitlines()[:2]]
        for root in roots:
            root['history'] = [{'text': 'PUBLIC-' + 'x' * (8 * 1024**2)}]
            root['H_sha256'] = digest(encoded(root['history']))
        auth['sources']['model_roots'] = self.save('sources/roots.jsonl', b''.join(encoded(r) + b'\n' for r in roots), True)
        self.save('authorization.json', auth)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        target = self.work / 'catalog'
        coverage = json.loads((target / 'coverage.json').read_text(encoding='utf-8'))
        self.assertFalse(coverage['complete'])
        self.assertIn('body_limit_exceeded', coverage['reasons'])
        self.assertEqual(coverage['N'], 1)
        prepared = json.loads(next((target / 'objects').iterdir()).read_text(encoding='utf-8'))
        self.assertGreater(prepared['wire_bytes'], 16 * 1024**2)
        self.assertEqual(len(json.loads(prepared['wire_body']['input'][1]['content'])['H'][0]['text']), 8 * 1024**2 + 7)
        plans = [json.loads(line) for line in (target / 'roots.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(any(p.get('failure_reason') == 'body_limit_exceeded' for p in plans))

    def test_independent_delivery_checks_detect_missing_objects_without_importing_production(self):
        authorization, _, _ = self.public_authorization()
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py'
        def check(name):
            return subprocess.run([sys.executable, '-B', str(checker), 'check', '--authorization', str(authorization),
                '--catalog', str(self.work / 'catalog'), '--output', str(self.work / name)],
                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        result = check('check-before.json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        next((self.work / 'catalog/objects').iterdir()).unlink()
        result = check('check-after.json')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = json.loads((self.work / 'check-after.json').read_text(encoding='utf-8'))
        self.assertIn('missing_object', report['errors'])
        self.assertFalse(report['complete'])

    def test_failed_dependency_probe_is_kept_and_charged_in_actual_probe_totals(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        (fixture.facts.root / 'materials.jsonl').write_bytes(b'PUBLIC broken original\n')
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = json.loads((self.work / 'catalog/run.json').read_text(encoding='utf-8'))
        self.assertEqual((report['actual_template_probes'], report['actual_template_dispatches']), (1, 1))
        probes = [json.loads(line) for line in (self.work / 'catalog/checks/probes.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(probes[0]['operations'][0]['result']['status'], 'source_integrity_error')
        self.assertGreater(probes[0]['audit']['setup']['file_reads'], 0)

    def test_prepared_identity_uses_full_wire_and_versions_without_losing_attempt_sources(self):
        import copy
        from model_adapter import ModelAdapter
        from tests.provider_fixtures import request, MODEL
        adapter = ModelAdapter(None, capability_binding={'execution_kind': 't0_development_catalog',
            'model_id': MODEL, 'project_id': 'UNBOUND-T0-DEV-CATALOG', 'provenance': 'synthetic'})
        logical = request()
        for field in ('input_token_upper_bound', 'deadline_ms', 'reservation_id'):
            logical.pop(field)
        logical.update(schema_version='rsm-model-prepare-0.1.0', execution_kind='t0_development_catalog')
        first = adapter.prepare(logical)
        another = copy.deepcopy(logical)
        another.update(request_id='PUBLIC-SECOND', attempt_id='PUBLIC-SECOND')
        second = adapter.prepare(another)
        self.assertEqual(first['prepared_id'], second['prepared_id'])
        self.assertEqual((first['source']['attempt_id'], second['source']['attempt_id']), ('PUBLIC-ATTEMPT', 'PUBLIC-SECOND'))
        changed_cap = adapter.prepare({**logical, 'max_output_tokens': 1501})
        self.assertEqual(first['count_payload_sha256'], changed_cap['count_payload_sha256'])
        self.assertNotEqual(first['prepared_id'], changed_cap['prepared_id'])
        another['tools'][0]['version'] = 'PUBLIC-VERSION-2'
        changed_version = adapter.prepare(another)
        self.assertEqual(first['wire_sha256'], changed_version['wire_sha256'])
        self.assertNotEqual(first['prepared_id'], changed_version['prepared_id'])
        another['output_schema']['description'] = 'PUBLIC schema revision'
        self.assertNotEqual(first['prepared_id'], adapter.prepare(another)['prepared_id'])

    def test_source_clause_objects_retain_predicates_parameters_and_time_scope_in_W(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        clause = {'clause_id': 'c1', 'source': 'experiment_design', 'predicate': 'inspection_report_conclusion',
            'parameters': {'required_conclusion': 'pass', 'required_test_scope': ['SIM-Q1']},
            'object_scope': {'candidate': 'current', 'sample_binding': 'event_sample_id'},
            'time_scope': {'mode': 'sampling_event', 'ttl_ms': None}, 'evidence_profile_id': 'inspection_sample_report_v1'}
        views = [json.loads(line) for line in (self.work / 'sources/views.jsonl').read_text().splitlines()]
        for view in views:
            view['request']['necessary_clauses'] = [clause]
        auth['sources']['view_bindings'] = self.save('sources/views.jsonl',
            b''.join((json.dumps(v, sort_keys=True) + '\n').encode() for v in views), True)
        self.save('authorization.json', auth)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first = json.loads((self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()[0])
        prepared = json.loads((self.work / 'catalog/objects' / (first['prepared_id'] + '.json')).read_text(encoding='utf-8'))
        original = json.loads(prepared['wire_body']['input'][1]['content'])
        self.assertEqual(original['request']['necessary_clauses'], [clause])
        self.assertEqual(original['request']['necessary_clauses'][0]['parameters']['required_test_scope'], ['SIM-Q1'])

    def test_existing_count_export_rejects_the_unregistered_streaming_catalog(self):
        authorization, _, _ = self.public_authorization()
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'export',
            '--prepared', str(self.work / 'catalog/catalog.json'), '--output', str(self.work / 'count-manifest.json')],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((self.work / 'count-manifest.json').exists())

    def test_closed_authorization_rejects_unapproved_overrides_and_changed_sources(self):
        import copy
        authorization, auth, _ = self.public_authorization()
        cases = []
        for field, value in [('approved', False), ('budget_candidate', 'B07'), ('scope', 'test'), ('model', 'other')]:
            altered = copy.deepcopy(auth)
            altered[field] = value
            cases.append(altered)
        altered = copy.deepcopy(auth)
        altered['sources']['model_roots']['sha256'] = '0' * 64
        cases.append(altered)
        altered = copy.deepcopy(auth)
        altered['sources']['model_roots']['path'] = '../outside.jsonl'
        cases.append(altered)
        for number, case in enumerate(cases):
            with self.subTest(number=number):
                self.save('authorization.json', case)
                result = self.cli(authorization, output='rejected-' + str(number))
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                report = json.loads((self.work / ('rejected-' + str(number)) / 'run.json').read_text(encoding='utf-8'))
                self.assertFalse(report['complete'])

    def test_junction_source_is_rejected_before_its_body_is_read(self):
        authorization, auth, _ = self.public_authorization()
        target = self.work / 'PUBLIC-target'
        target.mkdir()
        (target / 'roots.jsonl').write_bytes(b'PUBLIC body must not be parsed')
        link = self.work / 'PUBLIC-junction'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        auth['sources']['model_roots']['path'] = (link / 'roots.jsonl').relative_to(PROJECT).as_posix()
        self.save('authorization.json', auth)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = json.loads((self.work / 'catalog/run.json').read_text(encoding='utf-8'))
        self.assertEqual(report['reasons'], ['reparse_path'])

    def test_object_records_explicit_tool_versions_and_role_schema_source(self):
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        refs = [json.loads(line) for line in (self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()]
        ref = next(r for r in refs if r['output_kind'] == 'acquire')
        prepared = json.loads((self.work / 'catalog/objects' / (ref['prepared_id'] + '.json')).read_text(encoding='utf-8'))
        self.assertEqual(prepared['catalog_metadata']['tool_versions']['acquire_batch'], 'restricted-evidence-batch-0.1.0')
        self.assertEqual(prepared['catalog_metadata']['tool_versions']['candidate_page'], 'joint-page-0.1.0')
        self.assertEqual(prepared['catalog_metadata']['role_schema_generator_sha256'],
            '4a35e7c0a5a2fc780c9020ff55d1175ebf70af943600e4384def0fe6bf2890e3')
        self.assertEqual(prepared['catalog_metadata']['provenance'], 'synthetic')

    def test_metadata_permissions_are_checked_before_any_forbidden_body_open(self):
        import copy
        authorization, auth, _ = self.public_authorization()
        trap = self.work / 'PUBLIC-forbidden/evaluation.jsonl'
        trap.parent.mkdir()
        trap.write_bytes(b'PUBLIC target access trap, never actual evaluation data\n')
        marker = self.work / 'forbidden-open.txt'
        trap_ref = {'path': trap.relative_to(PROJECT).as_posix(), 'sha256': hashlib.sha256(trap.read_bytes()).hexdigest(),
                    'bytes': trap.stat().st_size}
        for number, field in enumerate(('contract', 'human_confirmation', 'program_acceptance')):
            altered = copy.deepcopy(auth)
            altered[field] = trap_ref
            self.save('authorization.json', altered)
            script = ('import sys,runpy,pathlib; trap=pathlib.Path(sys.argv[1]); marker=pathlib.Path(sys.argv[2]); '
                'args=sys.argv[3:];\n'
                'def audit(event,args):\n'
                ' if event=="open" and isinstance(args[0],(str,bytes)) and pathlib.Path(args[0])==trap:\n'
                '  marker.write_text("forbidden body opened"); raise AssertionError("forbidden_target_open")\n'
                'sys.addaudithook(audit); sys.argv=["t0_catalog",*args]; runpy.run_module("t0_catalog",run_name="__main__")')
            result = subprocess.run([sys.executable, '-B', '-c', script, str(trap), str(marker), 'prepare',
                '--authorization', str(authorization), '--output', str(self.work / ('gate-' + str(number)))],
                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(marker.exists(), field)

    def test_delivery_checker_checks_input_paths_before_opening_foreign_components(self):
        authorization, _, _ = self.public_authorization()
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        trap = self.work / 'PUBLIC-forbidden/evaluation.jsonl'
        trap.parent.mkdir()
        trap.write_text('{"PUBLIC":"forbidden target trap"}', encoding='utf-8')
        marker = self.work / 'forbidden-open.txt'
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py'
        script = ('import sys,runpy,pathlib; trap=pathlib.Path(sys.argv[1]); marker=pathlib.Path(sys.argv[2]); '
            'program=sys.argv[3]; args=sys.argv[4:];\n'
            'def audit(event,args):\n'
            ' if event=="open" and isinstance(args[0],(str,bytes)) and pathlib.Path(args[0])==trap:\n'
            '  marker.write_text("forbidden body opened"); raise AssertionError("forbidden_target_open")\n'
            'sys.addaudithook(audit); sys.argv=[program,*args]; runpy.run_path(program,run_name="__main__")')
        for number, bad_auth in enumerate((True, False)):
            if not bad_auth:
                catalog_path = self.work / 'catalog/catalog.json'
                catalog = json.loads(catalog_path.read_bytes())
                catalog['components'][str(trap)] = {'bytes': trap.stat().st_size, 'sha256': '0' * 64}
                catalog_path.write_text(json.dumps(catalog), encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', '-c', script, str(trap), str(marker), str(checker), 'check',
                '--authorization', str(trap if bad_auth else authorization), '--catalog', str(self.work / 'catalog'),
                '--output', str(self.work / ('checker-gate-' + str(number) + '.json'))],
                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(marker.exists())

    def test_synthetic_issue_and_repaired_draft_match_the_existing_release_contract(self):
        import copy
        from tests.runtime_fixtures import RuntimeFixture
        fixture = RuntimeFixture(self.work / 'sources/facts')
        rejected = copy.deepcopy(next(r for r in fixture.facts.rows['materials.jsonl'] if r['kind'] == 'inspection_report'))
        rejected.update(evidence_id='PUBLIC-REJECTED', issuer_id='PUBLIC-NONISSUER')
        fixture.facts.rows['materials.jsonl'].append(rejected)
        fixture.seal()
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        refs = [json.loads(line) for line in (self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()]
        rows = [r for r in refs if r['root_task_id'] == ids[0] and r['method'] == 'M']
        issue = next(r['script_response']['message']['content']['data']['issues'][0] for r in rows
                     if r['output_kind'] == 'verification' and r['script_response']['message']['content']['data']['issues'])
        self.assertEqual(issue['verifier'], 'model')
        draft = next(r['script_response']['message']['content']['data'] for r in rows if r['stage'] == 'revision')
        texts = {'inspection_supported': '检验必要条件有完整有效支持（SIM）。',
                 'on_sale_supported': '核验时点的在售必要条件有完整有效支持（SIM）。'}
        for item in draft['items']:
            for reason in item['reasons']:
                self.assertEqual(reason['text'], texts[reason['kind']])
                self.assertNotIn('PUBLIC-REJECTED', [c['target_id'] for c in reason['citations']])
        self.assertEqual(rows[-1]['script_response']['message']['content']['data']['draft_id'], draft['draft_id'])

    def test_catalog_replies_replay_through_the_existing_native_run_and_release_gate(self):
        import copy
        from evidence_access import encoded
        from model_adapter import ModelAdapter
        from tests.runtime_fixtures import RuntimeFixture
        from tests.provider_fixtures import BINDING, case_directory, native_response
        from token_counting import InputCounter
        catalog_fixture = RuntimeFixture(self.work / 'sources/facts')
        authorization, auth, ids = self.public_authorization()
        self.with_facts(auth, catalog_fixture, ids)
        result = self.cli(authorization)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        planned = [json.loads(line) for line in (self.work / 'catalog/requests.jsonl').read_text(encoding='utf-8').splitlines()]
        planned = [r for r in planned if r['root_task_id'] == ids[0] and r['method'] == 'M']
        sends = []
        def sender(body, *, deadline_ms):
            wire = json.loads(body)
            sends.append(wire)
            context = next(json.loads(m['content'])['runtime'] for m in reversed(wire['input'])
                if m.get('role') == 'user' and isinstance(json.loads(m['content']), dict) and 'runtime' in json.loads(m['content']))
            def rebind(value, parent=None):
                if isinstance(value, list):
                    return [rebind(v, parent) for v in value]
                if not isinstance(value, dict):
                    return value
                parent = value.get('candidate_id', value.get('parent_asin', parent))
                if {'target_id', 'evidence_ref', 'receipt_id', 'version', 'pointer'} <= set(value):
                    fact = next(f for facts in context['facts'].values() for f in facts
                        if f['citation']['target_id'] == value['target_id'] and f['citation']['version'] == value['version'])
                    return {**fact['citation'], 'pointer': value['pointer']}
                return {key: context['assessment_receipts'][parent] if key == 'assessment_receipt_id' else
                    sorted({f['citation']['receipt_id'] for facts in context['facts'].values() for f in facts}) if key == 'source_receipts' else
                    rebind(item, parent) for key, item in value.items()}
            scripted = planned[len(sends) - 1]['script_response']
            message = rebind(copy.deepcopy(scripted['message']))
            raw = native_response()
            if scripted['status'] == 'format_error':
                raw['body']['output'][0]['content'][0]['text'] = '{synthetic malformed'
            elif message['tool_requests']:
                raw['body']['output'] = [{'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                    'arguments': encoded(c['arguments']).decode()} for c in message['tool_requests']]
            else:
                raw['body']['output'][0]['content'][0]['text'] = encoded(message['content']).decode()
            return raw
        runtime_fixture = RuntimeFixture(case_directory('t0-controlled-reply-replay'))
        runtime_fixture.history = [{'text': 'PUBLIC rice'}]
        model = ModelAdapter(sender, capability_binding=BINDING, counter=InputCounter('PUBLIC-PROJECT', fixture_count=100))
        actual = runtime_fixture.make('M', model=model, binding_changes={'schema_version': 'rsm-run-0.2.0',
            'execution_kind': 'openai_native_fixture', 'orchestration': 'batch32-0.1.0', 'project_id': 'PUBLIC-PROJECT'},
            limits={'model_calls': 17, 'input_tokens': 192000, 'output_tokens': 24000, 'cost_microusd': 252017, 'elapsed_ms': 900000},
            final_reserve={'input_tokens': 8000, 'output_tokens': 1500, 'cost_microusd': 12751, 'elapsed_ms': 60000}).run()
        self.assertEqual(actual['terminal'], 'released', (actual['terminal'], actual['reason']))
        self.assertEqual((len(sends), actual['budget']['usage']['retries'], actual['feedback_round']), (13, 2, 1))
        self.assertEqual(actual['release_check']['issues'], [])


if __name__ == '__main__':
    unittest.main()
