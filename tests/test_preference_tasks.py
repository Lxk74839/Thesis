"""Ticket08 behavior through the approved data preparation CLI."""

import json
import hashlib
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class PreferenceTasksTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def write(self, relative, value):
        path = self.root / 'input' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8'))
        return path

    def rows(self, relative, values):
        path = self.root / 'input' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b''.join((json.dumps(v, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8') for v in values))
        return path

    def binding(self, path):
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def fixture(self):
        self.users = [f'fixture-user-{i:03}' for i in range(1, 6)]
        titles = {'P001': '长粒白米 1 kg', 'P002': '燕麦 1 kg', 'P003': '玉米 1 kg',
                  'P004': '白米 2 kg - Ships Free over $30', 'P005': 'Golden Star 大麦 1 kg', 'P006': '小米 500 g'}
        crops = ['rice', 'oats', 'corn', 'rice', 'barley', 'millet']
        self.catalog = [{'parent_asin': p, 'crop': crop, 'metadata': {
            'parent_asin': p, 'title': title, 'average_rating': 4.9, 'rating_number': 9999,
            'price': 123.45, 'description': ['CLOSED_DESCRIPTION'], 'details': {'Brand': 'CLOSED_BRAND'}},
            'source_line': i + 1, 'source_sha256': '0' * 64}
            for i, ((p, title), crop) in enumerate(zip(titles.items(), crops))]
        self.ledger = []

        def event(user, parent, time, rating, text):
            review = {'user_id': user, 'parent_asin': parent, 'asin': 'variant-' + parent,
                      'timestamp': time, 'rating': float(rating), 'title': 'CLOSED_HISTORY_TITLE',
                      'text': text, 'images': [], 'helpful_vote': 100, 'verified_purchase': True}
            self.ledger.append({'review': review, 'timestamp_ms': time,
                'timestamp_utc': 'fixture-UTC', 'source_references': [{'source_line': len(self.ledger) + 1,
                'selected_row': len(self.ledger) + 1, 'line_sha256': hashlib.sha256(json.dumps(review, sort_keys=True).encode()).hexdigest()}]})

        self.add_event = event

        event(self.users[0], 'P001', 1000, 5, '<p>好米5星，当时$12，也想试试P005。</p><p>https://example.invalid/rice rice@example.invalid</p>')
        event(self.users[0], 'P002', 1500, 1, '低分也已见')
        event(self.users[0], 'P003', 2000, 4, '')
        event(self.users[0], 'P005', 4000, 5, 'PRIVATE_TARGET_001')
        for u in self.users[1:]:
            event(u, 'P001', 1000, 4, '合成较早正文')
            event(u, 'P006', 5000, 5, 'PRIVATE_TARGET_OTHER')
        event(self.users[1], 'P005', 500, 1, '评价账号的更早低评分不得进入背景')
        event('bg-A', 'P004', 3999, 5, '背景')
        event('bg-B', 'P004', 2000, 2, '')
        event('bg-A', 'P005', 1000, 4, '背景')
        event('bg-C', 'P006', 4000, 5, '等时背景')
        event('bg-D', 'P006', 4001, 5, '未来背景')
        event('bg-A', 'P004', 6000, 1, '最新已见商品，该背景账号不合格')
        self.eligibility = [{'user_id': u, 'status': 'qualified', 'latest_timestamp_ms': 4000 if i == 0 else 5000,
            'prior_positive_product_count': 1, 'prior_positive_parent_asins': ['P001'],
            'seen_parent_asins': ['P001', 'P002', 'P003'] if i == 0 else (['P001', 'P005'] if i == 1 else ['P001']),
            'target_parent_asin': 'P005' if i == 0 else 'P006',
            'target_source_references': [r['source_references'][0] for r in self.ledger
                if r['review']['user_id'] == u and r['timestamp_ms'] == (4000 if i == 0 else 5000)], 'reasons': []}
            for i, u in enumerate(self.users)]
        self.eligibility += [{'user_id': u, 'status': 'excluded', 'reasons': ['fixture_excluded']} for u in ('bg-A', 'bg-B', 'bg-C', 'bg-D')]
        self.assignments = [{'user_id': u, 'split': 'dev' if i == 0 else 'test',
            'split_hash': hashlib.sha256(u.encode()).hexdigest(), 'assignment_reason': 'hash_fill' if i == 0 else 'hash_remainder'}
            for i, u in enumerate(self.users)]
        self.key_path = self.root / 'input/data/id-key.bin'
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(b'k' * 32)
        self.refresh()

    def refresh(self):
        cat_path = self.rows('data/catalog.jsonl', self.catalog)
        cat_record = self.write('records/catalog/catalog.json', {'stage': 'catalog', 'status': 'catalog_complete',
            'scope_version': 'fixture', 'catalog_path': 'data/catalog.jsonl', 'catalog_sha256': self.binding(cat_path)['sha256']})
        values = {'clean': self.ledger, 'text': [r for r in self.ledger if r['review']['text'].strip()],
                  'accounts': self.eligibility, 'products': [], 'quarantine': [], 'audit': []}
        self.clean = {'stage': 'review_clean', 'status': 'cleaning_complete', 'scope_version': 'fixture',
            'rules_version': 'review-cleaning-1.0.0', 'formal_clean_status': 'built', 'user_qualification_status': 'complete',
            'catalog_record_path': 'records/catalog/catalog.json', 'catalog_record_sha256': self.binding(cat_record)['sha256'],
            'catalog_sha256': self.binding(cat_path)['sha256'], 'counts': {'raw_accounts': 9, 'qualified_accounts': 5,
            'catalog_products': 6, 'clean_reviews': len(self.ledger), 'text_reviews': len(values['text'])},
            'window': {'cutoff_exclusive_ms': 1694550038852}}
        for name, rows in values.items():
            path = self.rows('data/' + name + '.jsonl', rows)
            self.clean[name + '_path'] = 'data/' + name + '.jsonl'
            self.clean[name + '_sha256'] = self.binding(path)['sha256']
        rules_path = self.write('config/review-cleaning-1.0.0.json', json.loads((PROJECT / 'config/review-cleaning-1.0.0.json').read_text('utf-8')))
        self.clean.update(rules_path='config/review-cleaning-1.0.0.json', rules_sha256=self.binding(rules_path)['sha256'])
        self.clean_path = self.write('records/cleaning/clean.json', self.clean)
        ca = self.write('records/cleaning/acceptance.json', {'status': 'accepted_ticket06_cleaning_and_qualification_only',
            'counts': self.clean['counts'], 'dependencies_sha256': {'records/cleaning/clean.json': self.binding(self.clean_path)['sha256']},
            'component_sha256': {n: self.clean[n + '_sha256'] for n in values}})
        erratum = self.write('records/cleaning/erratum.json', {'type': 'metadata_erratum', 'affected_field': 'stable_serialization',
            'affected_record_path': 'records/cleaning/clean.json', 'affected_record_sha256': self.binding(self.clean_path)['sha256'],
            'component_format_checks': {n: {'path': self.clean[n + '_path'], 'sha256': self.clean[n + '_sha256']} for n in values}})
        sp = self.rows('data/splits/accounts.jsonl', self.assignments)
        ex = self.rows('data/splits/exposure.jsonl', [{'user_id': u, 'agent_account_result_view': 'unknown'} for u in self.users])
        self.split = {'stage': 'user_split', 'status': 'split_complete', 'rules_version': 'user-split-1.0.0',
            'scope_version': 'fixture', 'user_split_status': 'complete', 'cleaning_record_sha256': self.binding(self.clean_path)['sha256'],
            'catalog_sha256': self.clean['catalog_sha256'], 'accounts_path': 'data/splits/accounts.jsonl', 'accounts_sha256': self.binding(sp)['sha256'],
            'exposure_path': 'data/splits/exposure.jsonl', 'exposure_sha256': self.binding(ex)['sha256'],
            'counts': {'qualified_accounts': 5, 'dev_accounts': 1, 'test_accounts': 4, 'source_accounts': 9}}
        self.split_path = self.write('records/splits/split.json', self.split)
        sa = self.write('records/splits/acceptance.json', {'status': 'accepted_ticket07_split_component_only',
            'rules_version': self.split['rules_version'], 'counts': self.split['counts'],
            'dependencies_sha256': {'records/splits/split.json': self.binding(self.split_path)['sha256']},
            'component_sha256': {'accounts': self.split['accounts_sha256'], 'exposure': self.split['exposure_sha256']}})
        self.config = {'version': 'preference-task-1.0.0', 'approval': 'approved', 'input_profile': 'text_portrait_trial_v1',
            'text_policy_version': 'finite-text-1.0.0', 'access_profile': 'api_only_no_host_io_v1',
            'upstream_acceptances': {'cleaning': self.binding(ca), 'cleaning_erratum': self.binding(erratum), 'split': self.binding(sa)},
            'identity_key': self.binding(self.key_path), 'contract_version': {'version': 'preference-task-1.0.0',
            'approved_document_sha256': '21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a'}}
        self.config_path = self.write('config/preference-task-1.0.0.json', self.config)

    def run_tasks(self, output='output', probe=None):
        return subprocess.run([sys.executable, str(PROJECT / 'prepare_data.py'), '--stage', 'preference_tasks',
            '--cleaning-record', str(self.clean_path), '--split-record', str(self.split_path),
            '--task-config', str(self.config_path), '--output-root', str(self.root / output),
            *(['--access-probe', str(probe)] if probe else [])], capture_output=True, text=True, encoding='utf-8')

    def record(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def output_rows(self, name, output='output'):
        path = self.root / output / 'data/preference-tasks/fixture/preference-task-1.0.0' / name
        return [json.loads(s) for s in path.read_text('utf-8').splitlines()]

    def test_01_required_parameters_have_private_safe_failure(self):
        result = subprocess.run(
            [sys.executable, str(PROJECT / 'prepare_data.py'), '--stage',
             'preference_tasks', '--output-root', str(self.root / 'output')],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'preference_tasks_incomplete')
        self.assertEqual(report['error']['code'], 'invalid_task')
        self.assertFalse((self.root / 'output').exists())

    def test_02_unapproved_profile_never_publishes(self):
        self.fixture()
        self.config['approval'] = 'pending_confirmation'
        self.write('config/preference-task-1.0.0.json', self.config)
        result = self.run_tasks()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'needs_confirmation')
        self.assertFalse((self.root / 'output').exists())

    def test_03_catalog_is_a_complete_title_crop_projection(self):
        self.fixture()
        report = self.record(self.run_tasks())
        rows = self.output_rows('model/catalog.jsonl')
        self.assertEqual(len(rows), 6)
        self.assertEqual([r['parent_asin'] for r in rows], ['P001', 'P002', 'P003', 'P004', 'P005', 'P006'])
        self.assertTrue(all(set(r) == {'parent_asin', 'title', 'crop'} for r in rows))
        self.assertEqual(rows[4]['title'], 'Golden Star 大麦 1 kg')
        self.assertEqual(report['formal_package_status'], 'not_built')
        self.assertEqual(report['model_execution_status'], 'not_run')

    def test_04_only_the_approved_bound_upstream_chain_is_consumed(self):
        for kind in ('profile', 'unknown_config', 'clean_bytes', 'erratum', 'split_acceptance', 'split_clean_binding'):
            with self.subTest(kind=kind):
                self.fixture()
                if kind == 'profile': self.config['input_profile'] = 'open_everything'
                if kind == 'unknown_config': self.config['target_hint'] = 'DO_NOT_ECHO_PRIVATE'
                if kind == 'clean_bytes':
                    (self.root / 'input/data/clean.jsonl').write_bytes(b'DO_NOT_ECHO_PRIVATE')
                if kind == 'erratum':
                    path = self.root / 'input/records/cleaning/erratum.json'
                    value = json.loads(path.read_text('utf-8')); value['affected_record_sha256'] = '0' * 64
                    self.write('records/cleaning/erratum.json', value)
                    self.config['upstream_acceptances']['cleaning_erratum'] = self.binding(path)
                if kind == 'split_acceptance':
                    path = self.root / 'input/records/splits/acceptance.json'
                    value = json.loads(path.read_text('utf-8')); value['status'] = 'not_accepted'
                    self.write('records/splits/acceptance.json', value)
                    self.config['upstream_acceptances']['split'] = self.binding(path)
                if kind == 'split_clean_binding':
                    self.split['cleaning_record_sha256'] = '0' * 64
                    self.write('records/splits/split.json', self.split)
                self.write('config/preference-task-1.0.0.json', self.config)
                result = self.run_tasks('failure-' + kind)
                self.assertEqual(result.returncode, 2)
                self.assertIn(json.loads(result.stdout)['error']['code'], ('unapproved_protocol', 'dependency_mismatch'))
                self.assertNotIn('DO_NOT_ECHO_PRIVATE', result.stdout + result.stderr)
                self.assertFalse((self.root / ('failure-' + kind)).exists())

    def test_05_strict_positive_foreground_and_private_targets_stay_separate(self):
        self.fixture()
        report = self.record(self.run_tasks())
        evaluation = self.output_rows('private/evaluation.jsonl')
        first = next(r for r in evaluation if r['source_user_id'] == self.users[0])
        task = next(r for r in self.output_rows('model/tasks.jsonl') if r['task_id'] == first['task_id'])
        self.assertEqual([(h['parent_asin'], h['timestamp_ms'], h['rating']) for h in task['history']], [('P001', 1000, 5.0)])
        self.assertEqual(set(task['history'][0]), {'parent_asin', 'timestamp_ms', 'rating', 'text'})
        self.assertEqual(first['target_parent_asin'], 'P005')
        self.assertEqual(first['target_review']['text'], 'PRIVATE_TARGET_001')
        self.assertEqual(first['reference_answer']['other_candidates'], 'unobserved_unlabeled')
        self.assertEqual(first['split'], 'dev')
        public = json.dumps(self.output_rows('model/tasks.jsonl'))
        self.assertNotIn('PRIVATE_TARGET_', public)
        self.assertNotIn('CLOSED_HISTORY_TITLE', public)
        self.assertNotIn('source_user_id', public)
        self.assertEqual(report['counts']['root_tasks'], 5)
        self.assertEqual(report['counts']['history_events'], 5)

    def test_06_all_unseen_candidates_include_zero_data_and_ignore_source_order(self):
        self.fixture()
        self.record(self.run_tasks())
        before = self.output_rows('model/tasks.jsonl')
        first_id = next(r['task_id'] for r in self.output_rows('private/evaluation.jsonl') if r['source_user_id'] == self.users[0])
        task = next(r for r in before if r['task_id'] == first_id)
        self.assertEqual(task['seen_parent_asins'], ['P001', 'P002', 'P003'])
        self.assertEqual(task['candidate_parent_asins'], ['P004', 'P005', 'P006'])
        self.catalog.reverse(); self.eligibility.reverse(); self.ledger.reverse(); self.assignments.reverse()
        self.refresh()
        self.record(self.run_tasks('reversed'))
        self.assertEqual(before, self.output_rows('model/tasks.jsonl', 'reversed'))

    def test_07_background_excludes_every_evaluation_account_and_uses_each_cutoff(self):
        self.fixture()
        self.record(self.run_tasks())
        ids = {r['source_user_id']: r['task_id'] for r in self.output_rows('private/evaluation.jsonl')}
        tasks = {r['task_id']: r for r in self.output_rows('model/tasks.jsonl')}
        expected = [
            {'parent_asin': 'P004', 'interaction_count': 2, 'account_count': 2, 'positive_account_count': 1},
            {'parent_asin': 'P005', 'interaction_count': 1, 'account_count': 1, 'positive_account_count': 1},
            {'parent_asin': 'P006', 'interaction_count': 0, 'account_count': 0, 'positive_account_count': 0}]
        self.assertEqual(tasks[ids[self.users[0]]]['background_statistics'], expected)
        second = {r['parent_asin']: r for r in tasks[ids[self.users[1]]]['background_statistics']}
        self.assertEqual(second['P006']['interaction_count'], 2)
        self.assertEqual(second['P002']['interaction_count'], 0)
        self.assertEqual(second['P003']['interaction_count'], 0)
        self.add_event(self.users[2], 'P004', 900, 5, '另一测试账号的较早互动')
        self.eligibility[2]['seen_parent_asins'].append('P004')
        self.eligibility[2]['prior_positive_parent_asins'].append('P004')
        self.eligibility[2]['prior_positive_product_count'] = 2
        self.add_event('bg-C', 'P004', 4000, 5, '等时不进入第一任务')
        self.add_event('bg-D', 'P004', 4001, 5, '未来不进入第一任务')
        self.add_event('bg-A', 'P004', 2500, 5, '同账号的第二次互动')
        self.refresh()
        self.record(self.run_tasks('extra'))
        first = next(t for t in self.output_rows('model/tasks.jsonl', 'extra') if t['task_id'] == ids[self.users[0]])
        expected[0]['interaction_count'] = 3
        self.assertEqual(first['background_statistics'], expected)

    def test_08_finite_text_retains_history_and_records_private_trace_without_truncation(self):
        self.fixture()
        for row in self.ledger:
            if row['review']['user_id'] == self.users[2] and row['timestamp_ms'] == 1000:
                row['review']['text'] = '<div>rice &amp; oats<br />price $10 P005</div><script>HIDDEN</script><style>HIDDEN</style><!--HIDDEN--><a href="https://x.invalid">visible name</a>\x00\t +1-202-555-0101 fixture-user-003'
            if row['review']['user_id'] == self.users[3] and row['timestamp_ms'] == 1000:
                row['review']['text'] = '🙂' + '米' * 8000
        self.refresh()
        self.record(self.run_tasks())
        ids = {r['source_user_id']: r['task_id'] for r in self.output_rows('private/evaluation.jsonl')}
        tasks = {r['task_id']: r for r in self.output_rows('model/tasks.jsonl')}
        self.assertEqual(tasks[ids[self.users[0]]]['history'][0]['text'], '好米5星，当时$12，也想试试P005。\n\n[LINK] [EMAIL]')
        self.assertEqual(tasks[ids[self.users[2]]]['history'][0]['text'], 'rice & oats\nprice $10 P005\nvisible name [PHONE] [USER]')
        self.assertEqual(tasks[ids[self.users[3]]]['history'][0]['text'], '🙂' + '米' * 8000)
        self.assertEqual(self.output_rows('model/catalog.jsonl')[3]['title'], '白米 2 kg')
        audits = self.output_rows('private/task-audit.jsonl')
        audit = next(r for r in audits if r['record_type'] == 'task' and r['task_id'] == ids[self.users[0]])['history'][0]
        self.assertEqual(audit['json_pointer'], '/history/0/text')
        self.assertEqual(audit['text_policy_version'], 'finite-text-1.0.0')
        self.assertEqual(audit['processed_sha256'], hashlib.sha256(tasks[ids[self.users[0]]]['history'][0]['text'].encode()).hexdigest())
        self.assertTrue(audit['stages'])
        self.assertTrue(audit['source_references'])

    def test_09_unconstructible_text_reports_all_affected_inputs_without_dropping_them(self):
        for kind in ('empty_histories', 'link_only', 'unhandled_title'):
            with self.subTest(kind=kind):
                self.fixture()
                if kind == 'unhandled_title':
                    self.catalog[3]['metadata']['title'] = 'rice currently $39'
                else:
                    for row in self.ledger:
                        if row['review']['user_id'] in self.users[:2] and row['timestamp_ms'] == 1000:
                            row['review']['text'] = '<script>PRIVATE_BLOCK</script>' if kind == 'empty_histories' else 'https://example.invalid/'
                self.refresh()
                before = self.binding(self.root / 'input/data/accounts.jsonl')['sha256']
                result = self.run_tasks(kind)
                self.assertEqual(result.returncode, 2)
                report = json.loads(result.stdout)
                self.assertEqual(report['error']['code'], 'embedded_dynamic_unhandled' if kind == 'unhandled_title' else 'text_processing_error')
                self.assertEqual(report['affected']['products'] if kind == 'unhandled_title' else report['affected']['accounts'], 1 if kind == 'unhandled_title' else 2)
                self.assertEqual(before, self.binding(self.root / 'input/data/accounts.jsonl')['sha256'])
                diagnostics = list((self.root / kind / 'data/preference-failures').glob('*.jsonl'))
                self.assertEqual(len(diagnostics), 1)
                failures = [json.loads(line) for line in diagnostics[0].read_text('utf-8').splitlines()]
                self.assertEqual(len(failures), 1 if kind == 'unhandled_title' else 2)
                self.assertNotIn('PRIVATE_BLOCK', result.stdout + result.stderr)

    def test_10_private_hmac_identity_and_target_changes_do_not_change_model_data(self):
        self.fixture()
        self.record(self.run_tasks())
        evaluation = self.output_rows('private/evaluation.jsonl')
        first_id = next(r['task_id'] for r in evaluation if r['source_user_id'] == self.users[0])
        self.assertRegex(first_id, '^[0-9a-f]{64}$')
        self.assertEqual(first_id, '9df20a2461a7d5aa9863c318e5349e3e41ebfc94488a060d3cdf2002728ca553')
        before = self.output_rows('model/tasks.jsonl')
        for r in self.ledger:
            if r['review']['user_id'] == self.users[0] and r['timestamp_ms'] == 4000:
                r['review'].update(parent_asin='P006', rating=4.0, text='DIFFERENT_PRIVATE_TARGET')
        self.eligibility[0]['target_parent_asin'] = 'P006'
        self.refresh()
        self.record(self.run_tasks('changed-target'))
        self.assertEqual(before, self.output_rows('model/tasks.jsonl', 'changed-target'))
        self.key_path.write_bytes(b'z' * 32)
        self.refresh()
        self.record(self.run_tasks('changed-key'))
        after_ids = {r['task_id'] for r in self.output_rows('model/tasks.jsonl', 'changed-key')}
        self.assertTrue(after_ids.isdisjoint(r['task_id'] for r in before))

    def test_11_real_api_channel_constructs_requests_and_denies_host_capabilities(self):
        self.fixture()
        self.record(self.run_tasks())
        tasks = self.output_rows('model/tasks.jsonl')
        first, second = tasks[0]['task_id'], tasks[1]['task_id']
        probes = [{'session_task_id': first, 'operation': 'model_request', 'arguments': {}}]
        for path in (str(self.key_path), str(self.root / 'input/data/clean.jsonl'), '../private/evaluation.jsonl',
                     'C:/unknown/no-file', 'https://example.invalid', 'old-index', 'old-cache'):
            probes.append({'session_task_id': first, 'operation': 'read_resource', 'arguments': {'path': path}})
        probes += [{'session_task_id': first, 'operation': 'invoke_tool', 'arguments': {'name': name, 'arguments': {'cmd': 'DO_NOT_RUN'}}}
                   for name in ('exec_command', 'file_search', 'python', 'web', 'mcp', 'evaluator')]
        probes += [{'session_task_id': first, 'operation': 'model_request', 'arguments': {'task_id': second}},
                   {'session_task_id': '0' * 64, 'operation': 'model_request', 'arguments': {}}]
        path = self.rows('probe.jsonl', probes)
        report = self.record(self.run_tasks('probed', path))
        self.assertEqual(report['access_probe_status'], 'completed')
        self.assertEqual(report['capabilities'], {'host_io': False, 'tools': [], 'indices': []})
        results = self.output_rows('private/access-probe.jsonl', 'probed')
        request = results[0]['response']['request']
        self.assertEqual(request['tools'], [])
        self.assertEqual([m['role'] for m in request['messages']], ['user'])
        payload = json.loads(request['messages'][0]['content'])
        self.assertEqual(payload['task_id'], first)
        self.assertEqual(set(payload['products'][0]), {'parent_asin', 'title', 'crop'})
        self.assertTrue(all(r['response'] == {'status': 'access_denied'} for r in results[1:]))
        serialized = json.dumps(results)
        for forbidden in ('PRIVATE_TARGET_', 'CLOSED_HISTORY_TITLE', 'CLOSED_DESCRIPTION', 'CLOSED_BRAND', 'source_user_id'):
            self.assertNotIn(forbidden, serialized)

    def test_12_inconsistent_qualification_or_split_cannot_be_silently_repaired(self):
        for kind in ('seen_target', 'missing_split', 'duplicate_account', 'lost_positive_history', 'wrong_latest'):
            with self.subTest(kind=kind):
                self.fixture()
                if kind == 'seen_target': self.eligibility[0]['seen_parent_asins'].append('P005')
                if kind == 'missing_split': self.assignments.pop()
                if kind == 'duplicate_account': self.eligibility.append(copy.deepcopy(self.eligibility[0]))
                if kind == 'lost_positive_history': self.ledger[0]['review']['rating'] = 1.0
                if kind == 'wrong_latest': self.eligibility[0]['latest_timestamp_ms'] = 3000
                self.refresh()
                result = self.run_tasks(kind)
                self.assertEqual(result.returncode, 2)
                report = json.loads(result.stdout)
                self.assertIn(report['error']['code'], ('invalid_task', 'invalid_time_or_candidate'))
                self.assertGreaterEqual(report['affected']['accounts'], 1)
                self.assertTrue(list((self.root / kind / 'data/preference-failures').glob('*.jsonl')))

    def test_13_versioned_components_reproduce_and_existing_versions_are_never_overwritten(self):
        self.fixture()
        first = self.record(self.run_tasks())
        record_path = self.root / 'output' / first['record_path']
        original_record = record_path.read_bytes()
        again = self.record(self.run_tasks())
        self.assertEqual(first, again)
        self.assertEqual(original_record, record_path.read_bytes())

        second = self.record(self.run_tasks('reproduced'))
        self.assertEqual(set(first['components']), set(second['components']))
        for name, component in first['components'].items():
            a = (self.root / 'output' / component['path']).read_bytes()
            b = (self.root / 'reproduced' / second['components'][name]['path']).read_bytes()
            self.assertEqual(a, b)
            self.assertFalse(a.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'\r\n', a)
        path = self.root / 'output' / first['components']['tasks']['path']
        path.write_bytes(path.read_bytes() + b'CORRUPTED_DO_NOT_ECHO')
        corrupted = path.read_bytes()
        result = self.run_tasks()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'output_conflict')
        self.assertEqual(corrupted, path.read_bytes())
        self.assertEqual(original_record, record_path.read_bytes())

    def test_14_invalid_probe_never_publishes_a_complete_bundle_or_echoes_private_data(self):
        self.fixture()
        for i, content in enumerate(('', '{"operation":"PRIVATE_PROBE"}\n', '[]\n',
            '{"session_task_id":"' + '0' * 64 + '","operation":"read_resource",'
            '"operation":"model_request","arguments":{}}\n',
            '{"session_task_id":"' + '0' * 64 + '","operation":"read_resource","arguments":{"x":NaN}}\n')):
            with self.subTest(i=i):
                probe = self.root / 'input/probe.jsonl'
                probe.write_bytes(content.encode('utf-8'))
                result = self.run_tasks('bad-probe-' + str(i), probe)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_probe')
                self.assertNotIn('PRIVATE_PROBE', result.stdout + result.stderr)
                output = self.root / ('bad-probe-' + str(i))
                self.assertFalse((output / 'records/preference-tasks').exists())
                self.assertFalse((output / 'data/preference-tasks/fixture/preference-task-1.0.0').exists())

    def test_15_accepted_catalog_and_split_totals_cannot_shrink_or_drift(self):
        for kind in ('missing_candidate', 'changed_split'):
            with self.subTest(kind=kind):
                self.fixture()
                if kind == 'missing_candidate':
                    self.catalog = [p for p in self.catalog if p['parent_asin'] != 'P004']
                else:
                    self.assignments[0]['split'] = 'test'
                self.refresh()
                result = self.run_tasks(kind)
                self.assertEqual(result.returncode, 2)
                report = json.loads(result.stdout)
                self.assertEqual(report['error']['code'], 'invalid_task')
                self.assertEqual(report['affected']['accounts'], 5)
                self.assertFalse((self.root / kind / 'records/preference-tasks').exists())

    def test_16_path_escape_and_junction_do_not_gain_output_permissions(self):
        self.fixture()
        result = self.run_tasks(PROJECT.parent / 'PRIVATE_PATH_DO_NOT_ECHO')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_task')
        self.assertNotIn('PRIVATE_PATH_DO_NOT_ECHO', result.stdout + result.stderr)
        target = self.root / 'junction-target'
        target.mkdir()
        link = self.root / 'junction-link'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        result = self.run_tasks(link / 'output')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_task')
        self.assertFalse((target / 'output').exists())

    def test_17_receipt_reports_scope_loss_and_bound_private_provenance(self):
        self.fixture()
        report = self.record(self.run_tasks())
        self.assertEqual(report['model_input_status'], 'prepared_not_executed')
        self.assertEqual(report['interaction_training_status'], 'not_built')
        self.assertEqual(report['construction_failures'], {'accounts': 0, 'history_events': 0, 'products': 0})
        self.assertEqual(report['sources']['cleaning_record']['sha256'], self.binding(self.clean_path)['sha256'])
        self.assertEqual(report['text_summary']['product_title']['fields'], 6)
        self.assertEqual(report['text_summary']['history_body']['fields'], 5)
        self.assertEqual(report['text_summary']['product_title']['operations']['commercial_tails_removed'], 1)
        self.assertEqual(report['text_summary']['history_body']['changed_fields'], 1)
        self.assertGreater(report['text_summary']['history_body']['raw_utf8_bytes'],
                           report['text_summary']['history_body']['raw_codepoints'])
        titles = [r for r in self.output_rows('private/task-audit.jsonl') if r['record_type'] == 'catalog_text']
        self.assertTrue(all(r['json_pointer'] == '/metadata/title' for r in titles))
        self.assertTrue(all(r['source_component_sha256'] == self.clean['catalog_sha256'] for r in titles))

    def test_18_existing_output_ancestor_junction_is_rejected_before_writing(self):
        self.fixture()
        output = self.root / 'output'
        output.mkdir()
        target = self.root / 'private-junction-target'
        target.mkdir()
        link = output / 'data'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        result = self.run_tasks()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_task')
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse((output / 'records').exists())

    def test_19_failure_trace_junction_cannot_redirect_private_writes(self):
        self.fixture()
        self.catalog[0]['metadata']['title'] = 'rice current price $39'
        self.refresh()
        output = self.root / 'output'
        (output / 'data').mkdir(parents=True)
        target = self.root / 'private-failure-target'
        target.mkdir()
        link = output / 'data/preference-failures'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        result = self.run_tasks()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(list(target.iterdir())), 0, 'private failures must not follow a junction')
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_task')
        self.assertFalse((output / 'records').exists())


if __name__ == '__main__':
    unittest.main()
