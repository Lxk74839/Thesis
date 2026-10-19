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

    def prepared_objects(self):
        from t0_catalog import iter_prepared_objects
        return {p['prepared_id']: p for p in iter_prepared_objects(self.work / 'catalog')}

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
        prepared = self.prepared_objects()[first['prepared_id']]
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
        second = self.prepared_objects()[acquisitions[1]['prepared_id']]
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
        objects = self.prepared_objects()
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
        import zlib
        manifest = json.loads((target / 'objects/manifest.json').read_bytes())
        wire = json.loads(zlib.decompress((target / 'objects/requests.pack').read_bytes()))
        self.assertGreater(manifest['records'][0]['raw_bytes'], 16 * 1024**2)
        self.assertEqual(len(json.loads(wire['input'][1]['content'])['H'][0]['text']), 8 * 1024**2 + 7)
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
        (self.work / 'catalog/objects/requests.pack').unlink()
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
        prepared = self.prepared_objects()[first['prepared_id']]
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
        prepared = self.prepared_objects()[ref['prepared_id']]
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


class StorageTests(unittest.TestCase):
    """Frozen PUBLIC objects exercise storage without expanding a root trace."""
    def setUp(self):
        label = os.environ['THESIS_BATCH_CHECK_LABEL']
        self.work = PROJECT / '.tmp/ticket12-t0/storage-repair-20261019' / label / self._testMethodName
        self.work.mkdir(parents=True)

    def originals(self, case='baseline'):
        package = json.loads((PROJECT / '.scratch/ticket12-budget-20261018/storage-repair-package-20261019.json').read_bytes())
        entries = sorted((p for p in package['public_objects'] if '/catalog-' + case + '/objects/' in p['path']),
                         key=lambda p: p['path'])
        values = []
        for entry in entries:
            blob = (PROJECT / entry['path']).read_bytes()
            self.assertEqual((len(blob), hashlib.sha256(blob).hexdigest()), (entry['bytes'], entry['sha256']))
            values.append(json.loads(blob))
        return values

    def check_objects(self, target, name='check.json', operation='check-objects'):
        import contextlib
        import io
        import runpy
        from unittest.mock import patch
        output = self.work / name
        arguments = ['check_t0_catalog_delivery.py', operation, '--catalog', str(target), '--output', str(output)]
        if operation == 'check':
            arguments += ['--authorization', str(PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/public-baseline/authorization.json')]
        with patch.object(sys, 'argv', arguments), contextlib.redirect_stdout(io.StringIO()):
            try:
                runpy.run_path(str(PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py'),
                               run_name='__main__')
            except SystemExit as exc:
                code = exc.code
        return code, json.loads(output.read_bytes()) if output.exists() else {}

    def test_complete_prepared_objects_round_trip_without_changing_any_field(self):
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        originals = self.originals()
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            for value in originals:
                writer.add(value)
        restored = list(iter_prepared_objects(target))
        self.assertEqual(len(restored), 26)
        self.assertTrue(restored == originals, 'W/P bytes, metadata or identity changed')

    def test_both_frozen_public_sets_meet_the_storage_stop_loss_target(self):
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        for case, old_bytes in (('baseline', 1710684), ('longH', 3861096)):
            originals = self.originals(case)
            target = self.work / case
            with PreparedObjectWriter(target) as writer:
                for value in originals:
                    writer.add(value)
            files = list((target / 'objects').iterdir())
            self.assertEqual({p.name for p in files}, {'requests.pack', 'manifest.json'})
            self.assertLessEqual(sum(p.stat().st_size for p in files), old_bytes // 10)
            self.assertTrue(list(iter_prepared_objects(target)) == originals, case + ' round trip changed')

    def test_duplicate_prepared_keeps_one_object_and_both_caller_sources(self):
        import copy
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        first = self.originals()[0]
        second = copy.deepcopy(first)
        second['source']['attempt_id'] = 'PUBLIC-SECOND-ATTEMPT'
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            refs = [writer.add(first), writer.add(second)]
        restored = list(iter_prepared_objects(target))
        self.assertEqual(refs, [first['prepared_id'], first['prepared_id']])
        self.assertEqual(len(restored), 1)
        self.assertTrue(restored[0] == first, 'first object metadata was replaced')
        self.assertEqual(second['source']['attempt_id'], 'PUBLIC-SECOND-ATTEMPT')

    def test_inconsistent_prepared_bytes_and_bindings_are_rejected_even_for_duplicate_ids(self):
        import copy
        from t0_catalog import PreparedObjectWriter
        original = self.originals()[0]
        with PreparedObjectWriter(self.work / 'store') as writer:
            writer.add(original)
            for field, value in (('wire_utf8', original['wire_utf8'] + ' '),
                                 ('count_utf8', original['count_utf8'] + ' '),
                                 ('prepared_id', 'f' * 64), ('mapper_version', 'unknown-mapper')):
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    writer.add(changed)
            changed = copy.deepcopy(original)
            changed['catalog_metadata']['tool_versions'] = {'PUBLIC-CHANGED': 'invalid'}
            with self.assertRaises(ValueError):
                writer.add(changed)

    def test_legacy_public_objects_remain_readable_without_rewriting_them(self):
        from t0_catalog import iter_prepared_objects
        legacy = PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline'
        self.assertTrue(list(iter_prepared_objects(legacy)) == self.originals(), 'legacy prepared objects changed')

    def test_reader_rejects_corrupt_pack_index_projection_and_identity(self):
        import copy
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            for value in self.originals()[:2]:
                writer.add(value)
        path = target / 'objects/manifest.json'
        manifest = json.loads(path.read_bytes())
        changes = [('pack_sha256', '0' * 64), ('codec', 'unknown'), ('count_projection', 'unknown'),
                   ('count_omit', ['input']), ('schema_version', 'unknown')]
        for field, value in changes:
            changed = copy.deepcopy(manifest)
            changed[field] = value
            path.write_text(json.dumps(changed), encoding='utf-8')
            with self.subTest(field=field), self.assertRaises(ValueError):
                list(iter_prepared_objects(target))
        for field, value in (('offset', 1), ('bytes', -1), ('raw_bytes', 16 * 1024**2 + 1), ('count_bytes', 0)):
            changed = copy.deepcopy(manifest)
            changed['records'][0][field] = value
            path.write_text(json.dumps(changed), encoding='utf-8')
            with self.subTest(index_field=field), self.assertRaises(ValueError):
                list(iter_prepared_objects(target))
        for field in ('prepared_id', 'wire_sha256', 'count_payload_sha256', 'role_schema_sha256'):
            changed = copy.deepcopy(manifest)
            changed['records'][0]['metadata'][field] = 'f' * 64
            path.write_text(json.dumps(changed), encoding='utf-8')
            with self.subTest(metadata_field=field), self.assertRaises(ValueError):
                list(iter_prepared_objects(target))
        for case in ('overlap', 'duplicate'):
            changed = copy.deepcopy(manifest)
            if case == 'overlap':
                changed['records'][1]['offset'] = 0
            else:
                changed['records'].append(copy.deepcopy(changed['records'][0]))
            path.write_text(json.dumps(changed), encoding='utf-8')
            with self.subTest(case=case), self.assertRaises(ValueError):
                list(iter_prepared_objects(target))
        path.write_text(json.dumps(manifest), encoding='utf-8')
        pack = target / 'objects/requests.pack'
        pack.write_bytes(pack.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            list(iter_prepared_objects(target))

    def test_interrupted_writer_keeps_complete_prefix_and_marks_store_incomplete(self):
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        target = self.work / 'store'
        original = self.originals()[0]
        with self.assertRaises(RuntimeError):
            with PreparedObjectWriter(target) as writer:
                writer.add(original)
                raise RuntimeError('PUBLIC-STOP')
        manifest = json.loads((target / 'objects/manifest.json').read_bytes())
        self.assertFalse(manifest['complete'])
        self.assertEqual(manifest['reason'], 'RuntimeError')
        self.assertEqual(len(manifest['records']), 1)
        self.assertGreater((target / 'objects/requests.pack').stat().st_size, 0)
        with self.assertRaises(ValueError):
            list(iter_prepared_objects(target))

    def test_failed_filesystem_write_does_not_publish_an_unwritten_object(self):
        import io
        from unittest.mock import patch
        from t0_catalog import PreparedObjectWriter
        original_open = io.open

        class FailingDisk:
            def __init__(self, stream):
                self.stream, self.writes = stream, 0

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def write(self, value):
                self.writes += 1
                if self.writes == 2:
                    raise OSError('PUBLIC disk write limit')
                return self.stream.write(value)

        def opened(path, mode='r', *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return FailingDisk(stream) if Path(path).name == 'requests.pack' and mode == 'xb' else stream

        target = self.work / 'store'
        originals = self.originals()[:2]
        with patch('io.open', opened), self.assertRaises(OSError):
            with PreparedObjectWriter(target) as writer:
                for value in originals:
                    writer.add(value)
        manifest = json.loads((target / 'objects/manifest.json').read_bytes())
        self.assertFalse(manifest['complete'])
        self.assertEqual(len(manifest['records']), 1)
        self.assertEqual(manifest['records'][0]['metadata']['prepared_id'], originals[0]['prepared_id'])

    def test_storage_reproduction_is_byte_stable_without_expanding_plans(self):
        from t0_catalog import PreparedObjectWriter
        originals = self.originals()
        for name in ('first', 'second'):
            with PreparedObjectWriter(self.work / name) as writer:
                for value in originals:
                    writer.add(value)
        for name in ('requests.pack', 'manifest.json'):
            self.assertEqual((self.work / 'first/objects' / name).read_bytes(),
                             (self.work / 'second/objects' / name).read_bytes())

    def test_oversize_W_is_kept_in_full_as_incomplete_evidence(self):
        import copy
        import zlib
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        value = copy.deepcopy(self.originals()[0])
        for body_key, text_key, sha_key in (('wire_body', 'wire_utf8', 'wire_sha256'),
                                          ('count_body', 'count_utf8', 'count_payload_sha256')):
            value[body_key]['input'][0]['content'] += 'X' * (16 * 1024**2)
            value[text_key] = json.dumps(value[body_key], ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':'), allow_nan=False)
            value[sha_key] = hashlib.sha256(value[text_key].encode()).hexdigest()
        value['wire_bytes'] = len(value['wire_utf8'].encode())
        value['prepared_id'] = hashlib.sha256(json.dumps({k: value[k] for k in
            ('wire_sha256', 'count_payload_sha256', 'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')},
            ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        target = self.work / 'store'
        with self.assertRaises(ValueError):
            with PreparedObjectWriter(target) as writer:
                writer.add(value)
        manifest = json.loads((target / 'objects/manifest.json').read_bytes())
        self.assertFalse(manifest['complete'])
        self.assertEqual(len(manifest['records']), 1)
        pack = (target / 'objects/requests.pack').read_bytes()
        self.assertEqual(zlib.decompress(pack), value['wire_utf8'].encode())
        with self.assertRaises(ValueError):
            list(iter_prepared_objects(target))

    def test_independent_cli_accepts_object_storage_without_accepting_a_full_catalog(self):
        from t0_catalog import PreparedObjectWriter
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            for value in self.originals():
                writer.add(value)
        for case, directory in (('new', target), ('legacy', PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline')):
            code, result = self.check_objects(directory, case + '.json')
            self.assertEqual(code, 0, result)
            self.assertEqual(result['status'], 'object_store_verified_only')
            self.assertEqual(result['objects_verified'], 26)
            self.assertFalse(result['full_catalog_accepted'])
            self.assertEqual(result['provider_api_calls'], {'count': 0, 'generate': 0, 'other': 0})

    def test_recompute_rebuilds_component_digests_without_reading_or_writing_the_store(self):
        import io
        from unittest.mock import patch
        from t0_catalog import PreparedObjectWriter
        values, target = self.originals(), self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            for value in values:
                writer.add(value)
        expected = {'objects/' + p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in (target / 'objects').iterdir()}
        original_open = io.open

        def opened(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)) and Path(path).is_relative_to(target):
                raise AssertionError('recompute touched original store')
            return original_open(path, *args, **kwargs)

        with patch('io.open', opened):
            with PreparedObjectWriter(target, recompute=True) as rebuilt:
                for value in values:
                    rebuilt.add(value)
        self.assertEqual(rebuilt.components, expected)

    def test_independent_cli_rejects_corrupt_storage_and_partial_without_accepting_catalog(self):
        import copy
        from t0_catalog import PreparedObjectWriter
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            for value in self.originals()[:2]:
                writer.add(value)
        path = target / 'objects/manifest.json'
        manifest = json.loads(path.read_bytes())
        for index, (field, value) in enumerate((('codec', 'unknown'), ('count_omit', ['input']),
                ('complete', False), ('pack_sha256', '0' * 64))):
            changed = copy.deepcopy(manifest)
            changed[field] = value
            path.write_text(json.dumps(changed), encoding='utf-8')
            code, result = self.check_objects(target, 'reject-' + str(index) + '.json')
            self.assertEqual(code, 2)
            self.assertFalse(result['complete'])
        for index, field in enumerate(('offset', 'raw_bytes', 'count_bytes')):
            changed = copy.deepcopy(manifest)
            changed['records'][0][field] = -1
            path.write_text(json.dumps(changed), encoding='utf-8')
            code, result = self.check_objects(target, 'index-' + str(index) + '.json')
            self.assertEqual(code, 2)
            self.assertFalse(result['complete'])
        changed = copy.deepcopy(manifest)
        changed['records'][0]['metadata']['prepared_id'] = 'f' * 64
        path.write_text(json.dumps(changed), encoding='utf-8')
        code, result = self.check_objects(target, 'identity.json')
        self.assertEqual(code, 2)
        self.assertFalse(result['complete'])

    def test_full_checker_accepts_storage_conversion_but_still_rejects_incomplete_coverage(self):
        from t0_catalog import PreparedObjectWriter
        legacy = PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline'
        target = self.work / 'catalog'
        with PreparedObjectWriter(target) as writer:
            for value in self.originals():
                writer.add(value)
        catalog = json.loads((legacy / 'catalog.json').read_bytes())
        catalog['schema_version'] = 'T0-request-catalog-0.2.0'
        for name in list(catalog['components']):
            if name.startswith('objects/'):
                del catalog['components'][name]
            else:
                (target / name).write_bytes((legacy / name).read_bytes())
        catalog['components'].update(writer.components)
        (target / 'catalog.json').write_text(json.dumps(catalog), encoding='utf-8')
        code, result = self.check_objects(target, 'full.json', 'check')
        self.assertEqual(code, 0, result)
        coverage = json.loads((target / 'coverage.json').read_bytes())
        coverage.update(complete=False, reasons=['PUBLIC-incomplete'])
        blob = json.dumps(coverage).encode()
        (target / 'coverage.json').write_bytes(blob)
        catalog['components']['coverage.json'] = {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
        (target / 'catalog.json').write_text(json.dumps(catalog), encoding='utf-8')
        code, result = self.check_objects(target, 'partial-full.json', 'check')
        self.assertEqual(code, 2)
        self.assertIn('catalog_incomplete', result['errors'])

    def test_development_validation_cli_denies_offline_before_reading_development_objects(self):
        import contextlib
        import io
        import runpy
        from unittest.mock import patch
        script = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py'
        original_open = io.open

        def opened(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)) and Path(path).is_relative_to(PROJECT / 'data/ticket12-t0/catalog-0.1.0'):
                raise AssertionError('development read before program acceptance')
            return original_open(path, *args, **kwargs)

        output = io.StringIO()
        with patch('io.open', opened), patch.object(sys, 'argv', [str(script), '--validate-storage']), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(script), run_name='__main__')
        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual(json.loads(output.getvalue())['reason'], 't0_domain_required')

    def test_storage_does_not_grant_prepare_generation_or_count_export_permissions(self):
        import contextlib
        import io
        from model_adapter import ModelAdapter
        from provider_openai import MODEL
        from t0_catalog import PreparedObjectWriter, main
        from token_counting import main as count_main
        target = self.work / 'store'
        with PreparedObjectWriter(target) as writer:
            writer.add(self.originals()[0])

        def sender(*args, **kwargs):
            raise AssertionError('supplier sender reached')

        adapter = ModelAdapter(sender, capability_binding={'execution_kind': 't0_development_catalog',
            'model_id': MODEL, 'provenance': 'synthetic', 'project_id': 'UNBOUND-T0-DEV-CATALOG'})
        denied = adapter.invoke({'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': 't0_development_catalog'})
        self.assertEqual(denied['status'], 'preflight_denied')
        self.assertFalse(denied['attempted'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = count_main(['export', '--prepared', str(target / 'objects/manifest.json'),
                               '--output', str(self.work / 'count.json')])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['provider_requests_sent'], 0)
        self.assertFalse((self.work / 'count.json').exists())
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(['prepare', '--authorization',
                str(PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/public-baseline/authorization.json'),
                '--output', str(self.work / 'forbidden-generation')])
        self.assertEqual(code, 2)
        report = json.loads((self.work / 'forbidden-generation/run.json').read_bytes())
        self.assertIn('storage_package_new_plans_forbidden', report['reasons'])
        self.assertFalse((self.work / 'forbidden-generation/roots.jsonl').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction boundary')
    def test_object_directory_junction_is_rejected_before_following_its_target(self):
        from t0_catalog import PreparedObjectWriter, iter_prepared_objects
        other, target = self.work / 'other-store', self.work / 'store'
        with PreparedObjectWriter(other) as writer:
            writer.add(self.originals()[0])
        target.mkdir()
        junction = target / 'objects'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(other / 'objects')],
                       check=True, capture_output=True)
        try:
            with self.assertRaisesRegex(ValueError, 'reparse_path'):
                list(iter_prepared_objects(target))
            code, result = self.check_objects(target)
            self.assertEqual(code, 2)
            self.assertFalse(result['complete'])
        finally:
            junction.rmdir()


class RecoveryPilotTests(unittest.TestCase):
    """New public CLI behavior, using the frozen PUBLIC facts without regeneration."""
    def setUp(self):
        self.work = PROJECT / '.tmp/ticket12-t0/recovery-pilot-20261019' / os.environ['THESIS_BATCH_CHECK_LABEL'] / hashlib.sha256(self._testMethodName.encode()).hexdigest()[:12]
        self.work.mkdir(parents=True)
        self.control = PROJECT / '.scratch/ticket12-budget-20261018'
        self.package = json.loads((self.control / 'recovery-pilot-package-20261019.json').read_bytes())

    def authorization(self):
        auth = json.loads((PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/public-baseline/authorization.json').read_bytes())
        auth.update(schema_version='t0-a-recovery-authorization-0.1.0', base=self.package['base'],
            contract=self.package['contract'], human_confirmation=self.package['human_confirmation'],
            operation='controlled_recovery', execution_stage='pilot',
            resource_package={'path': '.scratch/ticket12-budget-20261018/recovery-pilot-package-20261019.json',
                'sha256': '6da3c084bc2b1b298994f692db13d9b885dbd97cf180904e7a31cfefcb61c93b'},
            source_receipt=None, old_catalog=self.package['old_catalog'])
        original = PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline/catalog.json'
        auth['old_catalog'] = {'path': original.relative_to(PROJECT).as_posix(),
            'bytes': original.stat().st_size, 'sha256': hashlib.sha256(original.read_bytes()).hexdigest()}
        path = self.work / 'authorization.json'
        path.write_text(json.dumps(auth), encoding='utf-8')
        return path, auth

    def cli(self, auth, *extra, name='pilot'):
        import contextlib
        import io
        from t0_catalog import main
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(['prepare', '--authorization', str(auth), '--output', str(self.work / name), *extra])
        return code, json.loads((self.work / name / 'run.json').read_bytes())

    def checker(self, operation, auth, name, *extra):
        import contextlib
        import io
        import runpy
        from unittest.mock import patch
        path = self.work / name
        with patch.object(sys, 'argv', ['checker', operation, '--authorization', str(auth), '--output', str(path), *extra]), contextlib.redirect_stdout(io.StringIO()):
            try:
                runpy.run_path(str(self.control / 'diagnostics/check_t0_catalog_delivery.py'), run_name='__main__')
            except SystemExit as exc:
                code = exc.code
        return code, json.loads(path.read_bytes())

    def test_full_recovery_stage_is_denied_before_any_plan_attempt(self):
        path, auth = self.authorization()
        auth['execution_stage'] = 'recovery'
        path.write_text(json.dumps(auth), encoding='utf-8')
        code, report = self.cli(path)
        self.assertEqual(code, 2)
        self.assertIn('pilot_stage_not_authorized', report['reasons'])
        self.assertFalse((self.work / 'pilot/roots.jsonl').exists())

    def test_independent_snapshot_binds_the_frozen_public_selection_without_exposing_identity(self):
        path, auth = self.authorization()
        code, report = self.checker('snapshot', path, 'receipt.json')
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'PUBLIC_recovery_source_bound_only')
        expected = json.loads((PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline/source-index.json').read_bytes())
        self.assertEqual(report['selected_roots'], expected['selected_roots'])
        self.assertEqual(len(report['pilot_roots']), 1)
        self.assertEqual(report['identity_key_body_reads'], 1)
        self.assertFalse(report['full_catalog_accepted'])
        raw = (self.work / 'receipt.json').read_text(encoding='utf-8')
        self.assertNotIn('PUBLIC-IDENTITY', raw)
        self.assertNotIn('PUBLIC-DEV', raw)

    def bound_authorization(self):
        path, auth = self.authorization()
        code, receipt = self.checker('snapshot', path, 'receipt.json')
        self.assertEqual(code, 0)
        raw = (self.work / 'receipt.json').read_bytes()
        auth['source_receipt'] = {'path': (self.work / 'receipt.json').relative_to(PROJECT).as_posix(),
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        path.write_text(json.dumps(auth), encoding='utf-8')
        return path, auth

    def test_prepare_commits_the_frozen_public_plans_and_preserves_complete_prepared_bytes(self):
        from t0_catalog import iter_prepared_objects
        path, auth = self.bound_authorization()
        code, report = self.cli(path)
        self.assertEqual(code, 0, report)
        self.assertTrue(report['complete'])
        self.assertEqual(report['plans'], 3)
        self.assertEqual(report['N'], 26)
        checkpoint = json.loads((self.work / 'pilot/checkpoint.json').read_bytes())
        self.assertEqual(len(checkpoint['committed']), 3)
        originals = {p['prepared_id']: p for p in iter_prepared_objects(PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline')}
        actual = {p['prepared_id']: p for p in iter_prepared_objects(self.work / 'pilot')}
        self.assertEqual(actual, originals)

    def test_resume_keeps_committed_prefix_and_retries_only_the_uncommitted_plan(self):
        from unittest.mock import patch
        path, auth = self.bound_authorization()
        original_replace = os.replace
        def replace(source, target):
            if Path(target).name == 'checkpoint.json' and len(json.loads(Path(source).read_bytes())['committed']) == 2:
                raise OSError('PUBLIC checkpoint write failure')
            return original_replace(source, target)
        with patch('os.replace', replace):
            code, failed = self.cli(path)
        self.assertEqual(code, 2)
        checkpoint_path = self.work / 'pilot/checkpoint.json'
        first = json.loads(checkpoint_path.read_bytes())['committed'][0]
        code, restored = self.cli(path, '--resume')
        self.assertEqual(code, 0, restored)
        final = json.loads(checkpoint_path.read_bytes())
        self.assertEqual(final['committed'][0], first)
        self.assertEqual(len(final['committed']), 3)
        self.assertEqual(restored['N'], 26)
        self.assertEqual(restored['plans'], 3)

    def test_recompute_uses_frozen_inputs_without_reading_first_output_bodies_or_identity_key(self):
        import io
        from unittest.mock import patch
        path, auth = self.bound_authorization()
        code, report = self.cli(path)
        self.assertEqual(code, 0)
        original_open = io.open
        target = self.work / 'pilot'
        forbidden = {target / name for name in ('roots.jsonl', 'requests.jsonl', 'dependencies.jsonl')}
        forbidden.add(PROJECT / auth['sources']['identity_key']['path'])
        def opened(file, mode='r', *args, **kwargs):
            actual = Path(file)
            if 'r' in mode and (actual in forbidden or actual.is_relative_to(target / 'objects')):
                raise AssertionError('first output body or identity key read during recompute')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            code, ignored = self.cli(path, '--recompute-digests')
        self.assertEqual(code, 0)
        result = json.loads((target / 'checks/reproduction.json').read_bytes())
        self.assertTrue(result['match'])
        self.assertEqual(result['recomputed_N'], 26)
        self.assertFalse(result['second_catalog_written'])

    def test_independent_pilot_delivery_covers_all_plans_but_never_accepts_full_A(self):
        path, auth = self.bound_authorization()
        self.assertEqual(self.cli(path)[0], 0)
        code, report = self.checker('check-pilot', path, 'pilot-check.json', '--catalog', str(self.work / 'pilot'))
        self.assertEqual(code, 0, report)
        self.assertEqual(report['status'], 'PUBLIC_recovery_pilot_verified_only')
        self.assertEqual(report['plans'], 3)
        self.assertEqual(report['N'], 26)
        self.assertFalse(report['full_catalog_accepted'])
        code, full = self.checker('check', path, 'full-check.json', '--catalog', str(self.work / 'pilot'))
        self.assertEqual(code, 2)
        self.assertIn('pilot_not_full_delivery', full['errors'])

    def test_independent_checker_rejects_forged_dependency_body_even_when_component_hashes_are_updated(self):
        path, auth = self.bound_authorization()
        self.assertEqual(self.cli(path)[0], 0)
        target = self.work / 'pilot'
        dependency = target / 'dependencies.jsonl'
        values = [json.loads(row) for row in dependency.read_bytes().splitlines()]
        def forge(value):
            if isinstance(value, dict):
                if 'raw_utf8' in value and isinstance(value.get('source'), dict) and 'component_path' in value['source']:
                    value['raw_utf8'] += 'PUBLIC-forged-body'
                    return True
                return any(forge(v) for v in value.values())
            return isinstance(value, list) and any(forge(v) for v in value)
        self.assertTrue(forge(values[0]))
        raw = b''.join((json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode() for v in values)
        dependency.write_bytes(raw)
        catalog_path = target / 'catalog.json'
        catalog = json.loads(catalog_path.read_bytes())
        catalog['components']['dependencies.jsonl'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        catalog_path.write_text(json.dumps(catalog), encoding='utf-8')
        code, report = self.checker('check-pilot', path, 'forged-check.json', '--catalog', str(target))
        self.assertEqual(code, 2, report)
        self.assertIn('pilot_dependency_source_mismatch', report['errors'])

    def test_prepare_reports_per_root_costs_and_passes_the_source_aware_independent_check(self):
        path, auth = self.bound_authorization()
        code, report = self.cli(path)
        self.assertEqual(code, 0)
        costs = json.loads((self.work / 'pilot/checks/prepare-costs.json').read_bytes())
        self.assertEqual(costs['purpose'], 'prepare')
        self.assertEqual(len(costs['by_root']), 1)
        root = next(iter(costs['by_root'].values()))
        self.assertEqual(root['plans'], 3)
        self.assertEqual(root['N'], 26)
        self.assertEqual(root['wire_bytes'], 386237)
        self.assertEqual(root['count_payload_bytes'], 384183)
        self.assertGreater(root['seconds'], 0)
        self.assertGreater(root['read_transfer_bytes'], 0)
        self.assertGreater(root['write_transfer_bytes'], 0)
        self.assertGreater(root['sampled_peak_private_bytes'], 0)
        code, verified = self.checker('check-pilot', path, 'source-aware.json', '--catalog', str(self.work / 'pilot'))
        self.assertEqual(code, 0, verified)
        self.assertGreater(verified['dependency_templates_verified'], 0)

    def test_unapproved_authorization_and_receipt_paths_are_denied_before_reading_their_bodies(self):
        import io
        from unittest.mock import patch
        path, auth = self.authorization()
        original_open = io.open
        blocked = {PROJECT / auth['sources']['identity_key']['path'], PROJECT / 'AGENTS.md'}
        def opened(file, mode='r', *args, **kwargs):
            if 'r' in mode and Path(file) in blocked:
                raise AssertionError('unapproved authorization reached a protected body')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            old = PROJECT / '.tmp/ticket12-t0/diagnosis-20261019/public-baseline/authorization.json'
            code, report = self.cli(old, name='old')
            self.assertEqual(code, 2)
            self.assertIn('old_authorization_not_pilot', report['reasons'])
            entry = next(p for p in self.package['protected_before'] if p['path'] == 'AGENTS.md')
            auth['source_receipt'] = entry
            path.write_text(json.dumps(auth), encoding='utf-8')
            code, report = self.cli(path, name='unsafe')
            self.assertEqual(code, 2)
            self.assertIn('pilot_receipt_path_not_allowed', report['reasons'])

    def test_development_source_substitution_is_denied_before_identity_or_receipt_reads(self):
        import io
        from unittest.mock import patch
        path, auth = self.authorization()
        auth.update(scope='development_catalog_only', candidate='0' * 40)
        path.write_text(json.dumps(auth), encoding='utf-8')
        original_open = io.open
        def opened(file, mode='r', *args, **kwargs):
            if 'r' in mode and Path(file).name == 'id-key.bin':
                raise AssertionError('unaccepted program reached identity key')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            code, report = self.cli(path)
            self.assertEqual(code, 2)
            self.assertIn('pilot_source_set_mismatch', report['reasons'])
            code, report = self.checker('snapshot', path, 'denied.json')
            self.assertEqual(code, 2)
            self.assertIn('pilot_source_set_mismatch', report['errors'])

    def test_development_program_record_path_is_rejected_before_body_expansion(self):
        import io
        from unittest.mock import patch
        path, auth = self.authorization()
        auth.update(scope='development_catalog_only', candidate='0' * 40,
            sources=self.package['development_sources'], old_catalog=self.package['old_catalog'],
            program_acceptance={'path': 'AGENTS.md', 'sha256': '0' * 64})
        path.write_text(json.dumps(auth), encoding='utf-8')
        original_open = io.open
        def opened(file, mode='r', *args, **kwargs):
            if 'r' in mode and (Path(file).name == 'id-key.bin' or Path(file) == PROJECT / 'AGENTS.md'):
                raise AssertionError('unaccepted program reached protected body')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            code, report = self.cli(path)
            self.assertEqual(code, 2)
            self.assertIn('pilot_program_record_path_not_allowed', report['reasons'])
            code, report = self.checker('snapshot', path, 'program-denied.json')
            self.assertEqual(code, 2)
            self.assertIn('pilot_program_record_path_not_allowed', report['errors'])

    def test_snapshot_rejects_unbound_old_catalog_before_reading_identity(self):
        import io
        from unittest.mock import patch
        path, auth = self.authorization()
        auth['old_catalog'] = {'path': 'AGENTS.md', 'bytes': 1, 'sha256': '0' * 64}
        path.write_text(json.dumps(auth), encoding='utf-8')
        original_open = io.open
        def opened(file, mode='r', *args, **kwargs):
            if 'r' in mode and (Path(file).name == 'id-key.bin' or Path(file) == PROJECT / 'AGENTS.md'):
                raise AssertionError('unbound old catalog reached protected body')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            code, report = self.checker('snapshot', path, 'old-denied.json')
        self.assertEqual(code, 2)
        self.assertIn('pilot_original_catalog_not_allowed', report['errors'])

    def test_full_recovery_flags_and_old_bodies_are_not_available_in_the_pilot(self):
        path, auth = self.authorization()
        code, report = self.cli(path, '--recover-from', 'data/ticket12-t0/catalog-0.1.0')
        self.assertEqual(code, 2)
        self.assertIn('pilot_full_recovery_not_authorized', report['reasons'])
        for name in ('objects/unused.json', 'dependencies.jsonl', 'checks/probes.jsonl'):
            with self.assertRaisesRegex(OSError, 'pilot_old_body_read_forbidden'):
                (PROJECT / 'data/ticket12-t0/catalog-0.1.0' / name).open('rb')
        with self.assertRaisesRegex(OSError, 'pilot_identity_read_not_authorized'):
            (PROJECT / self.package['development_sources']['identity_key']['path']).open('rb')

    def test_completed_resume_keeps_the_delivery_unchanged_and_recomputation_remains_independent(self):
        import io
        from unittest.mock import patch
        path, auth = self.bound_authorization()
        code, report = self.cli(path)
        self.assertEqual(code, 0, report)
        target = self.work / 'pilot'
        catalog = json.loads((target / 'catalog.json').read_bytes())
        stamps = {name: ((target / name).stat().st_mtime_ns, (target / name).read_bytes())
            for name in (*catalog['components'], 'catalog.json')}
        code, report = self.cli(path, '--resume')
        self.assertEqual(code, 0, report)
        self.assertEqual({name: ((target / name).stat().st_mtime_ns, (target / name).read_bytes())
            for name in stamps}, stamps)
        original_open = io.open
        forbidden = {target / name for name in ('roots.jsonl', 'requests.jsonl', 'dependencies.jsonl')}
        forbidden.add(PROJECT / auth['sources']['identity_key']['path'])
        def opened(file, mode='r', *args, **kwargs):
            actual = Path(file)
            if 'r' in mode and (actual in forbidden or actual.is_relative_to(target / 'objects')):
                raise AssertionError('recompute read the first delivery or identity key')
            return original_open(file, mode, *args, **kwargs)
        with patch('io.open', opened):
            code, ignored = self.cli(path, '--recompute-digests')
        self.assertEqual(code, 0)
        reproduction = json.loads((target / 'checks/reproduction.json').read_bytes())
        self.assertTrue(reproduction['match'])
        self.assertEqual(reproduction['recomputed_N'], 26)
        code, checked = self.checker('check-pilot', path, 'final-check.json', '--catalog', str(target))
        self.assertEqual(code, 0, checked)
        self.assertEqual(checked['N'], 26)
        self.assertGreater(checked['dependency_templates_verified'], 0)


if __name__ == '__main__':
    unittest.main()
