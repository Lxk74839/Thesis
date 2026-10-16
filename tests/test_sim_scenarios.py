"""Ticket11: observe only the approved preparation and audit subprocess seams."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
AUDITOR = PROJECT / '.scratch/data-preparation/diagnostics/verify_sim11.py'


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.output = self.root / 'output'
        self.config_path = self.root / 'scenario-config.json'
        self.normal_record_path = self.root / 'normal/records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'

    def write(self, path, value, rows=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b''.join(wire(row) + b'\n' for row in value) if rows else wire(value) + b'\n')
        return path

    def cli(self, *extra, omit=(), output=None):
        arguments = {'--sim-record': self.normal_record_path, '--scenario-config': self.config_path,
                     '--output-root': output or self.output}
        command = [sys.executable, str(PROJECT / 'prepare_data.py'), '--stage', 'evidence_scenarios']
        for key, value in arguments.items():
            if key not in omit:
                command += [key, str(value)]
        return subprocess.run(command + list(extra), cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')

    def fixture(self):
        self.config = json.loads((PROJECT / 'config/sim-scenarios-1.0.0.json').read_bytes())
        normal = json.loads((PROJECT / 'config/sim-normal-1.0.0.json').read_bytes())
        catalog = self.write(self.root / 'inputs/catalog.jsonl', [
            {'parent_asin': p, 'crop': 'rice', 'status': 'included'} for p in ('PX1', 'PX2', 'PX3')], rows=True)
        catalog_record = self.write(self.root / 'inputs/catalog-record.json', {
            'stage': 'catalog', 'status': 'catalog_complete', 'scope_version': 'grain-A-1.1.15',
            'counts': {'included': 3}, 'catalog_path': catalog.relative_to(PROJECT).as_posix(),
            'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest()})
        normal['catalog_binding'].update(record_path=catalog_record.relative_to(PROJECT).as_posix(),
            record_sha256=hashlib.sha256(catalog_record.read_bytes()).hexdigest(),
            component_sha256=hashlib.sha256(catalog.read_bytes()).hexdigest(), expected_parent_count=3)
        normal_config = self.write(self.root / 'inputs/normal-config.json', normal)
        generated = subprocess.run([sys.executable, str(PROJECT / 'prepare_data.py'), '--stage', 'sim_normal',
            '--catalog-record', str(catalog_record), '--sim-config', str(normal_config),
            '--output-root', str(self.root / 'normal')], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        self.normal = json.loads(generated.stdout)
        self.base_files = {name: (self.root / 'normal' / info['path']).read_bytes()
                           for name, info in self.normal['components'].items()}
        acceptance = json.loads((PROJECT / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json').read_bytes())
        acceptance['generation_record'] = {'path': self.normal_record_path.relative_to(PROJECT).as_posix(),
            'sha256': hashlib.sha256(self.normal_record_path.read_bytes()).hexdigest()}
        acceptance['components'] = self.normal['components']
        acceptance['independent_reference']['audited_batches'] = 3
        acceptance['independent_reference']['state_counts'] = {'Supported': 3, 'Refuted': 0, 'Pending': 0, 'Conflict': 0}
        acceptance['approved_contract']['config'] = {'path': normal_config.relative_to(PROJECT).as_posix(),
            'sha256': hashlib.sha256(normal_config.read_bytes()).hexdigest()}
        acceptance_path = self.write(self.root / 'inputs/normal-acceptance.json', acceptance)
        for name, path in [('record', self.normal_record_path), ('acceptance', acceptance_path),
                           ('config', normal_config)]:
            self.config['normal_binding'][name] = {'path': path.relative_to(PROJECT).as_posix(),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        self.write(self.config_path, self.config)

    def prepared(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.record = json.loads(result.stdout)
        self.package = self.output / 'data/sim-scenarios/grain-A-1.1.15/sim-scenarios-1.0.0'
        self.views = [json.loads(line) for line in (self.package / 'view-index.jsonl').read_bytes().splitlines()]
        plan = [json.loads(line) for line in (self.package / 'private/mutation-plan.jsonl').read_bytes().splitlines()]
        self.view_by_name = {row['view_name']: next(v for v in self.views if v['view_id'] == row['view_id']) for row in plan}
        return result

    def rows(self, view, name):
        directory = Path(self.view_by_name[view]['snapshot_path']).parent
        return [json.loads(line) for line in (self.package / directory / name).read_bytes().splitlines()]

    def report(self, view, parent='PX3', version=1):
        base_id = next(row['evidence_id'] for row in self.rows('V00', 'materials.jsonl')
                       if row['parent_asin'] == parent and row['kind'] == 'inspection_report')
        return next(row for row in self.rows(view, 'materials.jsonl')
                    if row['evidence_id'] == base_id and row['version'] == version)

    def receipt(self, view, row):
        return next(r for r in self.rows(view, 'registrations.jsonl')
                    if r['target_id'] == row['evidence_id'] and r['version'] == row['version'])

    def audit(self, name='audit'):
        record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        audit_root = self.root / name
        result = subprocess.run([sys.executable, str(AUDITOR), '--record', str(record_path),
            '--audit-root', str(audit_root)], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
        return result, audit_root

    def references(self, audit_root):
        names = {v['view_id']: name for name, v in self.view_by_name.items()}
        return {(names[row['view_id']], row['request_profile_id'], row['parent_asin']): row
                for row in (json.loads(line) for line in (audit_root / 'reference.jsonl').read_bytes().splitlines())}

    def replace_rows(self, view, name, rows):
        directory = Path(self.view_by_name[view]['snapshot_path']).parent
        self.write(self.package / directory / name, rows, rows=True)

    def reseal(self):
        record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        record = json.loads(record_path.read_bytes())
        relative = self.package.relative_to(self.output)
        counts = {**record['counts'], 'batch_rows': 0, 'event_rows': 0, 'material_rows': 0,
                  'registration_rows': 0, 'change_action_rows': 0}
        def update(name):
            raw = (self.package / name).read_bytes()
            record['components'][name] = {'path': (relative / name).as_posix(), 'bytes': len(raw),
                'records': len(raw.splitlines()), 'sha256': hashlib.sha256(raw).hexdigest()}
        changed_request = hashlib.sha256((self.package / 'requests.jsonl').read_bytes()).hexdigest() != record['components']['requests.jsonl']['sha256']
        update('requests.jsonl')
        for view in self.views:
            path = view['snapshot_path']
            snapshot = json.loads((self.package / path).read_bytes())
            if changed_request:
                snapshot['requests_sha256'] = record['components']['requests.jsonl']['sha256']
            for name in ('batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl',
                         'change-actions.jsonl', 'policy.json'):
                key = str(Path(path).parent / name).replace('\\', '/')
                update(key)
                snapshot['components'][name] = {k: record['components'][key][k] for k in ('bytes', 'records', 'sha256')}
            for field, name in [('batch_rows', 'batches.jsonl'), ('event_rows', 'events.jsonl'),
                                ('material_rows', 'materials.jsonl'), ('registration_rows', 'registrations.jsonl'),
                                ('change_action_rows', 'change-actions.jsonl')]:
                counts[field] += snapshot['components'][name]['records']
            snapshot.pop('snapshot_id')
            snapshot['snapshot_id'] = 'n_' + hashlib.sha256(b'Thesis-SIM-1:scenario_snapshot\0' + wire(snapshot)).hexdigest()
            self.write(self.package / path, snapshot)
            update(path)
            view['snapshot_sha256'] = record['components'][path]['sha256']
        self.write(self.package / 'view-index.jsonl', self.views, rows=True)
        update('view-index.jsonl')
        update('requests.jsonl')
        manifest = json.loads((self.package / 'manifest.json').read_bytes())
        manifest['components'] = {name: {k: info[k] for k in ('bytes', 'records', 'sha256')}
                                  for name, info in record['components'].items() if name != 'manifest.json'}
        record['counts'] = manifest['counts'] = counts
        self.write(self.package / 'manifest.json', manifest)
        update('manifest.json')
        self.write(record_path, record)

    def rebind_original(self, view, original):
        receipts = self.rows(view, 'registrations.jsonl')
        for receipt in receipts:
            if receipt['target_id'] == original.get('evidence_id') and receipt['version'] == original['version']:
                receipt['content_sha256'] = hashlib.sha256(wire(original)).hexdigest()
                for key in ('issuer_id', 'parent_asin', 'sim_batch_id', 'event_id'):
                    receipt[key] = original[key]
        self.replace_rows(view, 'registrations.jsonl', receipts)

    def capture_public(self):
        record = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        return {p: p.read_bytes() for p in [record] + [self.output / info['path']
                for info in json.loads(record.read_bytes())['components'].values()]}

    def restore_public(self, saved):
        for path, raw in saved.items():
            path.write_bytes(raw)

    def rebind_normal(self, record, acceptance):
        self.write(self.normal_record_path, record)
        self.config['normal_binding']['record']['sha256'] = hashlib.sha256(self.normal_record_path.read_bytes()).hexdigest()
        acceptance['generation_record'] = copy.deepcopy(self.config['normal_binding']['record'])
        acceptance['components'] = copy.deepcopy(record['components'])
        acceptance_path = PROJECT / self.config['normal_binding']['acceptance']['path']
        self.write(acceptance_path, acceptance)
        self.config['normal_binding']['acceptance']['sha256'] = hashlib.sha256(acceptance_path.read_bytes()).hexdigest()
        self.write(self.config_path, self.config)

    def snapshot_update(self, view, **changes):
        path = self.package / self.view_by_name[view]['snapshot_path']
        snapshot = json.loads(path.read_bytes())
        snapshot.update(changes)
        self.write(path, snapshot)

    def order_receipts(self, view):
        rows = self.rows(view, 'registrations.jsonl')
        rows.sort(key=lambda r: (r['registered_at_ms'], ['batch', 'event', 'material', 'change_action'].index(r['target_kind']),
                                  r['target_id'].encode(), r['version']))
        for number, row in enumerate(rows, 1):
            row['sequence'] = number
        self.replace_rows(view, 'registrations.jsonl', rows)
        snapshot = self.rows(view, 'snapshot.json')[0]
        self.snapshot_update(view, cutoff_sequence=sum(r['registered_at_ms'] <= snapshot['sealed_at_ms'] for r in rows))

    def rebind_actions(self, view, actions):
        old = self.rows(view, 'change-actions.jsonl')
        receipts = self.rows(view, 'registrations.jsonl')
        for previous, action in zip(old, actions):
            for receipt in receipts:
                if receipt['target_id'] == previous['action_id']:
                    receipt['content_sha256'] = hashlib.sha256(wire(action)).hexdigest()
                    receipt['issuer_id'] = action['issuer_id']
        self.replace_rows(view, 'change-actions.jsonl', actions)
        self.replace_rows(view, 'registrations.jsonl', receipts)

    def test_missing_dependencies_use_the_structured_stage_error(self):
        for name in ('--sim-record', '--scenario-config', '--output-root'):
            with self.subTest(missing=name):
                result = self.cli(omit=(name,))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout), {'stage': 'evidence_scenarios',
                    'status': 'evidence_scenarios_incomplete', 'error': {'code': 'invalid_arguments'}})
        self.assertFalse(self.output.exists())

    def test_config_rejects_unapproved_and_wrong_typed_fields(self):
        approved = json.loads((PROJECT / 'config/sim-scenarios-1.0.0.json').read_bytes())
        cases = [('invalid_config', b'{"version":"a","version":"b"}'),
                 ('invalid_config', b'{"x":NaN}')]
        for path, value in [(('selection', 'numerator'), True), (('publication', 'overwrite'), 0),
                            (('publication', 'repeat_count'), 1.0), (('unknown',), 1),
                            (('clock', 'verify_at_ms'), 2**53)]:
            config = copy.deepcopy(approved)
            target = config
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            cases.append(('invalid_config', wire(config)))
        config = copy.deepcopy(approved)
        config['approval_binding']['draft_sha256'] = '0' * 64
        cases.append(('unapproved_protocol', wire(config)))
        for code, raw in cases:
            with self.subTest(code=code, raw=raw[:40]):
                self.config_path.write_bytes(raw)
                result = self.cli()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(json.loads(result.stdout)['error']['code'], code)
        self.assertFalse(self.output.exists())

    def test_publishes_the_normal_anchor_in_sixteen_sealed_views(self):
        self.fixture()
        self.prepared()
        self.assertEqual(self.record['status'], 'evidence_scenarios_prepared')
        self.assertEqual(len(self.views), 16)
        self.assertEqual(self.record['counts']['business_parents'], 3)
        for name in ('batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl', 'policy.json'):
            directory = Path(self.view_by_name['V00']['snapshot_path']).parent
            self.assertEqual((self.package / directory / name).read_bytes(), self.base_files[name])
        self.assertEqual(self.rows('V00', 'change-actions.jsonl'), [])
        self.assertEqual([r['parent_asin'] for r in self.rows('V00', 'batches.jsonl')], ['PX1', 'PX2', 'PX3'])
        self.assertEqual(self.record['independent_acceptance'], 'pending_separate_record')
        self.assertEqual(self.record['sample_sufficiency'], 'not_determined')

    def test_missing_report_uses_the_frozen_parent_selection(self):
        self.fixture()
        self.prepared()
        original = self.rows('V00', 'materials.jsonl')
        missing = self.rows('V01', 'materials.jsonl')
        self.assertEqual(len(missing), 23)
        self.assertEqual([(r['parent_asin'], r['kind']) for r in original if r not in missing],
                         [('PX3', 'inspection_report')])
        self.assertEqual(self.rows('V01', 'registrations.jsonl'), self.rows('V00', 'registrations.jsonl'))
        for line in (self.package / 'private/mutation-plan.jsonl').read_bytes().splitlines():
            self.assertEqual(json.loads(line)['selected_parents'], ['PX3'])

    def test_view_identity_uses_nul_delimited_seed_without_answer_names(self):
        self.fixture()
        self.prepared()
        self.assertEqual(self.view_by_name['V00']['view_id'],
                         'q_286b0847b020a9d2cb5baa04a756d4fac00299e9f17fa1756df55ca7a32a03f8')
        index = (self.package / 'view-index.jsonl').read_bytes()
        for forbidden in (b'V00', b'Conflict', b'Pending', b'expected_status', b'gold'):
            self.assertNotIn(forbidden, index)

    def test_object_mismatch_has_matching_digest_but_keeps_original_index(self):
        self.fixture()
        self.prepared()
        wrong = self.report('V02')
        donor = self.report('V00', parent='PX2')
        self.assertEqual(wrong['parent_asin'], 'PX2')
        for field in ('sim_batch_id', 'event_id'):
            self.assertEqual(wrong[field], donor[field])
        self.assertEqual(wrong['facts']['sample_id'], donor['facts']['sample_id'])
        receipt = self.receipt('V02', wrong)
        self.assertEqual(receipt['parent_asin'], 'PX3')
        self.assertEqual(receipt['content_sha256'], hashlib.sha256(wire(wrong)).hexdigest())
        self.assertEqual(self.report('V02', parent='PX2'), donor)

    def test_tampered_fail_keeps_the_old_pass_receipt(self):
        self.fixture()
        self.prepared()
        tampered = self.report('V03')
        self.assertEqual(tampered['facts']['conclusion'], 'fail')
        self.assertEqual(self.receipt('V03', tampered), self.receipt('V00', self.report('V00')))
        self.assertNotEqual(self.receipt('V03', tampered)['content_sha256'], hashlib.sha256(wire(tampered)).hexdigest())

    def test_registry_identity_error_does_not_change_the_original(self):
        self.fixture()
        self.prepared()
        report = self.report('V04')
        self.assertEqual(report, self.report('V00'))
        receipt = self.receipt('V04', report)
        self.assertEqual(receipt['issuer_id'], 'SIM-RETAIL')
        self.assertEqual(receipt['content_sha256'], hashlib.sha256(wire(report)).hexdigest())

    def test_valid_negative_retains_full_binding_and_has_its_own_digest(self):
        self.fixture()
        self.prepared()
        negative = self.report('V05')
        expected = copy.deepcopy(self.report('V00'))
        expected['facts']['conclusion'] = 'fail'
        self.assertEqual(negative, expected)
        self.assertEqual(self.receipt('V05', negative)['content_sha256'], hashlib.sha256(wire(expected)).hexdigest())
        sample = next(row for row in self.rows('V05', 'materials.jsonl')
                      if row['parent_asin'] == 'PX3' and row['kind'] == 'inspection_sample')
        self.assertEqual(sample['facts']['sample_id'], negative['facts']['sample_id'])

    def test_conflict_adds_an_independent_fully_bound_report_without_replacing_pass(self):
        self.fixture()
        self.prepared()
        reports = [r for r in self.rows('V06', 'materials.jsonl')
                   if r['parent_asin'] == 'PX3' and r['kind'] == 'inspection_report']
        self.assertEqual(len(reports), 2)
        self.assertEqual(self.report('V06'), self.report('V00'))
        second = next(r for r in reports if r['evidence_id'] != self.report('V00')['evidence_id'])
        self.assertEqual(second['facts']['conclusion'], 'fail')
        self.assertEqual(second['issuer_id'], 'SIM-LAB')
        self.assertEqual(second['facts']['sample_id'], self.report('V00')['facts']['sample_id'])
        self.assertEqual(second['issued_at_ms'], 1791372000000)
        self.assertEqual(second['version'], 1)
        self.assertEqual(self.receipt('V06', second)['registered_at_ms'], 1791372060000)
        self.assertEqual(self.rows('V06', 'change-actions.jsonl'), [])
        self.assertEqual([r['sequence'] for r in self.rows('V06', 'registrations.jsonl')], list(range(1, 47)))

    def test_expiry_only_changes_the_retail_interval_not_historical_reports(self):
        self.fixture()
        self.prepared()
        retail = next(r for r in self.rows('V07', 'materials.jsonl')
                      if r['parent_asin'] == 'PX3' and r['kind'] == 'retail_status')
        self.assertEqual(retail['valid_to_ms'], 1791417600000)
        self.assertEqual(retail['valid_from_ms'], 1791374400000)
        self.assertEqual(retail['facts']['status'], 'on_sale')
        self.assertEqual(self.receipt('V07', retail)['content_sha256'], hashlib.sha256(wire(retail)).hexdigest())
        self.assertEqual(self.report('V07'), self.report('V00'))
        self.assertNotIn('valid_to_ms', self.report('V07'))

    def test_revocation_preserves_originals_and_registers_an_authorized_action(self):
        self.fixture()
        self.prepared()
        self.assertEqual(self.report('V08'), self.report('V00'))
        actions = self.rows('V08', 'change-actions.jsonl')
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual((action['action_type'], action['target_id'], action['target_version'],
                          action['supersedes_version'], action['issuer_id']),
                         ('revokes', self.report('V00')['evidence_id'], 1, None, 'SIM-LAB'))
        self.assertEqual(action['effective_from_ms'], 1791372120000)
        receipt = next(r for r in self.rows('V08', 'registrations.jsonl') if r['target_id'] == action['action_id'])
        self.assertEqual(receipt['target_kind'], 'change_action')
        self.assertEqual(receipt['registered_at_ms'], 1791372180000)
        self.assertEqual(receipt['content_sha256'], hashlib.sha256(wire(action)).hexdigest())

    def test_legal_versions_keep_v1_and_explicitly_replace_it_with_v2(self):
        self.fixture()
        self.prepared()
        for view, conclusion in [('V09', 'fail'), ('V10', 'pass')]:
            with self.subTest(view=view):
                self.assertEqual(self.report(view), self.report('V00'))
                second = self.report(view, version=2)
                self.assertEqual(second['facts']['conclusion'], conclusion)
                self.assertEqual(second['issued_at_ms'], 1791372000000)
                self.assertEqual(second['facts']['sample_id'], self.report('V00')['facts']['sample_id'])
                action = self.rows(view, 'change-actions.jsonl')[0]
                self.assertEqual((action['action_type'], action['target_version'], action['supersedes_version']),
                                 ('supersedes', 2, 1))
                self.assertEqual(action['target_id'], second['evidence_id'])
                self.assertEqual(len(self.rows(view, 'registrations.jsonl')), 47)

    def test_permission_view_only_denies_the_selected_existing_report(self):
        self.fixture()
        self.prepared()
        policy = self.rows('V11', 'policy.json')[0]
        self.assertEqual(policy['read_denials'], [{'principal_id': 'SIM-VERIFIER', 'target_kind': 'material',
                          'target_id': self.report('V00')['evidence_id'], 'version': 1}])
        self.assertEqual(policy['issuers'], self.rows('V00', 'policy.json')[0]['issuers'])
        self.assertEqual(self.rows('V11', 'materials.jsonl'), self.rows('V00', 'materials.jsonl'))

    def test_unrelated_origin_change_keeps_all_necessary_materials_identical(self):
        self.fixture()
        self.prepared()
        before, after = self.rows('V00', 'materials.jsonl'), self.rows('V12', 'materials.jsonl')
        changed = [(old, new) for old, new in zip(before, after) if old != new]
        self.assertEqual(len(changed), 1)
        old, new = changed[0]
        expected = copy.deepcopy(old)
        expected['facts']['origin_area_id'] = 'SIM-AREA-02'
        self.assertEqual(new, expected)
        self.assertEqual(new['parent_asin'], 'PX3')
        self.assertEqual(new['kind'], 'harvest_record')
        self.assertEqual(self.receipt('V12', new)['content_sha256'], hashlib.sha256(wire(new)).hexdigest())

    def test_fixed_combinations_share_selection_and_have_the_approved_counts(self):
        self.fixture()
        self.prepared()
        self.assertEqual(len(self.rows('V13', 'materials.jsonl')), 25)
        self.assertEqual(self.report('V14'), self.report('V00'))
        for view in ('V14', 'V15'):
            retail = next(r for r in self.rows(view, 'materials.jsonl') if r['parent_asin'] == 'PX3'
                          and r['kind'] == 'retail_status')
            self.assertEqual(retail['valid_to_ms'], 1791417600000)
        self.assertEqual(self.report('V15', version=2)['facts']['conclusion'], 'fail')
        self.assertEqual(self.record['counts'], {'business_parents': 3, 'business_batches': 3, 'views': 16,
            'request_profiles': 2, 'batch_rows': 48, 'event_rows': 288, 'material_rows': 389,
            'registration_rows': 730, 'change_action_rows': 4})

    def test_private_mutation_trace_locates_before_after_originals_and_receipts(self):
        self.fixture()
        self.prepared()
        plan = [json.loads(line) for line in (self.package / 'private/mutation-plan.jsonl').read_bytes().splitlines()]
        trace = next(row for row in plan if row['view_name'] == 'V05')['changes'][0]
        self.assertEqual(trace['before']['materials'][0]['sha256'], hashlib.sha256(wire(self.report('V00'))).hexdigest())
        self.assertEqual(trace['after']['materials'][0]['sha256'], hashlib.sha256(wire(self.report('V05'))).hexdigest())
        self.assertEqual(trace['after']['registrations'][0]['sha256'],
                         hashlib.sha256(wire(self.receipt('V05', self.report('V05')))).hexdigest())
        self.assertGreater(trace['after']['materials'][0]['line'], 0)
        mismatch = next(row for row in plan if row['view_name'] == 'V02')['changes'][0]
        self.assertEqual(mismatch['donor_parent_asin'], 'PX2')
        self.assertNotIn(b'expected_status', (self.package / 'private/mutation-plan.jsonl').read_bytes())

    def test_identical_reuse_keeps_record_bytes_and_damage_is_never_overwritten(self):
        self.fixture()
        first = self.prepared()
        record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        saved = record_path.read_bytes()
        second = self.cli()
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(record_path.read_bytes(), saved)
        damaged = self.package / 'requests.jsonl'
        damaged.write_bytes(damaged.read_bytes()[:-1])
        wrong_bytes = damaged.read_bytes()
        rejected = self.cli()
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(json.loads(rejected.stdout)['error']['code'], 'output_conflict')
        self.assertEqual(damaged.read_bytes(), wrong_bytes)
        self.assertEqual(record_path.read_bytes(), saved)

    def test_resealed_changed_outputs_cannot_be_reused_as_the_fixed_profile(self):
        self.fixture()
        self.prepared()
        materials = self.rows('V00', 'materials.jsonl')
        report = next(r for r in materials if r['parent_asin'] == 'PX3' and r['kind'] == 'inspection_report')
        report['facts']['conclusion'] = 'fail'
        self.replace_rows('V00', 'materials.jsonl', materials)
        self.rebind_original('V00', report)
        self.reseal()
        saved = self.capture_public()
        result = self.cli()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'output_conflict')
        self.assertEqual(self.capture_public(), saved)

    def test_independent_reference_rederives_normal_support_and_rejects_container_damage(self):
        self.fixture()
        self.prepared()
        result, audit_root = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        references = self.references(audit_root)
        self.assertEqual(len(references), 96)
        for profile in ('R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE'):
            for parent in ('PX1', 'PX2', 'PX3'):
                row = references['V00', profile, parent]
                self.assertEqual(row['candidate_state'], 'Supported')
                self.assertIs(row['eligible'], True)
                self.assertEqual(row['clauses'][0]['s'], 1)
                self.assertEqual(row['clauses'][0]['r'], 0)
                self.assertTrue(row['clauses'][0]['enumeration_complete'])
        (self.package / 'requests.jsonl').write_bytes(b'broken')
        failed, failed_root = self.audit('broken-audit')
        self.assertEqual(failed.returncode, 2, failed.stdout)
        self.assertEqual(json.loads((failed_root / 'check.json').read_bytes())['status'], 'failed')
        self.assertFalse((failed_root / 'reference.jsonl').exists())

    def test_check_reports_outer_integrity_and_inner_rejection_observation_counts(self):
        self.fixture()
        self.prepared()
        result, audit = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        check = json.loads((audit / 'check.json').read_bytes())
        self.assertEqual(check['outer_integrity'], {'status': 'passed', 'public_components': 115, 'views': 16})
        self.assertEqual(check['rejection_count_unit'], 'clause_trace_occurrence')
        for reason in ('unavailable', 'digest_mismatch', 'access_denied', 'revoked'):
            self.assertEqual(check['rejection_reason_counts'][reason], 2)
        self.assertTrue(all(type(v) is int and v > 0 for v in check['rejection_reason_counts'].values()))

    def test_reference_distinguishes_missing_invalid_negative_and_independent_conflict(self):
        self.fixture()
        self.prepared()
        result, audit_root = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        refs = self.references(audit_root)
        expected = {'V01': 'Pending', 'V02': 'Pending', 'V03': 'Pending', 'V04': 'Pending',
                    'V05': 'Refuted', 'V06': 'Conflict'}
        for view, state in expected.items():
            for profile in ('R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE'):
                with self.subTest(view=view, profile=profile):
                    self.assertEqual(refs[view, profile, 'PX3']['candidate_state'], state)
        digest_clause = refs['V03', 'R1_SIM_Q1', 'PX3']['clauses'][0]
        self.assertEqual((digest_clause['s'], digest_clause['r']), (0, 0))
        self.assertIn('digest_mismatch', [r['reason'] for r in digest_clause['rejected']])

    def test_reference_keeps_the_request_bound_to_the_baseline_event_and_sample(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for other_event in (False, True):
            with self.subTest(other_event=other_event):
                self.restore_public(saved)
                materials = self.rows('V00', 'materials.jsonl')
                receipts = self.rows('V00', 'registrations.jsonl')
                sample = copy.deepcopy(next(r for r in materials if r['parent_asin'] == 'PX3' and r['kind'] == 'inspection_sample'))
                report = copy.deepcopy(self.report('V00'))
                event_id = sample['event_id']
                if other_event:
                    events = self.rows('V00', 'events.jsonl')
                    event = copy.deepcopy(next(r for r in events if r['event_id'] == event_id))
                    receipt = copy.deepcopy(next(r for r in receipts if r['target_id'] == event_id))
                    event_id = event['event_id'] = 'e_' + hashlib.sha256(b'other-inspection-event').hexdigest()
                    receipt.update(target_id=event_id, event_id=event_id, content_sha256=hashlib.sha256(wire(event)).hexdigest(),
                                   registration_id='g_' + hashlib.sha256(b'other-event-receipt').hexdigest())
                    receipts.append(receipt)
                    self.replace_rows('V00', 'events.jsonl', events + [event])
                for index, original in enumerate((sample, report)):
                    receipt = copy.deepcopy(next(r for r in receipts if r['target_id'] == original['evidence_id']))
                    original.update(evidence_id='d_' + hashlib.sha256(f'other-sample-evidence-{index}'.encode()).hexdigest(),
                                    event_id=event_id)
                    original['facts']['sample_id'] = 'another-sample'
                    if original['kind'] == 'inspection_report':
                        original['facts']['conclusion'] = 'fail'
                    receipt.update(target_id=original['evidence_id'], event_id=event_id,
                        content_sha256=hashlib.sha256(wire(original)).hexdigest(),
                        registration_id='g_' + hashlib.sha256(f'other-sample-receipt-{index}'.encode()).hexdigest())
                    materials.append(original)
                    receipts.append(receipt)
                self.replace_rows('V00', 'materials.jsonl', materials)
                self.replace_rows('V00', 'registrations.jsonl', receipts)
                self.order_receipts('V00')
                self.reseal()
                result, audit = self.audit('other-sample-' + str(other_event))
                self.assertEqual(result.returncode, 0, result.stdout)
                refs = self.references(audit)
                for profile in ('R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE'):
                    clause = refs['V00', profile, 'PX3']['clauses'][0]
                    self.assertEqual((clause['s'], clause['r'], clause['state']), (1, 0, 'Supported'))

    def test_reference_requires_authorized_sampling_and_compatible_test_times(self):
        self.fixture()
        self.prepared()
        original_rows = self.rows('V05', 'materials.jsonl')
        original_receipts = self.rows('V05', 'registrations.jsonl')
        cases = [('inspection_sample', ('facts', 'sampled_at_ms'), 1791190800001),
                 ('inspection_sample', ('issuer_id',), 'SIM-RETAIL'),
                 ('inspection_report', ('facts', 'test_started_at_ms'), 1791105299999),
                 ('inspection_report', ('issued_at_ms',), 1791417600001)]
        for index, (kind, path, value) in enumerate(cases):
            with self.subTest(kind=kind, path=path):
                rows = copy.deepcopy(original_rows)
                row = next(r for r in rows if r['parent_asin'] == 'PX3' and r['kind'] == kind)
                target = row
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.replace_rows('V05', 'materials.jsonl', rows)
                self.replace_rows('V05', 'registrations.jsonl', original_receipts)
                self.rebind_original('V05', row)
                self.reseal()
                result, audit_root = self.audit('binding-' + str(index))
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(self.references(audit_root)['V05', 'R1_SIM_Q1', 'PX3']['candidate_state'], 'Pending')

    def test_reference_honors_read_denials_and_rejects_policy_escalation(self):
        self.fixture()
        self.prepared()
        result, audit_root = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        row = self.references(audit_root)['V11', 'R1_SIM_Q1', 'PX3']
        self.assertEqual(row['candidate_state'], 'Pending')
        self.assertFalse(row['clauses'][0]['required_reads_complete'])
        self.assertIn('access_denied', [r['reason'] for r in row['clauses'][0]['rejected']])
        policy = self.rows('V00', 'policy.json')[0]
        policy['issuers'][0]['material_kinds'].append('inspection_report')
        self.replace_rows('V00', 'policy.json', [policy])
        self.reseal()
        failed, failed_root = self.audit('escalation')
        self.assertEqual(failed.returncode, 2, failed.stdout)
        self.assertFalse((failed_root / 'reference.jsonl').exists())

    def test_reference_resolves_authorized_heads_and_never_revives_v1(self):
        self.fixture()
        self.prepared()
        result, audit_root = self.audit()
        self.assertEqual(result.returncode, 0, result.stdout)
        refs = self.references(audit_root)
        for view, expected in [('V08', 'Pending'), ('V09', 'Refuted'), ('V10', 'Supported'),
                               ('V14', 'Conflict'), ('V15', 'Refuted')]:
            for profile in ('R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE'):
                self.assertEqual(refs[view, profile, 'PX3']['candidate_state'], expected, (view, profile))
        rows = self.rows('V09', 'materials.jsonl')
        self.replace_rows('V09', 'materials.jsonl', [r for r in rows if r.get('version') != 2])
        self.reseal()
        missing, missing_root = self.audit('missing-head')
        self.assertEqual(missing.returncode, 0, missing.stdout)
        row = self.references(missing_root)['V09', 'R1_SIM_Q1', 'PX3']
        self.assertEqual(row['candidate_state'], 'Pending')
        self.assertIn(2, [head['head_version'] for head in row['clauses'][0]['version_heads']])

    def test_invalid_receipts_cannot_grant_another_issuer_or_object_status_authority(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for mode in ('issuer', 'object'):
            with self.subTest(mode=mode):
                self.restore_public(saved)
                actions = self.rows('V08', 'change-actions.jsonl')
                if mode == 'issuer':
                    actions[0]['issuer_id'] = 'SIM-RETAIL'
                else:
                    donor = self.report('V08', parent='PX2')
                    for field in ('parent_asin', 'sim_batch_id', 'event_id'):
                        actions[0][field] = donor[field]
                self.rebind_actions('V08', actions)
                receipts = self.rows('V08', 'registrations.jsonl')
                fake = copy.deepcopy(self.receipt('V08', self.report('V08')))
                for field in ('issuer_id', 'parent_asin', 'sim_batch_id', 'event_id'):
                    fake[field] = actions[0][field]
                fake['registration_id'] = 'g_' + hashlib.sha256(('fake-authority-' + mode).encode()).hexdigest()
                for receipt in receipts:
                    if receipt['target_kind'] == 'change_action':
                        for field in ('issuer_id', 'parent_asin', 'sim_batch_id', 'event_id'):
                            receipt[field] = actions[0][field]
                self.replace_rows('V08', 'registrations.jsonl', receipts + [fake])
                self.order_receipts('V08')
                self.reseal()
                result, audit = self.audit('fake-authority-' + mode)
                self.assertEqual(result.returncode, 0, result.stdout)
                clause = self.references(audit)['V08', 'R1_SIM_Q1', 'PX3']['clauses'][0]
                self.assertEqual(clause['state'], 'Supported')
                head = next(h for h in clause['version_heads'] if h['evidence_id'] == self.report('V08')['evidence_id'])
                self.assertEqual(head['revoked_versions'], [])
                self.assertIn('action_not_authorized', [a['reason'] for a in head['actions']])

    def test_missing_registered_status_actions_keep_version_checks_incomplete(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for view in ('V08', 'V09'):
            with self.subTest(view=view):
                self.restore_public(saved)
                self.replace_rows(view, 'change-actions.jsonl', [])
                self.reseal()
                result, audit = self.audit('missing-action-' + view)
                self.assertEqual(result.returncode, 0, result.stdout)
                clause = self.references(audit)[view, 'R1_SIM_Q1', 'PX3']['clauses'][0]
                self.assertEqual((clause['s'], clause['r']), (1, 0))
                self.assertFalse(clause['required_reads_complete'])
                self.assertFalse(clause['version_checks_complete'])
                self.assertEqual(clause['state'], 'Pending')
                self.assertIn('unavailable', [r['reason'] for r in clause['rejected']])

    def test_cross_scope_revision_actions_cannot_remove_the_original_claim(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for field, value in (('sample_id', 'another-sample'), ('test_scope', ['SIM-OTHER'])):
            with self.subTest(field=field):
                self.restore_public(saved)
                rows = self.rows('V09', 'materials.jsonl')
                report = next(r for r in rows if r['parent_asin'] == 'PX3' and r['kind'] == 'inspection_report' and r['version'] == 2)
                report['facts'][field] = value
                self.replace_rows('V09', 'materials.jsonl', rows)
                self.rebind_original('V09', report)
                self.reseal()
                result, audit = self.audit('cross-scope-' + field)
                self.assertEqual(result.returncode, 0, result.stdout)
                clause = self.references(audit)['V09', 'R1_SIM_Q1', 'PX3']['clauses'][0]
                self.assertEqual((clause['s'], clause['r'], clause['state']), (1, 0, 'Supported'))
                head = next(h for h in clause['version_heads'] if h['evidence_id'] == report['evidence_id'])
                self.assertEqual(head['head_version'], 1)
                self.assertIn('revision_scope_mismatch', [a['reason'] for a in head['actions']])

    def test_reference_rejects_numeric_type_aliases_but_keeps_policy_booleans(self):
        self.fixture()
        self.prepared()
        original = {name: self.rows('V09', name) for name in ('materials.jsonl', 'events.jsonl', 'change-actions.jsonl')}
        receipts = self.rows('V09', 'registrations.jsonl')
        cases = [('materials.jsonl', 'inspection_report', ('version',), 1.0),
                 ('materials.jsonl', 'inspection_sample', ('facts', 'sampled_at_ms'), True),
                 ('events.jsonl', None, ('event_start_ms',), 1790841600000.0),
                 ('change-actions.jsonl', None, ('supersedes_version',), True)]
        for index, (name, kind, path, value) in enumerate(cases):
            with self.subTest(name=name, path=path):
                for filename, rows in original.items():
                    self.replace_rows('V09', filename, rows)
                self.replace_rows('V09', 'registrations.jsonl', receipts)
                rows = copy.deepcopy(original[name])
                row = next(r for r in rows if r['parent_asin'] == 'PX3' and (kind is None or r['kind'] == kind))
                target = row
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.replace_rows('V09', name, rows)
                if name == 'materials.jsonl':
                    self.rebind_original('V09', row)
                self.reseal()
                failed, audit_root = self.audit('type-' + str(index))
                self.assertEqual(failed.returncode, 2, failed.stdout)
                self.assertFalse((audit_root / 'reference.jsonl').exists())
        for filename, rows in original.items():
            self.replace_rows('V09', filename, rows)
        self.replace_rows('V09', 'registrations.jsonl', receipts)
        self.reseal()
        valid, audit_root = self.audit('valid-bools')
        self.assertEqual(valid.returncode, 0, valid.stdout)
        rights = self.rows('V00', 'policy.json')[0]['issuers']
        self.assertEqual([r['may_create_batch'] for r in rights], [True, False, False, False, False, False, False, False])

    def test_reference_closes_master_manifest_and_snapshot_contracts(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        snapshot_path = self.package / self.view_by_name['V00']['snapshot_path']
        record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        for index, (path, key, value) in enumerate([
                (snapshot_path, 'request_profiles', 'R1_SIM_Q1'),
                (snapshot_path, 'requests_sha256', '0' * 64),
                (self.package / 'manifest.json', 'expected_status', 'Supported'),
                (record_path, 'unknown', 'extra')]):
            with self.subTest(key=key):
                self.restore_public(saved)
                obj = json.loads(path.read_bytes())
                obj[key] = value
                self.write(path, obj)
                if path != record_path:
                    self.reseal()
                result, audit_root = self.audit('closed-' + str(index))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse((audit_root / 'reference.jsonl').exists())

    def test_baseline_acceptance_checks_numbers_before_equality_and_requires_all_gates(self):
        self.fixture()
        original_record = copy.deepcopy(self.normal)
        original_acceptance = json.loads((PROJECT / self.config['normal_binding']['acceptance']['path']).read_bytes())
        cases = [('record', ('sim_verify_at_ms',), 1791417600000.0),
                 ('record', ('inputs', 'config', 'bytes'), 1.0),
                 ('acceptance', ('reviews', 'Standards', 'blocking_findings'), False),
                 ('acceptance', ('validation',), {}),
                 ('acceptance', ('validation', 'public_cli_tests', 'tests'), True),
                 ('acceptance', ('independent_reference', 'audited_batches'), 3.0)]
        outputs = []
        for index, (owner, path, value) in enumerate(cases):
            with self.subTest(owner=owner, path=path):
                record, acceptance = copy.deepcopy(original_record), copy.deepcopy(original_acceptance)
                target = record if owner == 'record' else acceptance
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.rebind_normal(record, acceptance)
                output = self.root / ('invalid-baseline-' + str(index))
                outputs.append(output)
                result = self.cli(output=output)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_baseline')
        self.assertTrue(all(not path.exists() for path in outputs))

    def test_audit_output_cannot_write_inside_the_package_or_normal_baseline(self):
        self.fixture()
        self.prepared()
        for index, protected in enumerate([self.package, self.root / 'normal/data/sim',
                                           self.root / 'normal/records/sim']):
            target = protected / ('audit-child-' + str(index))
            result, _ = self.audit(target)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertFalse(target.exists())

    def test_reference_excludes_future_and_unauthorized_revision_actions(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('future_registration', 'future_effect', 'foreign_issuer', 'wrong_target_kind')):
            with self.subTest(mode=mode):
                self.restore_public(saved)
                actions = self.rows('V09', 'change-actions.jsonl')
                if mode == 'future_registration':
                    receipts = self.rows('V09', 'registrations.jsonl')
                    for receipt in receipts:
                        if (receipt['target_id'] == self.report('V09')['evidence_id'] and receipt['version'] == 2
                                or receipt['target_kind'] == 'change_action'):
                            receipt['registered_at_ms'] = 1791417601000
                    self.replace_rows('V09', 'registrations.jsonl', receipts)
                    self.order_receipts('V09')
                else:
                    key, value = {'future_effect': ('effective_from_ms', 1791417600001),
                                  'foreign_issuer': ('issuer_id', 'SIM-RETAIL'),
                                  'wrong_target_kind': ('target_kind', 'batch')}[mode]
                    actions[0][key] = value
                    self.rebind_actions('V09', actions)
                self.reseal()
                result, audit_root = self.audit('inactive-' + str(index))
                self.assertEqual(result.returncode, 0, result.stdout)
                row = self.references(audit_root)['V09', 'R1_SIM_Q1', 'PX3']
                self.assertEqual(row['candidate_state'], 'Supported')
                if mode == 'future_effect':
                    self.assertIn('not_current_version', [r['reason'] for r in row['clauses'][0]['rejected']])

    def test_half_open_endpoints_and_historical_reports_without_ttl(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        tau = 1791417600000
        for index, (start, end, expected) in enumerate([(tau, tau + 2, 'Supported'),
                (tau - 2, tau + 1, 'Supported'), (tau - 2, tau, 'Pending'), (tau - 2, tau - 1, 'Pending')]):
            self.restore_public(saved)
            materials, events, receipts = [self.rows('V00', name) for name in
                                           ('materials.jsonl', 'events.jsonl', 'registrations.jsonl')]
            retail = next(r for r in materials if r['parent_asin'] == 'PX3' and r['kind'] == 'retail_status')
            retail.update(valid_from_ms=start, valid_to_ms=end, issued_at_ms=tau - 2)
            retail['facts']['observed_at_ms'] = tau - 2
            event = next(e for e in events if e['event_id'] == retail['event_id'])
            event.update(event_start_ms=tau - 2, event_end_ms=tau - 2)
            for receipt in receipts:
                if receipt['target_id'] in (retail['evidence_id'], event['event_id']):
                    body = retail if receipt['target_kind'] == 'material' else event
                    receipt.update(registered_at_ms=tau - 2, content_sha256=hashlib.sha256(wire(body)).hexdigest())
            for name, rows in [('materials.jsonl', materials), ('events.jsonl', events), ('registrations.jsonl', receipts)]:
                self.replace_rows('V00', name, rows)
            self.snapshot_update('V00', sealed_at_ms=tau - 2)
            self.order_receipts('V00')
            self.reseal()
            result, audit_root = self.audit('endpoint-' + str(index))
            self.assertEqual(result.returncode, 0, result.stdout)
            refs = self.references(audit_root)
            self.assertEqual(refs['V00', 'R1_SIM_Q1', 'PX3']['candidate_state'], 'Supported')
            self.assertEqual(refs['V00', 'R1_AND_R5_SIM_Q1_ON_SALE', 'PX3']['clauses'][1]['state'], expected)
        self.restore_public(saved)
        requests = [json.loads(line) for line in (self.package / 'requests.jsonl').read_bytes().splitlines()]
        requests[1]['necessary_clauses'][1]['time_scope']['verify_at_ms'] = tau + 2 * 86400000
        self.write(self.package / 'requests.jsonl', requests, rows=True)
        for name in self.view_by_name:
            self.snapshot_update(name, verify_at_ms=tau + 2 * 86400000)
        self.reseal()
        result, audit_root = self.audit('later-tau')
        self.assertEqual(result.returncode, 0, result.stdout)
        refs = self.references(audit_root)
        self.assertEqual(refs['V00', 'R1_SIM_Q1', 'PX3']['candidate_state'], 'Supported')
        self.assertEqual(refs['V00', 'R1_AND_R5_SIM_Q1_ON_SALE', 'PX3']['candidate_state'], 'Pending')

    def test_ambiguous_registration_and_unfinished_positive_scope_are_pending(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('ambiguous', 'unavailable_extra')):
            self.restore_public(saved)
            receipts = self.rows('V00', 'registrations.jsonl')
            extra = copy.deepcopy(self.receipt('V00', self.report('V00')))
            extra['registration_id'] = 'g_' + hashlib.sha256(mode.encode()).hexdigest()
            if mode == 'ambiguous':
                extra['content_sha256'] = 'f' * 64
            else:
                extra['target_id'] = 'd_' + hashlib.sha256(b'unavailable-extra-report').hexdigest()
            receipts.append(extra)
            self.replace_rows('V00', 'registrations.jsonl', receipts)
            self.order_receipts('V00')
            self.reseal()
            result, audit_root = self.audit('scope-' + str(index))
            self.assertEqual(result.returncode, 0, result.stdout)
            clause = self.references(audit_root)['V00', 'R1_SIM_Q1', 'PX3']['clauses'][0]
            self.assertEqual(clause['state'], 'Pending')
            self.assertEqual(clause['r'], 0)
            if mode == 'unavailable_extra':
                self.assertEqual(clause['s'], 1)
                self.assertFalse(clause['required_reads_complete'])

    def test_damaged_or_denied_head_never_falls_back_to_an_old_pass(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('digest', 'denied', 'revoked')):
            self.restore_public(saved)
            if mode == 'digest':
                rows = self.rows('V09', 'materials.jsonl')
                row = next(r for r in rows if r['version'] == 2)
                row['facts']['conclusion'] = 'pass'
                self.replace_rows('V09', 'materials.jsonl', rows)
            elif mode == 'denied':
                policy = copy.deepcopy(self.rows('V11', 'policy.json')[0])
                policy['read_denials'][0]['version'] = 2
                policy.pop('policy_id')
                policy['policy_id'] = 'p_' + hashlib.sha256(wire(policy)).hexdigest()
                self.replace_rows('V09', 'policy.json', [policy])
                self.snapshot_update('V09', policy_id=policy['policy_id'])
            else:
                actions = self.rows('V09', 'change-actions.jsonl')
                withdrawal = copy.deepcopy(actions[0])
                withdrawal.update(action_type='revokes', supersedes_version=None)
                withdrawal['action_id'] = 'a_' + hashlib.sha256(('Thesis-SIM-1:change_action\0' +
                    withdrawal['target_id'] + '\0' + '2\0revokes\0' + str(withdrawal['effective_from_ms'])).encode()).hexdigest()
                receipts = self.rows('V09', 'registrations.jsonl')
                receipt = copy.deepcopy(next(r for r in receipts if r['target_kind'] == 'change_action'))
                receipt.update(target_id=withdrawal['action_id'], content_sha256=hashlib.sha256(wire(withdrawal)).hexdigest(),
                    registration_id='g_' + hashlib.sha256(('Thesis-SIM-1:registration\0change_action\0' +
                                     withdrawal['action_id'] + '\0' + '1').encode()).hexdigest())
                self.replace_rows('V09', 'change-actions.jsonl', actions + [withdrawal])
                self.replace_rows('V09', 'registrations.jsonl', receipts + [receipt])
                self.order_receipts('V09')
            self.reseal()
            result, audit_root = self.audit('head-' + str(index))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(self.references(audit_root)['V09', 'R1_SIM_Q1', 'PX3']['candidate_state'], 'Pending')

    def test_misbound_receipts_cannot_borrow_another_candidates_retail_support(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for registrar in ('UNTRUSTED', 'SIM-REGISTRY'):
            with self.subTest(registrar=registrar):
                self.restore_public(saved)
                materials = self.rows('V07', 'materials.jsonl')
                own = next(r for r in materials if r['parent_asin'] == 'PX3' and r['kind'] == 'retail_status')
                donor = next(r for r in materials if r['parent_asin'] == 'PX1' and r['kind'] == 'retail_status')
                receipt = copy.deepcopy(self.receipt('V07', donor))
                receipt.update(parent_asin=own['parent_asin'], sim_batch_id=own['sim_batch_id'], event_id=own['event_id'],
                    registrar_id=registrar, registration_id='g_' + hashlib.sha256(('foreign-retail-' + registrar).encode()).hexdigest())
                self.replace_rows('V07', 'registrations.jsonl', self.rows('V07', 'registrations.jsonl') + [receipt])
                self.order_receipts('V07')
                self.reseal()
                result, audit = self.audit('foreign-retail-' + registrar)
                self.assertEqual(result.returncode, 0, result.stdout)
                row = self.references(audit)['V07', 'R1_AND_R5_SIM_Q1_ON_SALE', 'PX3']
                self.assertEqual(row['clauses'][0]['state'], 'Supported')
                self.assertEqual(row['clauses'][1]['state'], 'Pending')
                self.assertEqual(row['candidate_state'], 'Pending')
                self.assertNotIn(donor['evidence_id'], [item['id'] for item in row['clauses'][1]['adopted']])

    def test_legal_zero_and_maximum_integer_stock_do_not_change_a_status_only_request(self):
        self.fixture()
        self.prepared()
        for index, value in enumerate((0, 2**53 - 1)):
            rows = self.rows('V00', 'materials.jsonl')
            row = next(r for r in rows if r['parent_asin'] == 'PX3' and r['kind'] == 'retail_status')
            row['facts']['stock_units'] = value
            self.replace_rows('V00', 'materials.jsonl', rows)
            self.rebind_original('V00', row)
            self.reseal()
            result, audit_root = self.audit('legal-int-' + str(index))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(self.references(audit_root)['V00', 'R1_AND_R5_SIM_Q1_ON_SALE', 'PX3']['candidate_state'], 'Supported')

    def test_private_plan_labels_and_preference_sentinels_do_not_supply_answers(self):
        self.fixture()
        self.prepared()
        baseline, baseline_root = self.audit()
        self.assertEqual(baseline.returncode, 0, baseline.stdout)
        reference = (baseline_root / 'reference.jsonl').read_bytes()
        private = self.package / 'private/mutation-plan.jsonl'
        plan = [json.loads(line) for line in private.read_bytes().splitlines()]
        for row in plan:
            row['view_name'] = 'WRONG_LABEL'
            row['expected_status'] = 'WRONG_ANSWER'
        self.write(private, plan, rows=True)
        record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
        record = json.loads(record_path.read_bytes())
        record['audit_private']['mutation-plan.jsonl'].update(bytes=private.stat().st_size,
            sha256=hashlib.sha256(private.read_bytes()).hexdigest())
        self.write(record_path, record)
        renamed, renamed_root = self.audit('renamed-plan')
        self.assertEqual(renamed.returncode, 0, renamed.stdout)
        self.assertEqual((renamed_root / 'reference.jsonl').read_bytes(), reference)
        self.write(self.root / 'private/evaluation.json', {'target_parent_asin': 'PX1', 'rating': 5, 'text': 'PRIVATE_TARGET'})
        self.write(self.root / 'model-results.json', {'winner': 'PX2', 'result': 'MODEL_RESULT'})
        fresh_root = self.root / 'fresh'
        fresh = self.cli(output=fresh_root)
        self.assertEqual(fresh.returncode, 0, fresh.stdout)
        fresh_record = json.loads(fresh.stdout)
        for name, spec in self.record['components'].items():
            self.assertEqual((self.output / spec['path']).read_bytes(),
                             (fresh_root / fresh_record['components'][name]['path']).read_bytes())
        for filename in ('prepare_data.py', 'sim_scenarios.py'):
            self.assertNotIn(b'PRIVATE_TARGET', (PROJECT / filename).read_bytes())

    def test_request_versions_and_metadata_strings_are_validated_as_closed_types(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('request_schema', 'git_head_integer', 'git_head_format', 'denial_target_integer')):
            with self.subTest(mode=mode):
                self.restore_public(saved)
                if mode == 'request_schema':
                    requests = [json.loads(line) for line in (self.package / 'requests.jsonl').read_bytes().splitlines()]
                    requests[0]['schema_version'] = 'sim-scenario-request-2.0.0'
                    self.write(self.package / 'requests.jsonl', requests, rows=True)
                    self.reseal()
                elif mode.startswith('git_head'):
                    record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
                    record = json.loads(record_path.read_bytes())
                    record['code_state']['git_head_sha'] = 0 if mode.endswith('integer') else 'not-a-commit'
                    self.write(record_path, record)
                    reused = self.cli()
                    self.assertEqual(reused.returncode, 2)
                    self.assertEqual(json.loads(reused.stdout)['error']['code'], 'output_conflict')
                else:
                    policy = self.rows('V11', 'policy.json')[0]
                    policy['read_denials'][0]['target_id'] = 0
                    policy.pop('policy_id')
                    policy['policy_id'] = 'p_' + hashlib.sha256(wire(policy)).hexdigest()
                    self.replace_rows('V11', 'policy.json', [policy])
                    self.snapshot_update('V11', policy_id=policy['policy_id'])
                    self.reseal()
                result, audit = self.audit('metadata-types-' + str(index))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads((audit / 'check.json').read_bytes())['status'], 'failed')
                self.assertFalse((audit / 'reference.jsonl').exists())

    def test_unknown_wire_schema_fails_but_untrusted_receipts_and_unknown_values_are_pending(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('schema', 'backend', 'unknown_value')):
            with self.subTest(mode=mode):
                self.restore_public(saved)
                if mode == 'backend':
                    rows = self.rows('V00', 'registrations.jsonl')
                    next(r for r in rows if r['target_id'] == self.report('V00')['evidence_id'])['registry_backend'] = 'untrusted_registry'
                    self.replace_rows('V00', 'registrations.jsonl', rows)
                else:
                    rows = self.rows('V00', 'materials.jsonl')
                    row = next(r for r in rows if r['evidence_id'] == self.report('V00')['evidence_id'])
                    if mode == 'schema':
                        row['schema_version'] = 'unsupported-material-99'
                    else:
                        row['facts']['conclusion'] = 'unknown'
                    self.replace_rows('V00', 'materials.jsonl', rows)
                    self.rebind_original('V00', row)
                self.reseal()
                result, audit_root = self.audit('unsupported-' + str(index))
                self.assertEqual(result.returncode, 2 if mode == 'schema' else 0, result.stdout)
                if mode != 'schema':
                    clause = self.references(audit_root)['V00', 'R1_SIM_Q1', 'PX3']['clauses'][0]
                    self.assertEqual(clause['state'], 'Pending')
                    if mode == 'unknown_value':
                        self.assertIn('unknown_assertion', [r['reason'] for r in clause['rejected']])

    def test_junctions_cannot_redirect_sources_generation_or_audit_writes(self):
        self.fixture()
        self.prepared()
        destination = self.root / 'junction-target'
        destination.mkdir()
        sentinel = destination / 'keep.txt'
        sentinel.write_bytes(b'UNCHANGED')
        junction = self.root / 'junction'
        created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(destination)],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(created.returncode, 0, created.stderr.decode(errors='replace'))
        self.assertTrue(junction.resolve().is_relative_to(self.root))
        self.addCleanup(junction.rmdir)
        rejected = self.cli(output=junction / 'generated')
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        self.assertEqual(json.loads(rejected.stdout)['error']['code'], 'invalid_path')
        audit, _ = self.audit(junction / 'audit')
        self.assertEqual(audit.returncode, 2, audit.stdout)
        source = destination / 'config.json'
        source.write_bytes(self.config_path.read_bytes())
        self.config_path = junction / 'config.json'
        bad_source = self.cli(output=self.root / 'bad-source-output')
        self.assertEqual(bad_source.returncode, 2, bad_source.stdout)
        self.assertEqual(json.loads(bad_source.stdout)['error']['code'], 'invalid_path')
        self.assertEqual({p.name for p in destination.iterdir()}, {'keep.txt', 'config.json'})
        self.assertEqual(sentinel.read_bytes(), b'UNCHANGED')

    def test_nonobject_originals_and_malformed_component_maps_fail_with_a_check_record(self):
        self.fixture()
        self.prepared()
        saved = self.capture_public()
        for index, mode in enumerate(('original_scalar', 'component_list')):
            self.restore_public(saved)
            if mode == 'original_scalar':
                rows = self.rows('V00', 'materials.jsonl')
                rows[0] = 0
                self.replace_rows('V00', 'materials.jsonl', rows)
                self.reseal()
            else:
                record_path = self.output / 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
                record = json.loads(record_path.read_bytes())
                record['components'] = []
                self.write(record_path, record)
            result, audit_root = self.audit('object-type-' + str(index))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads((audit_root / 'check.json').read_bytes())['status'], 'failed')
            self.assertFalse((audit_root / 'reference.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
