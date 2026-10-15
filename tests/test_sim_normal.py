"""Ticket10 behavior observed only at the approved S1/S2 subprocess seams."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
VERIFIER = PROJECT / '.scratch/data-preparation/diagnostics/verify_sim10.py'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


class SimNormalTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.config = json.loads((PROJECT / 'config/sim-normal-1.0.0.json').read_bytes())
        self.catalog = [
            {'parent_asin': 'DEMO-P001', 'crop': 'rice', 'status': 'included',
             'metadata': {'price': 2.5, 'rating': 5, 'text': 'CLOSED_METADATA_SENTINEL'}},
            {'parent_asin': '无评论 商品', 'crop': '燕麦', 'status': 'included', 'metadata': {}},
        ]
        self.catalog_path = self.write('inputs/catalog.jsonl', self.catalog, rows=True)
        self.record = {'stage': 'catalog', 'status': 'catalog_complete',
                       'scope_version': 'grain-A-1.1.15', 'counts': {'included': 2},
                       'catalog_path': self.relative(self.catalog_path),
                       'catalog_sha256': hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()}
        self.record_path = self.write('inputs/catalog-record.json', self.record)
        self.config['catalog_binding'].update(
            record_path=self.relative(self.record_path),
            record_sha256=hashlib.sha256(self.record_path.read_bytes()).hexdigest(),
            component_sha256=self.record['catalog_sha256'], expected_parent_count=2)
        self.config_path = self.write('inputs/config.json', self.config)
        self.output = self.root / 'output'

    def relative(self, path):
        return path.relative_to(PROJECT).as_posix()

    def write(self, name, value, rows=False):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b''.join(encoded(row) + b'\n' for row in value) if rows else encoded(value) + b'\n')
        return path

    def run_cli(self, *extra, omit=(), output=None):
        args = {'--catalog-record': self.record_path, '--sim-config': self.config_path,
                '--output-root': output or self.output}
        command = [sys.executable, str(PROJECT / 'prepare_data.py'), '--stage', 'sim_normal']
        for key, value in args.items():
            if key not in omit:
                command.extend([key, str(value)])
        return subprocess.run(command + list(extra), cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')

    def rebind_catalog(self):
        self.write('inputs/catalog.jsonl', self.catalog, rows=True)
        self.record['catalog_sha256'] = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()
        self.write('inputs/catalog-record.json', self.record)
        self.config['catalog_binding'].update(record_sha256=hashlib.sha256(self.record_path.read_bytes()).hexdigest(),
                                               component_sha256=self.record['catalog_sha256'])
        self.write('inputs/config.json', self.config)

    def test_missing_stage_dependencies_are_structured_failures(self):
        for missing in ('--catalog-record', '--sim-config', '--output-root'):
            with self.subTest(missing=missing):
                result = self.run_cli(omit=(missing,))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout), {'stage': 'sim_normal',
                    'status': 'sim_normal_incomplete', 'error': {'code': 'invalid_arguments'}})
        self.assertFalse(self.output.exists())

    def test_unbound_protocol_or_profile_needs_confirmation(self):
        variants = []
        for field in ('version', 'record_sha256', 'draft_sha256', 'record_path'):
            config = copy.deepcopy(self.config)
            config['protocol_binding'][field] = 'unapproved'
            variants.append(config)
        config = copy.deepcopy(self.config)
        config['profile'] = 'other_profile'
        variants.append(config)
        for config in variants:
            self.write('inputs/config.json', config)
            result = self.run_cli()
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout), {'stage': 'sim_normal', 'status': 'needs_confirmation',
                                                        'error': {'code': 'unapproved_protocol'}})
        self.assertFalse(self.output.exists())

    def test_config_is_closed_typed_integer_json(self):
        variants = []
        for key, value in [('unknown', 1), ('clock', {}), ('facts', []), ('version', '../escape')]:
            config = copy.deepcopy(self.config)
            config[key] = value
            variants.append(encoded(config))
        for value in (True, 1.5, -1, 9007199254740992):
            config = copy.deepcopy(self.config)
            config['facts']['quantity_units'] = value
            variants.append(encoded(config))
        variants.extend([b'{"version":"one","version":"two"}', b'{"x":NaN}', b'[]'])
        for raw in variants:
            with self.subTest(raw=raw[:80]):
                self.config_path.write_bytes(raw)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_config')
        self.assertFalse(self.output.exists())

    def test_normal_baseline_matches_the_hand_worked_single_product(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record['counts'], {'parents': 2, 'batches': 2, 'events': 12,
                                            'materials': 16, 'registrations': 30})
        self.assertEqual(record['status'], 'normal_sim_prepared')
        self.assertEqual(record['independent_acceptance'], 'pending_separate_record')
        self.assertEqual(record['formal_package_status'], 'not_built')
        components = {}
        raw_lines = {}
        for name, binding in record['components'].items():
            raw = (self.output / binding['path']).read_bytes()
            self.assertTrue(raw.endswith(b'\n'))
            self.assertNotIn(b'\r', raw)
            self.assertNotIn(b'CLOSED_METADATA_SENTINEL', raw)
            self.assertEqual(binding['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(binding['bytes'], len(raw))
            raw_lines[name] = raw.splitlines()
            components[name] = [json.loads(line) for line in raw_lines[name]]
            self.assertEqual(binding['records'], len(components[name]))
            for row, line in zip(components[name], raw_lines[name]):
                self.assertEqual(encoded(row), line)
        self.assertEqual(set(components), {'batches.jsonl', 'events.jsonl', 'materials.jsonl',
                                          'registrations.jsonl', 'policy.json', 'snapshot.json'})
        batch = components['batches.jsonl'][0]
        self.assertEqual(batch, {
            'catalog_version': 'grain-A-1.1.15', 'created_at_ms': 1790812800000, 'crop': 'rice',
            'issuer_id': 'SIM-PRODUCER', 'parent_asin': 'DEMO-P001',
            'protocol_version': 'sim-evidence-protocol-1.0.0', 'schema_version': 'sim-batch-1.0.0',
            'sim_batch_id': 'b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04',
            'sim_profile_id': 'normal_six_stage_v1', 'source': 'SIM', 'version': 1})
        events = components['events.jsonl'][:6]
        self.assertEqual([e['stage'] for e in events],
                         ['harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail'])
        self.assertEqual(events[3]['event_id'],
                         'e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6')
        for previous, event in zip([None] + events, events):
            self.assertEqual(event['predecessor_event_ids'], [previous['event_id']] if previous else [])
            self.assertEqual(event['sim_batch_id'], batch['sim_batch_id'])
        materials = components['materials.jsonl'][:8]
        self.assertEqual(materials[3]['facts']['sample_id'],
                         's_9082e4616e39185b4700ac663b5c479408ded39790a8cf28a146a9b872cd3289')
        self.assertEqual(materials[4]['facts']['sample_id'], materials[3]['facts']['sample_id'])
        self.assertEqual(materials[1]['facts']['harvest_event_id'], events[0]['event_id'])
        self.assertEqual(materials[5]['facts']['transport_segment_id'],
                         't_256ec93a00a3481029e8ecfafbacfc9d7279a1a1699a4d1ae0269098c61522e0')
        self.assertEqual(materials[5]['facts']['transport_segment_id'], materials[6]['facts']['transport_segment_id'])
        for index, digest in [(3, 'defc69f661bc92ee5a92f16b2bb9f956b74066409bad558ce1ff22896c6e97d8'),
                              (4, 'b2666c82d25aa867050b78ca64c457caf3edd5ddfcf021a361b3609733580b5d')]:
            self.assertEqual(hashlib.sha256(raw_lines['materials.jsonl'][index]).hexdigest(), digest)
        registrations = components['registrations.jsonl']
        self.assertEqual([r['sequence'] for r in registrations], list(range(1, 31)))
        targets = {}
        for name, key in [('batches.jsonl', 'sim_batch_id'), ('events.jsonl', 'event_id'),
                          ('materials.jsonl', 'evidence_id')]:
            for row, raw in zip(components[name], raw_lines[name]):
                targets[row[key]] = hashlib.sha256(raw).hexdigest()
        self.assertEqual({r['target_id']: r['content_sha256'] for r in registrations}, targets)
        self.assertFalse(list(self.output.rglob('*acceptance.json')))

    def test_catalog_must_match_binding_and_contain_unique_included_parents(self):
        original = (copy.deepcopy(self.catalog), copy.deepcopy(self.record), copy.deepcopy(self.config))
        for mutation in ('record_hash', 'component_hash', 'stage', 'status', 'version', 'count',
                         'duplicate', 'missing_parent', 'empty_crop', 'nul_parent', 'excluded'):
            with self.subTest(mutation=mutation):
                self.catalog, self.record, self.config = copy.deepcopy(original)
                if mutation in ('stage', 'status'):
                    self.record[mutation] = 'incomplete'
                elif mutation == 'version':
                    self.record['scope_version'] = 'other'
                elif mutation == 'count':
                    self.record['counts']['included'] = 3
                elif mutation == 'duplicate':
                    self.catalog[1] = copy.deepcopy(self.catalog[0])
                elif mutation == 'missing_parent':
                    del self.catalog[1]['parent_asin']
                elif mutation == 'empty_crop':
                    self.catalog[1]['crop'] = ''
                elif mutation == 'nul_parent':
                    self.catalog[1]['parent_asin'] = 'bad\0id'
                elif mutation == 'excluded':
                    self.catalog[1]['status'] = 'excluded'
                self.rebind_catalog()
                if mutation in ('record_hash', 'component_hash'):
                    field = 'record_sha256' if mutation == 'record_hash' else 'component_sha256'
                    self.config['catalog_binding'][field] = '0' * 64
                    self.write('inputs/config.json', self.config)
                result = self.run_cli(output=self.root / mutation)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_catalog')
                self.assertFalse((self.root / mutation).exists())

    def test_illegal_time_or_current_validity_cannot_publish(self):
        changes = [
            ('clock', 'verify_at_ms', None, 1791374999999),
            ('clock', 'batch_created_at_ms', None, 1790845200001),
            ('clock', 'batch_registered_at_ms', None, 0),
            ('events', 'storage', 'end_ms', 1790935199999),
            ('events', 'packaging', 'start_ms', 1790845199999),
            ('events', 'harvest', 'registered_at_ms', 1790845199999),
            ('clock', 'sampled_at_ms', None, 1791104399999),
            ('clock', 'test_started_at_ms', None, 1791105299999),
            ('clock', 'test_completed_at_ms', None, 1791190800001),
            ('materials', 'inspection_report', 'issued_at_ms', 1791188999999),
            ('materials', 'inspection_sample', 'registered_at_ms', 1791105600000),
            ('materials', 'retail_status', 'registered_at_ms', 1791374699999),
            ('clock', 'retail_valid_to_ms', None, 1791417600000),
            ('clock', 'retail_valid_from_ms', None, 1791417600001),
        ]
        for group, key, child, value in changes:
            with self.subTest(change=(group, key, child)):
                config = copy.deepcopy(self.config)
                if child:
                    config[group][key][child] = value
                else:
                    config[group][key] = value
                self.write('inputs/config.json', config)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_config')
                self.assertFalse(self.output.exists())

    def test_only_confirmed_sim_issuers_and_enumerations_are_enabled(self):
        variants = []
        config = copy.deepcopy(self.config)
        config['issuers'][4]['material_kinds'] = ['transport_receipt']
        variants.append(config)
        config = copy.deepcopy(self.config)
        config['issuers'].reverse()
        variants.append(config)
        config = copy.deepcopy(self.config)
        config['issuers'][0]['may_create_batch'] = False
        variants.append(config)
        for group, key, value in [('registry', 'read_principal_id', 'MODEL'),
                                  ('registry', 'identity_mode', 'signature_verified'),
                                  ('facts', 'report_conclusion', 'fail'),
                                  ('facts', 'test_scope', ['UNAPPROVED']),
                                  ('reference_request', 'required_conclusion', 'fail')]:
            config = copy.deepcopy(self.config)
            config[group][key] = value
            variants.append(config)
        for key in ('schema_version', 'byte_contract', 'id_namespace'):
            config = copy.deepcopy(self.config)
            config[key] = 'unapproved'
            variants.append(config)
        for index, config in enumerate(variants):
            self.write('inputs/config.json', config)
            result = self.run_cli(output=self.root / f'case-{index}')
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_config')
            self.assertFalse((self.root / f'case-{index}').exists())

    def test_other_stage_arguments_are_rejected(self):
        for flag in ('--review-record', '--split-record', '--task-config', '--access-probe', '--source-manifest'):
            result = self.run_cli(flag, str(self.root / 'never-read'))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_arguments')
        self.assertFalse(self.output.exists())

    def test_paths_and_all_write_ancestors_are_checked_before_writing(self):
        result = self.run_cli(output=PROJECT.parent / 'ticket10-forbidden')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_path')
        self.assertFalse((PROJECT.parent / 'ticket10-forbidden').exists())
        target = self.root / 'junction-target'
        target.mkdir()
        linked_root = self.root / 'junction-root'
        linked_root.mkdir()
        junction = linked_root / 'data'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        try:
            result = self.run_cli(output=linked_root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_path')
            self.assertEqual(list(target.iterdir()), [])
        finally:
            junction.rmdir()
        input_target = self.root / 'input-target'
        input_target.mkdir()
        input_link = self.root / 'input-link'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(input_link), str(input_target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        try:
            self.record['catalog_path'] = self.relative(input_link / 'catalog.jsonl')
            (input_target / 'catalog.jsonl').write_bytes(self.catalog_path.read_bytes())
            self.write('inputs/catalog-record.json', self.record)
            self.config['catalog_binding']['record_sha256'] = hashlib.sha256(self.record_path.read_bytes()).hexdigest()
            self.write('inputs/config.json', self.config)
            result = self.run_cli()
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_path')
        finally:
            input_link.rmdir()

    def test_reuse_is_immutable_and_new_roots_reproduce_exact_bytes(self):
        first = self.run_cli()
        self.assertEqual(first.returncode, 0, first.stdout)
        record = json.loads(first.stdout)
        record_path = self.output / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
        original = record_path.read_bytes()
        repeated = self.run_cli()
        self.assertEqual(repeated.returncode, 0, repeated.stdout)
        self.assertEqual(json.loads(repeated.stdout), record)
        self.assertEqual(record_path.read_bytes(), original)
        fresh_root = self.root / 'fresh'
        fresh = self.run_cli(output=fresh_root)
        self.assertEqual(fresh.returncode, 0, fresh.stdout)
        self.assertEqual(json.loads(fresh.stdout)['snapshot_id'], record['snapshot_id'])
        for component in record['components'].values():
            self.assertEqual((fresh_root / component['path']).read_bytes(), (self.output / component['path']).read_bytes())
        self.config_path.write_bytes(self.config_path.read_bytes() + b' ')
        changed = self.run_cli()
        self.assertEqual(changed.returncode, 2)
        self.assertEqual(json.loads(changed.stdout)['error']['code'], 'output_conflict')
        self.write('inputs/config.json', self.config)
        damaged = self.output / record['components']['materials.jsonl']['path']
        damaged.write_bytes(damaged.read_bytes() + b' ')
        before = damaged.read_bytes()
        refused = self.run_cli()
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)['error']['code'], 'output_conflict')
        self.assertEqual(damaged.read_bytes(), before)
        self.assertEqual(record_path.read_bytes(), original)
        occupied = self.root / 'occupied'
        occupied_dir = occupied / 'data/sim/grain-A-1.1.15/sim-normal-1.0.0'
        occupied_dir.mkdir(parents=True)
        (occupied_dir / 'old.txt').write_bytes(b'old-version-sentinel')
        result = self.run_cli(output=occupied)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'output_conflict')
        self.assertEqual((occupied_dir / 'old.txt').read_bytes(), b'old-version-sentinel')

    def run_audit(self, record=None, audit=None):
        record = record or self.output / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
        audit = audit or self.root / 'audit'
        return subprocess.run([sys.executable, str(VERIFIER), '--record', str(record), '--audit-root', str(audit)],
                              cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')

    def reseal_fixture(self, record):
        """Update fixture envelopes after changing public raw bytes; never supplies R1 answers."""
        snapshot_path = self.output / record['components']['snapshot.json']['path']
        snapshot = json.loads(snapshot_path.read_bytes())
        for name, component in record['components'].items():
            if name == 'snapshot.json':
                continue
            raw = (self.output / component['path']).read_bytes()
            component.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), records=len(raw.splitlines()))
            snapshot['components'][name] = {key: component[key] for key in ('sha256', 'bytes', 'records')}
        del snapshot['snapshot_id']
        snapshot['snapshot_id'] = 'n_' + hashlib.sha256(b'Thesis-SIM-1:snapshot\0' + encoded(snapshot)).hexdigest()
        snapshot_path.write_bytes(encoded(snapshot) + b'\n')
        raw = snapshot_path.read_bytes()
        record['snapshot_id'] = snapshot['snapshot_id']
        record['components']['snapshot.json'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), records=1)
        raw = self.config_path.read_bytes()
        record['inputs']['config'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        core = {key: record[key] for key in ('stage', 'catalog_version', 'sim_version', 'profile',
                                           'protocol_version', 'inputs', 'producer_sha256')}
        record['reuse_fingerprint_sha256'] = hashlib.sha256(encoded(core)).hexdigest()
        path = self.output / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
        path.write_bytes(encoded(record) + b'\n')

    def test_independent_audit_derives_r1_from_originals_and_receipts(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0, generated.stdout)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 0, audited.stdout + audited.stderr)
        check = json.loads((self.root / 'audit/check.json').read_bytes())
        self.assertEqual(check['status'], 'passed')
        self.assertEqual(check['state_counts'], {'Supported': 2, 'Refuted': 0, 'Pending': 0, 'Conflict': 0})
        refs = [json.loads(line) for line in (self.root / 'audit/reference-r1.jsonl').read_bytes().splitlines()]
        example = next(row for row in refs if row['parent_asin'] == 'DEMO-P001')
        self.assertEqual(example['state'], 'Supported')
        self.assertEqual(example['derivation'], {'batch_event_binding': True, 'sample_id_match': True,
            'required_project_covered': True, 'material_time_valid': True, 'issuer_and_read_authorized': True,
            'observed_report_conclusion': 'pass', 'requested_conclusion': 'pass',
            'selected_versions': {'sample': 1, 'report': 1}, 'related_registration_count': 4})
        self.assertEqual({row['content_sha256'] for row in example['adopted_evidence']},
            {'defc69f661bc92ee5a92f16b2bb9f956b74066409bad558ce1ff22896c6e97d8',
             'b2666c82d25aa867050b78ca64c457caf3edd5ddfcf021a361b3609733580b5d'})
        self.assertEqual(len(example['registration_ids']), 4)
        self.assertEqual(example['rejected_evidence'], [])
        self.assertTrue(example['scope_complete'] and example['support_present'])
        self.assertFalse(example['refutation_present'])

    def test_independent_audit_does_not_accept_self_declared_extra_authority(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        policy_path = self.output / record['components']['policy.json']['path']
        policy = json.loads(policy_path.read_bytes())
        policy['issuers'][0]['material_kinds'].append('retail_status')
        self.config['issuers'] = policy['issuers']
        self.write('inputs/config.json', self.config)
        policy_path.write_bytes(encoded(policy) + b'\n')
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')
        self.assertFalse(list(self.output.rglob('*acceptance.json')))

    def test_independent_audit_rejects_an_unrecognized_snapshot_schema(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        snapshot_path = self.output / record['components']['snapshot.json']['path']
        snapshot = json.loads(snapshot_path.read_bytes())
        snapshot['schema_version'] = 'unapproved-schema'
        snapshot_path.write_bytes(encoded(snapshot) + b'\n')
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')

    def test_independent_audit_checks_declared_event_and_material_order(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        for name in ('events.jsonl', 'materials.jsonl'):
            path = self.output / record['components'][name]['path']
            lines = path.read_bytes().splitlines()
            path.write_bytes(b'\n'.join(reversed(lines)) + b'\n')
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')

    def test_independent_audit_cannot_write_inside_original_components(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        original_dir = (self.output / record['components']['materials.jsonl']['path']).parent
        before = {p.name: p.read_bytes() for p in original_dir.iterdir()}
        result = self.run_audit(audit=original_dir / 'audit')
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual({p.name for p in original_dir.iterdir()}, set(before))
        for name, raw in before.items():
            self.assertEqual((original_dir / name).read_bytes(), raw)

    def test_independent_audit_retains_failed_check_for_a_broken_record(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record_path = self.output / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
        record_path.write_bytes(b'{"stage":"sim_normal"}\n')
        result = self.run_audit()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')
        self.assertFalse((self.root / 'audit/reference-r1.jsonl').exists())

    def test_closed_metadata_and_sibling_private_files_do_not_change_sim_bytes(self):
        first = self.run_cli()
        self.assertEqual(first.returncode, 0)
        original = json.loads(first.stdout)
        self.catalog[0]['metadata'] = {'target_parent_asin': 'PRIVATE_TARGET_CHANGED',
            'rating': 1.25, 'comments': ['PRIVATE_COMMENT_CHANGED'], 'model_result': 'PRIVATE_MODEL_CHANGED'}
        self.rebind_catalog()
        self.write('private/evaluation-labels.json', {'target': 'CHANGED'})
        self.write('private/reviews.json', {'text': 'CHANGED'})
        second_root = self.root / 'isolation-second'
        second = self.run_cli(output=second_root)
        self.assertEqual(second.returncode, 0, second.stdout)
        changed = json.loads(second.stdout)
        self.assertEqual(set(changed['inputs']), {'config', 'protocol_record', 'protocol_draft', 'catalog_record', 'catalog'})
        self.assertEqual(changed['snapshot_id'], original['snapshot_id'])
        for component in original['components'].values():
            self.assertEqual((self.output / component['path']).read_bytes(), (second_root / component['path']).read_bytes())

    def test_independent_reference_uses_report_facts_and_requires_sample_binding(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        materials_path = self.output / record['components']['materials.jsonl']['path']
        materials = [json.loads(line) for line in materials_path.read_bytes().splitlines()]
        for row in materials:
            if row['parent_asin'] == 'DEMO-P001' and row['kind'] == 'inspection_report':
                row['facts']['conclusion'] = 'fail'
            if row['parent_asin'] != 'DEMO-P001' and row['kind'] == 'inspection_report':
                row['facts']['sample_id'] = 'unbound-sample'
        materials_path.write_bytes(b''.join(encoded(row) + b'\n' for row in materials))
        registrations_path = self.output / record['components']['registrations.jsonl']['path']
        registrations = [json.loads(line) for line in registrations_path.read_bytes().splitlines()]
        digests = {row['evidence_id']: hashlib.sha256(encoded(row)).hexdigest() for row in materials}
        for row in registrations:
            if row['target_kind'] == 'material':
                row['content_sha256'] = digests[row['target_id']]
        registrations_path.write_bytes(b''.join(encoded(row) + b'\n' for row in registrations))
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        refs = [json.loads(line) for line in (self.root / 'audit/reference-r1.jsonl').read_bytes().splitlines()]
        self.assertEqual({row['parent_asin']: row['state'] for row in refs}, {'DEMO-P001': 'Refuted', '无评论 商品': 'Pending'})
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')

    def test_independent_audit_rejects_changed_original_bytes_and_preserves_them(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        path = self.output / record['components']['materials.jsonl']['path']
        path.write_bytes(path.read_bytes().replace(b'"pass"', b'"fail"', 1))
        corrupted = path.read_bytes()
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2)
        self.assertEqual(json.loads((self.root / 'audit/check.json').read_bytes())['status'], 'failed')
        self.assertEqual(path.read_bytes(), corrupted)
        self.assertFalse((self.root / 'audit/reference-r1.jsonl').exists())

    def test_independent_audit_rejects_boolean_registration_version(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        path = self.output / record['components']['registrations.jsonl']['path']
        receipts = [json.loads(line) for line in path.read_bytes().splitlines()]
        receipts[0]['version'] = True
        path.write_bytes(b''.join(encoded(row) + b'\n' for row in receipts))
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        self.assertIn('integer_type', json.loads((self.root / 'audit/check.json').read_bytes())['errors'])
        self.assertFalse((self.root / 'audit/reference-r1.jsonl').exists())

    def test_independent_normal_audit_rejects_extra_report_projects(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        record = json.loads(generated.stdout)
        path = self.output / record['components']['materials.jsonl']['path']
        materials = [json.loads(line) for line in path.read_bytes().splitlines()]
        changed = next(row for row in materials if row['parent_asin'] == 'DEMO-P001' and row['kind'] == 'inspection_report')
        changed['facts']['test_scope'].append('UNAPPROVED')
        path.write_bytes(b''.join(encoded(row) + b'\n' for row in materials))
        receipt_path = self.output / record['components']['registrations.jsonl']['path']
        receipts = [json.loads(line) for line in receipt_path.read_bytes().splitlines()]
        receipt = next(row for row in receipts if row['target_id'] == changed['evidence_id'])
        receipt['content_sha256'] = hashlib.sha256(encoded(changed)).hexdigest()
        receipt_path.write_bytes(b''.join(encoded(row) + b'\n' for row in receipts))
        self.reseal_fixture(record)
        audited = self.run_audit()
        self.assertEqual(audited.returncode, 2, audited.stdout)
        check = json.loads((self.root / 'audit/check.json').read_bytes())
        self.assertEqual(check['status'], 'failed')
        # Coverage can support R1 while the fixed normal component contract fails.
        self.assertEqual(check['state_counts']['Supported'], 2)
        self.assertIn('normal_r1_facts:DEMO-P001', check['errors'])


if __name__ == '__main__':
    unittest.main()
