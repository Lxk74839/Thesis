"""Independent evidence reference: only original facts, no producer or plan imports."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import stat
import sys


PROJECT = Path(__file__).resolve().parents[3]
KINDS = 'harvest_record packaging_binding storage_log inspection_sample inspection_report transport_dispatch transport_receipt retail_status'.split()
FILES = 'batches.jsonl events.jsonl materials.jsonl registrations.jsonl change-actions.jsonl policy.json snapshot.json'.split()
SCHEMAS = {
    'batches.jsonl': 'schema_version source parent_asin crop catalog_version sim_batch_id sim_profile_id protocol_version issuer_id version created_at_ms',
    'events.jsonl': 'schema_version source event_id parent_asin sim_batch_id stage actor_id version event_start_ms event_end_ms predecessor_event_ids',
    'materials.jsonl': 'schema_version source evidence_id parent_asin sim_batch_id event_id kind issuer_id temporal_mode version issued_at_ms facts',
    'registrations.jsonl': 'schema_version source registry_backend registration_id target_kind target_id version sequence parent_asin sim_batch_id event_id issuer_id content_sha256 registrar_id receipt_status registered_at_ms',
    'change-actions.jsonl': 'schema_version source action_id action_type target_kind target_id target_version supersedes_version parent_asin sim_batch_id event_id issuer_id issued_at_ms effective_from_ms',
    'policy.json': 'schema_version source policy_id catalog_version sim_version identity_mode creation_source issuers registrar_id read_principal_id read_scope status_change_authority',
    'snapshot.json': 'schema_version source catalog_version scenario_version base_sim_version base_snapshot_id protocol_version policy_id sealed_at_ms verify_at_ms cutoff_sequence request_profiles requests_sha256 components snapshot_id',
}
FACTS = {
    'harvest_record': 'crop origin_area_id harvested_at_ms',
    'packaging_binding': 'harvest_event_id packaged_at_ms package_condition quantity_units unit',
    'storage_log': 'coverage_start_ms coverage_end_ms segments',
    'inspection_sample': 'sample_id sampled_at_ms',
    'inspection_report': 'sample_id test_scope test_started_at_ms test_completed_at_ms conclusion',
    'transport_dispatch': 'transport_segment_id from_location_id to_location_id quantity_units unit departed_at_ms',
    'transport_receipt': 'transport_segment_id from_location_id to_location_id quantity_units unit arrived_at_ms handover_status',
    'retail_status': 'observed_at_ms location_id status stock_units unit',
}
NUMBERS = {'version', 'sequence', 'bytes', 'records', 'cutoff_sequence', 'quantity_units', 'stock_units',
           'target_version', 'supersedes_version', 'tests', 'audited_batches', 'blocking_findings', 'nonblocking_findings'}


def insist(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def distinct(pairs):
    result = {}
    for key, value in pairs:
        insist(key not in result, 'duplicate_key')
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=distinct,
                      parse_constant=lambda value: insist(False, 'nonfinite_json'))


def integer(value, positive=False):
    insist(type(value) is int and (1 if positive else 0) <= value <= 2**53 - 1, 'integer_type')


def fields(obj, names):
    insist(type(obj) is dict and set(obj) == set(names.split()), 'closed_fields')


def primitives(value, key=''):
    if key.endswith('_ms') or key in NUMBERS:
        if value is None and key in ('ttl_ms', 'supersedes_version'):
            return
        integer(value, positive=key in ('version', 'sequence', 'target_version', 'supersedes_version'))
    elif key in ('may_create_batch', 'worktree_dirty'):
        insist(type(value) is bool, 'boolean_type')
    elif key in ('counts', 'state_counts'):
        insist(type(value) is dict, 'count_structure')
        for count in value.values():
            integer(count)
    elif type(value) is dict:
        for name, child in value.items():
            primitives(child, name)
    elif type(value) is list:
        insist(len({canonical(child) for child in value}) == len(value), 'duplicate_array_item')
        for child in value:
            primitives(child)
    else:
        insist(value is None or type(value) is int or (type(value) is str and bool(value) and '\0' not in value), 'primitive_type')
        if type(value) is int:
            integer(value)


def atom_strings(obj, excluded=()):
    for key, value in obj.items():
        if key not in excluded and not key.endswith('_ms') and key not in NUMBERS:
            insist(type(value) is str and bool(value), 'string_type')


def validate_row(filename, row):
    primitives(row)
    insist(type(row) is dict, 'record_object')
    version_tags = {'batches.jsonl': 'sim-batch-1.0.0', 'events.jsonl': 'sim-event-1.0.0',
                    'materials.jsonl': 'sim-material-1.0.0', 'change-actions.jsonl': 'sim-change-action-1.0.0',
                    'requests.jsonl': 'sim-scenario-request-1.0.0'}
    if filename in version_tags:
        insist(row.get('schema_version') == version_tags[filename], 'unsupported_schema')
    if filename == 'registrations.jsonl':
        insist(row.get('target_kind') in ('batch', 'event', 'material', 'change_action'), 'registry_target_kind')
        expected_tag = 'sim-scenario-registration-1.0.0' if row['target_kind'] == 'change_action' else 'sim-registration-1.0.0'
        insist(row.get('schema_version') == expected_tag, 'unsupported_schema')
    if filename in SCHEMAS:
        expected = SCHEMAS[filename]
        if filename == 'materials.jsonl' and row.get('kind') == 'retail_status':
            expected += ' valid_from_ms valid_to_ms'
        if filename == 'policy.json' and row.get('schema_version') == 'sim-scenario-policy-1.0.0':
            expected += ' base_policy_sha256 read_denials'
        fields(row, expected)
    if filename == 'materials.jsonl':
        insist(row['kind'] in FACTS, 'material_kind')
        fields(row['facts'], FACTS[row['kind']])
        atom_strings(row, ('facts',))
        atom_strings(row['facts'], ('segments', 'test_scope'))
        if row['kind'] == 'storage_log':
            insist(type(row['facts']['segments']) is list, 'segment_type')
            for segment in row['facts']['segments']:
                fields(segment, 'start_ms end_ms mode')
                atom_strings(segment)
        if row['kind'] == 'inspection_report':
            insist(type(row['facts']['test_scope']) is list
                   and all(type(v) is str for v in row['facts']['test_scope']), 'test_scope_type')
    elif filename == 'events.jsonl':
        atom_strings(row, ('predecessor_event_ids',))
        insist(type(row['predecessor_event_ids']) is list
               and all(type(v) is str for v in row['predecessor_event_ids']), 'predecessor_type')
    elif filename == 'registrations.jsonl':
        atom_strings(row, ('event_id',))
        insist(row['event_id'] is None if row['target_kind'] == 'batch' else type(row['event_id']) is str, 'event_id_type')
    elif filename == 'batches.jsonl':
        atom_strings(row)
    elif filename == 'change-actions.jsonl':
        atom_strings(row)
    elif filename == 'policy.json':
        atom_strings(row, ('issuers', 'read_scope', 'read_denials'))
        insist(type(row['issuers']) is list, 'issuer_list')
        for issuer in row['issuers']:
            fields(issuer, 'issuer_id event_stages material_kinds may_create_batch')
            insist(type(issuer['issuer_id']) is str and type(issuer['may_create_batch']) is bool
                and type(issuer['event_stages']) is list and type(issuer['material_kinds']) is list
                and all(type(v) is str for v in issuer['event_stages'] + issuer['material_kinds']), 'issuer_types')
        fields(row['read_scope'], 'target_kinds material_kinds scope')
    elif filename == 'snapshot.json':
        atom_strings(row, ('components', 'request_profiles'))
    elif filename == 'requests.jsonl':
        fields(row, 'schema_version profile_id source design_text necessary_clauses preference_policy')
        atom_strings(row, ('necessary_clauses',))
        insist(type(row['necessary_clauses']) is list and bool(row['necessary_clauses']), 'clause_list')
        for clause in row['necessary_clauses']:
            fields(clause, 'clause_id source predicate parameters object_scope time_scope evidence_profile_id')
            atom_strings(clause, ('parameters', 'object_scope', 'time_scope'))
            fields(clause['object_scope'], 'candidate event_selection sample_binding')
            if clause['predicate'] == 'inspection_report_conclusion':
                fields(clause['parameters'], 'required_conclusion required_test_scope')
                fields(clause['time_scope'], 'mode ttl_ms')
                insist(clause['time_scope'] == {'mode': 'sampling_event', 'ttl_ms': None}, 'historical_request')
            elif clause['predicate'] == 'retail_status':
                fields(clause['parameters'], 'required_status')
                fields(clause['time_scope'], 'mode verify_at_ms interval_rule')
            else:
                insist(False, 'unsupported_predicate')


def location(value):
    path = PROJECT / value
    insist('..' not in path.parts and path.is_relative_to(PROJECT), 'invalid_path')
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            insist(not part.is_symlink() and not part.is_junction()
                   and not (getattr(part.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT), 'invalid_path')
        if part == PROJECT:
            break
    path = path.resolve()
    insist(path.is_relative_to(PROJECT), 'invalid_path')
    return path


def read_bound(root, spec):
    fields(spec, 'path bytes records sha256')
    integer(spec['bytes'])
    integer(spec['records'])
    raw = location(root / spec['path']).read_bytes()
    insist(len(raw) == spec['bytes'] and sha(raw) == spec['sha256'], 'component_digest')
    insist(not raw or (raw.endswith(b'\n') and b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf')), 'byte_contract')
    lines = raw.splitlines()
    insist(len(lines) == spec['records'], 'component_count')
    values = [decode(line) for line in lines]
    insist(all(canonical(row) == line for row, line in zip(values, lines)), 'byte_contract')
    for row in values:
        validate_row(Path(spec['path']).name, row)
    return values, lines


def public_package(record_path):
    insist(record_path.parent.name == 'sim-scenarios' and record_path.parent.parent.name == 'records', 'record_layout')
    root = record_path.parents[2]
    record = decode(record_path.read_bytes())
    primitives(record)
    fields(record, 'schema_version stage status catalog_version scenario_version protocol_version profile inputs producer_sha256 reuse_fingerprint_sha256 components audit_private counts code_state runtime independent_acceptance formal_package_status model_execution_status ledger_deployment_status sample_sufficiency')
    atom_strings(record, ('inputs', 'producer_sha256', 'components', 'audit_private', 'counts', 'code_state', 'runtime'))
    insist(type(record['components']) is dict and type(record['audit_private']) is dict, 'component_map')
    insist(record['stage'] == 'evidence_scenarios' and record['status'] == 'evidence_scenarios_prepared', 'record_status')
    insist(record['schema_version'] == 'sim-scenario-record-1.0.0' and record['scenario_version'] == 'sim-scenarios-1.0.0'
        and record['protocol_version'] == 'sim-evidence-protocol-1.0.0' and record['profile'] == 'paired_evidence_views_v1', 'record_version')
    fields(record['counts'], 'business_parents business_batches views request_profiles batch_rows event_rows material_rows registration_rows change_action_rows')
    fields(record['code_state'], 'git_head_sha worktree_dirty')
    atom_strings(record['code_state'], ('worktree_dirty',))
    insist(re.fullmatch('[0-9a-f]{40}', record['code_state']['git_head_sha']) is not None, 'git_head_format')
    fields(record['runtime'], 'python_version conda_prefix generated_at_utc')
    atom_strings(record['runtime'])
    fields(record['producer_sha256'], 'prepare_data.py sim_scenarios.py sim_normal.py')
    insist(all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in record['producer_sha256'].values()), 'producer_digest')
    core = {key: record[key] for key in ('stage', 'catalog_version', 'scenario_version', 'protocol_version',
                                        'profile', 'inputs', 'producer_sha256')}
    insist(sha(canonical(core)) == record['reuse_fingerprint_sha256'], 'record_fingerprint')
    fields(record['inputs'], 'scenario_config normal_record normal_acceptance normal_config protocol_draft protocol_record approval_draft authorization')
    for info in record['inputs'].values():
        fields(info, 'path bytes sha256')
        integer(info['bytes'])
        raw = location(info['path']).read_bytes()
        insist(len(raw) == info['bytes'] and sha(raw) == info['sha256'], 'input_binding')
    base_path = location(record['inputs']['normal_record']['path'])
    base_record = decode(base_path.read_bytes())
    acceptance = decode(location(record['inputs']['normal_acceptance']['path']).read_bytes())
    primitives(base_record)
    primitives(acceptance)
    insist(acceptance['status'] == 'accepted_ticket10_normal_sim_component_only'
        and acceptance['generation_record'] == {k: record['inputs']['normal_record'][k] for k in ('path', 'sha256')}, 'baseline_acceptance')
    base_policy_spec = base_record['components']['policy.json']
    base_policy_raw = location(base_path.parents[2] / base_policy_spec['path']).read_bytes()
    insist(sha(base_policy_raw) == base_policy_spec['sha256'], 'base_policy_binding')
    base_policy = decode(base_policy_raw)
    base = {name: read_bound(base_path.parents[2], base_record['components'][name])[0]
            for name in ('batches.jsonl', 'events.jsonl', 'materials.jsonl')}
    request_bindings = {}
    for batch in base['batches.jsonl']:
        scope = batch['parent_asin'], batch['sim_batch_id']
        binding = {}
        for stage in ('inspection', 'retail'):
            events = [r for r in base['events.jsonl'] if (r['parent_asin'], r['sim_batch_id']) == scope and r['stage'] == stage]
            insist(len(events) == 1, 'baseline_request_scope')
            binding[stage] = events[0]['event_id']
        samples = [r['facts']['sample_id'] for r in base['materials.jsonl'] if r['kind'] == 'inspection_sample'
            and (r['parent_asin'], r['sim_batch_id']) == scope and r['event_id'] == binding['inspection']]
        insist(len(set(samples)) == 1, 'baseline_request_scope')
        binding['sample_id'] = samples[0]
        request_bindings[scope] = binding
    relative = Path('data/sim-scenarios') / record['catalog_version'] / record['scenario_version']
    parsed, originals = {}, {}
    for name, spec in record['components'].items():
        insist(spec['path'] == (relative / name).as_posix(), 'component_path')
        parsed[name], originals[name] = read_bound(root, spec)
    manifest = parsed['manifest.json'][0]
    fields(manifest, 'schema_version source catalog_version scenario_version base_snapshot_id counts components')
    atom_strings(manifest, ('counts', 'components'))
    insist(type(manifest['components']) is dict, 'manifest_component_map')
    insist(manifest['schema_version'] == 'sim-scenario-manifest-1.0.0' and manifest['source'] == 'SIM'
        and manifest['counts'] == record['counts'] and manifest['catalog_version'] == record['catalog_version']
        and manifest['scenario_version'] == record['scenario_version']
        and manifest['base_snapshot_id'] == base_record['snapshot_id'], 'manifest_identity')
    insist(set(manifest['components']) == set(record['components']) - {'manifest.json'}, 'manifest_components')
    for name, spec in manifest['components'].items():
        insist(spec == {k: record['components'][name][k] for k in ('bytes', 'records', 'sha256')}, 'manifest_binding')
    index = parsed['view-index.jsonl']
    insist(len(index) == 16 and len({row['view_id'] for row in index}) == 16, 'view_count')
    expected = {'manifest.json', 'view-index.jsonl', 'requests.jsonl'}
    profile_ids = [request['profile_id'] for request in parsed['requests.jsonl']]
    insist(profile_ids == ['R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE'], 'request_profiles')
    for request, clause_ids in zip(parsed['requests.jsonl'], [['c1'], ['c1', 'c2']]):
        insist(request['source'] == 'experiment_design' and request['preference_policy'] == 'inherit_root_history'
            and [c['clause_id'] for c in request['necessary_clauses']] == clause_ids, 'request_contract')
        for clause in request['necessary_clauses']:
            insist(clause['source'] == 'experiment_design' and clause['object_scope']['candidate'] == 'current', 'clause_source')
            if clause['clause_id'] == 'c1':
                insist(clause['predicate'] == 'inspection_report_conclusion'
                    and clause['parameters'] == {'required_conclusion': 'pass', 'required_test_scope': ['SIM-Q1']}
                    and clause['object_scope'] == {'candidate': 'current', 'event_selection': 'baseline_inspection_event',
                                                   'sample_binding': 'event_sample_id'}
                    and clause['evidence_profile_id'] == 'inspection_sample_report_v1', 'inspection_request')
            else:
                insist(clause['predicate'] == 'retail_status' and clause['parameters'] == {'required_status': 'on_sale'}
                    and clause['object_scope'] == {'candidate': 'current', 'event_selection': 'baseline_retail_event', 'sample_binding': None}
                    and clause['evidence_profile_id'] == 'retail_current_status_v1'
                    and clause['time_scope']['mode'] == 'current_assertion'
                    and clause['time_scope']['interval_rule'] == 'from_inclusive_to_exclusive', 'retail_request')
    views = []
    for view in index:
        fields(view, 'view_id snapshot_path snapshot_sha256 base_snapshot_id')
        atom_strings(view)
        insist(re.fullmatch('q_[0-9a-f]{64}', view['view_id']) is not None
               and view['base_snapshot_id'] == base_record['snapshot_id'], 'view_identity')
        prefix = 'views/' + view['view_id'] + '/'
        insist(view['snapshot_path'] == prefix + 'snapshot.json', 'snapshot_path')
        expected.update(prefix + name for name in FILES)
        snapshot = parsed[prefix + 'snapshot.json'][0]
        insist(type(snapshot['components']) is dict, 'snapshot_component_map')
        insist(snapshot['schema_version'] == 'sim-scenario-snapshot-1.0.0' and snapshot['source'] == 'SIM'
            and snapshot['catalog_version'] == record['catalog_version']
            and snapshot['scenario_version'] == record['scenario_version']
            and snapshot['base_snapshot_id'] == base_record['snapshot_id']
            and snapshot['base_sim_version'] == base_record['sim_version']
            and snapshot['protocol_version'] == record['protocol_version'], 'snapshot_identity')
        insist(type(snapshot['request_profiles']) is list and snapshot['request_profiles'] == profile_ids
            and snapshot['requests_sha256'] == record['components']['requests.jsonl']['sha256'], 'snapshot_request_binding')
        insist(set(snapshot['components']) == set(FILES) - {'snapshot.json'}, 'snapshot_components')
        for request in parsed['requests.jsonl']:
            for clause in request['necessary_clauses']:
                if clause['clause_id'] == 'c2':
                    insist(clause['time_scope']['verify_at_ms'] == snapshot['verify_at_ms'], 'request_time_binding')
        policy = parsed[prefix + 'policy.json'][0]
        insist(policy['policy_id'] == snapshot['policy_id'], 'policy_id')
        if canonical(policy) != canonical(base_policy):
            fields(policy, 'schema_version source policy_id catalog_version sim_version identity_mode creation_source issuers registrar_id read_principal_id read_scope status_change_authority base_policy_sha256 read_denials')
            insist(policy['schema_version'] == 'sim-scenario-policy-1.0.0'
                and policy['base_policy_sha256'] == base_policy_spec['sha256'], 'policy_base')
            comparable = {k: policy[k] for k in base_policy}
            comparable.update(schema_version=base_policy['schema_version'], policy_id=base_policy['policy_id'])
            insist(canonical(comparable) == canonical(base_policy), 'policy_escalation')
            insist(policy['policy_id'] == 'p_' + sha(canonical({k: v for k, v in policy.items() if k != 'policy_id'})), 'policy_id')
            for denial in policy['read_denials']:
                fields(denial, 'principal_id target_kind target_id version')
                atom_strings(denial)
                integer(denial['version'], positive=True)
                insist(denial['principal_id'] == base_policy['read_principal_id'] and denial['target_kind'] == 'material', 'denial_scope')
        insist(sha(originals[prefix + 'snapshot.json'][0] + b'\n') == view['snapshot_sha256'], 'snapshot_binding')
        integer(snapshot['verify_at_ms'])
        integer(snapshot['sealed_at_ms'])
        integer(snapshot['cutoff_sequence'])
        insist(snapshot['sealed_at_ms'] <= snapshot['verify_at_ms'], 'snapshot_time')
        receipts = parsed[prefix + 'registrations.jsonl']
        insist([r['sequence'] for r in receipts] == list(range(1, len(receipts) + 1))
            and snapshot['cutoff_sequence'] <= len(receipts), 'registry_sequences')
        insist(all(r['registered_at_ms'] <= snapshot['sealed_at_ms'] for r in receipts
                   if r['sequence'] <= snapshot['cutoff_sequence']), 'registry_cutoff_time')
        snapshot_core = {key: value for key, value in snapshot.items() if key != 'snapshot_id'}
        insist(snapshot['snapshot_id'] == 'n_' + sha(b'Thesis-SIM-1:scenario_snapshot\0' + canonical(snapshot_core)), 'snapshot_id')
        for name, spec in snapshot['components'].items():
            insist(spec == manifest['components'][prefix + name], 'snapshot_component')
        views.append((view, snapshot, {name: parsed[prefix + name] for name in FILES},
                      {name: originals[prefix + name] for name in FILES}))
    insist(set(parsed) == expected, 'component_set')
    counts = {'business_parents': base_record['counts']['parents'], 'business_batches': base_record['counts']['batches'],
              'views': len(views), 'request_profiles': len(profile_ids), 'batch_rows': 0, 'event_rows': 0,
              'material_rows': 0, 'registration_rows': 0, 'change_action_rows': 0}
    for _, _, data, _ in views:
        insist(len(data['batches.jsonl']) == counts['business_batches'], 'batch_count')
        for field, filename in [('batch_rows', 'batches.jsonl'), ('event_rows', 'events.jsonl'),
                ('material_rows', 'materials.jsonl'), ('registration_rows', 'registrations.jsonl'),
                ('change_action_rows', 'change-actions.jsonl')]:
            counts[field] += len(data[filename])
    insist(counts == record['counts'], 'actual_counts')
    return record, parsed['requests.jsonl'], views, record['components']['manifest.json']['sha256'], request_bindings


def state(support, refutation, complete):
    if support and refutation:
        return 'Conflict'
    if refutation:
        return 'Refuted'
    return 'Supported' if support and complete else 'Pending'


class EvidenceView:
    def __init__(self, snapshot, data, originals, prefix, request_bindings):
        self.snapshot, self.data, self.prefix = snapshot, data, prefix
        self.request_bindings = request_bindings
        self.objects, self.receipts, self.scopes, self.cache = {}, defaultdict(list), defaultdict(set), {}
        self.head_cache, self.actions_by_target = {}, defaultdict(list)
        self.events = defaultdict(list)
        self.rights = {row['issuer_id']: row for row in data['policy.json'][0]['issuers']}
        self.denied = {(r['target_kind'], r['target_id'], r['version'])
                       for r in data['policy.json'][0].get('read_denials', [])}
        for row in data['events.jsonl']:
            self.events[row['parent_asin'], row['sim_batch_id'], row['stage']].append(row)
        for filename, kind, id_key in [('batches.jsonl', 'batch', 'sim_batch_id'),
                ('events.jsonl', 'event', 'event_id'), ('materials.jsonl', 'material', 'evidence_id'),
                ('change-actions.jsonl', 'change_action', 'action_id')]:
            for number, row in enumerate(data[filename], 1):
                version = row.get('version', 1)
                key = kind, row[id_key], version
                insist(key not in self.objects, 'duplicate_original')
                self.objects[key] = (row, {'path': prefix + filename, 'line': number,
                    'sha256': sha(originals[filename][number - 1]), 'id': row[id_key],
                    'version': version, 'json_pointer': '/facts' if kind == 'material' else '/'})
        for number, row in enumerate(data['registrations.jsonl'], 1):
            if row['sequence'] > snapshot['cutoff_sequence'] or row['registered_at_ms'] > snapshot['sealed_at_ms']:
                continue
            key = row['target_kind'], row['target_id'], row['version']
            self.receipts[key].append((row, {'path': prefix + 'registrations.jsonl', 'line': number,
                'sha256': sha(originals['registrations.jsonl'][number - 1]), 'id': row['registration_id'],
                'version': row['version'], 'json_pointer': '/content_sha256'}))
            if row['receipt_status'] == 'accepted' and row['source'] == 'SIM' and row['registry_backend'] == 'local_sim_registry' \
                    and row['registrar_id'] == data['policy.json'][0]['registrar_id']:
                self.scopes[row['parent_asin'], row['sim_batch_id'], row['event_id']].add(key)
        for action in data['change-actions.jsonl']:
            self.actions_by_target[action['target_id']].append(action)

    def original(self, key):
        if key in self.cache:
            return self.cache[key]
        pair = self.objects.get(key)
        records = self.receipts.get(key, [])
        observation = {'id': key[1], 'version': key[2], 'registrations': [loc for _, loc in records]}
        observation['checks'] = dict.fromkeys(('source_authorized', 'digest_match', 'object_bound', 'time_applicable'))
        reason = None
        if key in self.denied:
            reason = 'access_denied'
        elif pair is None:
            reason = 'unavailable'
        elif not records:
            reason = 'unregistered'
        else:
            row, locator = pair
            observation['original'] = locator
            owner = row.get('issuer_id', row.get('actor_id'))
            valid = [(r, loc) for r, loc in records if r['receipt_status'] == 'accepted'
                and r['source'] == 'SIM' and r['registry_backend'] == 'local_sim_registry'
                and r['registrar_id'] == self.data['policy.json'][0]['registrar_id']
                and r['issuer_id'] == owner and r['parent_asin'] == row['parent_asin']
                and r['sim_batch_id'] == row['sim_batch_id'] and r['event_id'] == row.get('event_id')]
            if not valid:
                reason = 'registration_binding'
            elif len({r['content_sha256'] for r, _ in valid}) != 1:
                reason = 'ambiguous_registration'
            elif valid[0][0]['content_sha256'] != locator['sha256']:
                reason = 'digest_mismatch'
            if reason is None:
                observation['registrations'] = [loc for _, loc in valid]
                rights = self.rights.get(owner, {})
                authorized = row['source'] == 'SIM' and (rights.get('may_create_batch', False) if key[0] == 'batch'
                    else row['stage'] in rights.get('event_stages', []) if key[0] == 'event'
                    else row['kind'] in rights.get('material_kinds', []) if key[0] == 'material' else bool(rights))
                observation['checks']['source_authorized'] = authorized
                observation['checks']['digest_match'] = True
                observation['checks']['object_bound'] = True
                if not authorized:
                    reason = 'issuer_not_authorized'
                elif not self.valid_time(key[0], row, valid):
                    reason = 'time_not_applicable'
                elif key[0] == 'material' and (
                        row['kind'] == 'inspection_report' and row['facts']['conclusion'] not in ('pass', 'fail')
                        or row['kind'] == 'retail_status' and row['facts']['status'] not in ('on_sale', 'off_sale')):
                    reason = 'unknown_assertion'
                observation['checks']['time_applicable'] = reason != 'time_not_applicable'
        observation['reason'] = reason
        value = (pair[0] if pair and reason is None else None, observation)
        self.cache[key] = value
        return value

    def valid_time(self, kind, row, receipts):
        issued = row.get('issued_at_ms', row.get('created_at_ms', row.get('event_end_ms')))
        if not all(issued <= r['registered_at_ms'] <= self.snapshot['sealed_at_ms'] <= self.snapshot['verify_at_ms']
                   for r, _ in receipts):
            return False
        if kind == 'event':
            return row['event_start_ms'] <= row['event_end_ms']
        if kind != 'material':
            return True
        expected_stage = {'inspection_sample': 'inspection', 'inspection_report': 'inspection', 'retail_status': 'retail'}.get(row['kind'])
        event = self.objects.get(('event', row['event_id'], 1))
        if event is None:
            return False
        event = event[0]
        if (event['parent_asin'], event['sim_batch_id']) != (row['parent_asin'], row['sim_batch_id']):
            return False
        if expected_stage and event['stage'] != expected_stage:
            return False
        facts = row['facts']
        if row['kind'] in ('inspection_sample', 'inspection_report') and row['temporal_mode'] != 'historical_fact':
            return False
        if row['kind'] == 'inspection_sample':
            return event['event_start_ms'] <= facts['sampled_at_ms'] <= event['event_end_ms'] and facts['sampled_at_ms'] <= issued
        if row['kind'] == 'inspection_report':
            return (event['event_start_ms'] <= facts['test_started_at_ms'] <= facts['test_completed_at_ms']
                    <= event['event_end_ms'] and facts['test_completed_at_ms'] <= issued)
        if row['kind'] == 'retail_status':
            return (row['temporal_mode'] == 'current_assertion'
                and event['event_start_ms'] <= facts['observed_at_ms'] <= event['event_end_ms']
                and facts['observed_at_ms'] <= issued
                and row['valid_from_ms'] <= self.snapshot['verify_at_ms'] < row['valid_to_ms'])
        return True

    def lineage(self, identity):
        if identity in self.head_cache:
            return self.head_cache[identity]
        records = {key[2]: entries for key, entries in self.receipts.items() if key[:2] == ('material', identity)}
        trace = {'evidence_id': identity, 'head_version': 1, 'revoked_versions': [], 'actions': [], 'reason': None}
        visible = [r for entries in records.values() for r, _ in entries
                   if r['receipt_status'] == 'accepted' and r['source'] == 'SIM'
                   and r['registry_backend'] == 'local_sim_registry'
                   and r['registrar_id'] == self.data['policy.json'][0]['registrar_id']]
        anchors = [r for r in visible if r['version'] == 1]
        identity_fields = ('issuer_id', 'parent_asin', 'sim_batch_id', 'event_id')
        bound_identity = None
        for version in sorted(records):
            key = 'material', identity, version
            pair = self.objects.get(key)
            if key not in self.denied and pair and any(r['version'] == version and r['content_sha256'] == pair[1]['sha256']
                                                      for r in visible):
                bound_identity = tuple(pair[0][field] for field in identity_fields)
                break
        if bound_identity is None:
            registered_identities = {tuple(r[field] for field in identity_fields) for r in anchors}
            if len(registered_identities) == 1:
                bound_identity = next(iter(registered_identities))
        anchors = [r for r in anchors if tuple(r[field] for field in identity_fields) == bound_identity]
        edges, revoked = defaultdict(set), set()
        for action in self.actions_by_target[identity]:
            accepted, observation = self.original(('change_action', action['action_id'], 1))
            if accepted is not None:
                own = [r for r in anchors if r['issuer_id'] == action['issuer_id']
                    and all(r[field] == action[field] for field in ('parent_asin', 'sim_batch_id', 'event_id'))]
                target_records = [r for r in visible if r['version'] == action['target_version']
                    and tuple(r[field] for field in identity_fields) == bound_identity and r['issuer_id'] == action['issuer_id']
                    and all(r[field] == action[field] for field in ('parent_asin', 'sim_batch_id', 'event_id'))]
                if action['target_kind'] != 'material':
                    observation = {**observation, 'reason': 'action_target_kind'}
                elif not own or not target_records or self.data['policy.json'][0]['status_change_authority'] != 'issuer_own_lineage_only':
                    observation = {**observation, 'reason': 'action_not_authorized'}
                elif action['effective_from_ms'] > self.snapshot['verify_at_ms']:
                    observation = {**observation, 'reason': 'action_not_effective'}
                elif action['action_type'] == 'supersedes':
                    previous = action['supersedes_version']
                    if previous is None or previous >= action['target_version'] or previous not in records:
                        observation = {**observation, 'reason': 'invalid_revision_chain'}
                    else:
                        known = []
                        for version in (previous, action['target_version']):
                            key = 'material', identity, version
                            _, material_observation = self.original(key)
                            if material_observation['checks']['digest_match'] is True:
                                known.append(self.objects[key][0])
                        same_scope = True
                        if len(known) == 2:
                            old, new = known
                            same_scope = all(old[field] == new[field] for field in
                                ('parent_asin', 'sim_batch_id', 'event_id', 'kind', 'issuer_id', 'temporal_mode'))
                            if same_scope and old['kind'] in ('inspection_sample', 'inspection_report'):
                                same_scope = old['facts']['sample_id'] == new['facts']['sample_id']
                            if same_scope and old['kind'] == 'inspection_report':
                                same_scope = set(old['facts']['test_scope']) == set(new['facts']['test_scope'])
                        if not same_scope:
                            observation = {**observation, 'reason': 'revision_scope_mismatch'}
                        else:
                            edges[previous].add(action['target_version'])
                elif action['action_type'] == 'revokes' and action['supersedes_version'] is None:
                    revoked.add(action['target_version'])
                else:
                    observation = {**observation, 'reason': 'invalid_action'}
            trace['actions'].append(observation)
        if not anchors:
            trace.update(head_version=None, reason='missing_lineage_root')
        else:
            head, visited = 1, set()
            while head in edges:
                if head in visited or len(edges[head]) != 1:
                    trace.update(head_version=None, reason='ambiguous_revision_chain')
                    break
                visited.add(head)
                head = next(iter(edges[head]))
            else:
                trace['head_version'] = head
        trace['revoked_versions'] = sorted(revoked)
        self.head_cache[identity] = trace
        return trace

    def claim(self, clause, batch):
        is_inspection = clause['predicate'] == 'inspection_report_conclusion'
        stage = 'inspection' if is_inspection else 'retail'
        binding = self.request_bindings[batch['parent_asin'], batch['sim_batch_id']]
        events = [r for r in self.events[batch['parent_asin'], batch['sim_batch_id'], stage]
                  if r['event_id'] == binding[stage]]
        relevant = self.scopes[batch['parent_asin'], batch['sim_batch_id'], events[0]['event_id']] if len(events) == 1 else set()
        accepted, rejected, combinations, heads = [], [], [], {}
        usable, reads_complete, versions_complete = [], True, True
        gate = len(events) == 1
        proof_keys = [('batch', batch['sim_batch_id'], batch['version'])]
        if events:
            proof_keys.append(('event', events[0]['event_id'], events[0]['version']))
        for key in proof_keys:
            row, observation = self.original(key)
            if row is None:
                gate = False
                rejected.append(observation)
                reads_complete &= observation['reason'] not in ('unavailable', 'access_denied')
            else:
                accepted.append(observation)
        for key in sorted(relevant):
            if key[0] == 'change_action':
                if any(r['receipt_status'] == 'accepted' and r['source'] == 'SIM'
                       and r['registry_backend'] == 'local_sim_registry'
                       and r['registrar_id'] == self.data['policy.json'][0]['registrar_id']
                       for r, _ in self.receipts[key]):
                    _, observation = self.original(key)
                    if observation['reason'] in ('unavailable', 'access_denied'):
                        rejected.append(observation)
                        reads_complete = versions_complete = False
                continue
            if key[0] != 'material':
                continue
            head = self.lineage(key[1])
            heads[key[1]] = head
            if head['reason'] is not None:
                versions_complete = False
                rejected.append({'id': key[1], 'version': key[2], 'reason': head['reason']})
                continue
            if key[2] != head['head_version'] or key[2] in head['revoked_versions']:
                rejected.append({'id': key[1], 'version': key[2],
                                 'reason': 'revoked' if key[2] in head['revoked_versions']
                                    else 'superseded' if key[2] < head['head_version'] else 'not_current_version'})
                continue
            row, observation = self.original(key)
            if row is None:
                rejected.append(observation)
                reads_complete &= observation['reason'] not in ('unavailable', 'access_denied')
            elif row['kind'] in (('inspection_sample', 'inspection_report') if is_inspection else ('retail_status',)):
                if (row['parent_asin'], row['sim_batch_id'], row['event_id']) != (
                        batch['parent_asin'], batch['sim_batch_id'], binding[stage]):
                    rejected.append({**observation, 'reason': 'outside_request_object'})
                    continue
                if is_inspection and row['facts']['sample_id'] != binding['sample_id']:
                    rejected.append({**observation, 'reason': 'outside_request_sample'})
                    continue
                usable.append((row, observation))
                accepted.append(observation)
        support, refutation = False, False
        if is_inspection:
            samples = [(r, loc) for r, loc in usable if r['kind'] == 'inspection_sample']
            for report, report_loc in ((r, loc) for r, loc in usable if r['kind'] == 'inspection_report'):
                for sample, sample_loc in samples:
                    if report['facts']['sample_id'] != sample['facts']['sample_id'] or report['event_id'] != sample['event_id']:
                        continue
                    if not sample['facts']['sampled_at_ms'] <= report['facts']['test_started_at_ms']:
                        continue
                    if not set(clause['parameters']['required_test_scope']) <= set(report['facts']['test_scope']):
                        continue
                    positive = report['facts']['conclusion'] == clause['parameters']['required_conclusion']
                    negative = report['facts']['conclusion'] == 'fail'
                    support |= positive
                    refutation |= negative
                    if positive or negative:
                        combinations.append({'polarity': 'support' if positive else 'refute',
                                             'members': [sample_loc, report_loc]})
        else:
            for retail, locator in usable:
                if retail['valid_from_ms'] <= self.snapshot['verify_at_ms'] < retail['valid_to_ms']:
                    positive = retail['facts']['status'] == clause['parameters']['required_status']
                    negative = retail['facts']['status'] == 'off_sale'
                    support |= positive
                    refutation |= negative
                    if positive or negative:
                        combinations.append({'polarity': 'support' if positive else 'refute', 'members': [locator]})
        support, refutation = support and gate, refutation and gate
        return {'clause_id': clause['clause_id'], 's': int(support), 'r': int(refutation),
                'enumeration_complete': True, 'required_reads_complete': reads_complete, 'version_checks_complete': versions_complete,
                'state': state(support, refutation, reads_complete and versions_complete), 'adopted': accepted, 'rejected': rejected,
                'combinations': combinations, 'version_heads': [heads[key] for key in sorted(heads)]}


def calculate(requests, views, manifest_sha, request_bindings):
    result = []
    for view, snapshot, data, originals in views:
        context = EvidenceView(snapshot, data, originals, 'views/' + view['view_id'] + '/', request_bindings)
        for request in requests:
            for batch in data['batches.jsonl']:
                clauses = [context.claim(c, batch) for c in request['necessary_clauses']]
                states = {c['state'] for c in clauses}
                candidate = ('Conflict' if 'Conflict' in states else 'Refuted' if 'Refuted' in states
                             else 'Supported' if states == {'Supported'} else 'Pending')
                result.append({'schema_version': 'sim-scenario-reference-1.0.0', 'view_id': view['view_id'],
                    'snapshot_id': snapshot['snapshot_id'], 'request_profile_id': request['profile_id'],
                    'parent_asin': batch['parent_asin'], 'sim_batch_id': batch['sim_batch_id'], 'clauses': clauses,
                    'candidate_state': candidate, 'eligible': candidate == 'Supported',
                    'reference_rule_version': 'scenario-reference-1.0.0', 'public_fact_manifest_sha256': manifest_sha})
    return sorted(result, key=lambda row: (row['view_id'], row['request_profile_id'], row['parent_asin'].encode()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True)
    parser.add_argument('--audit-root', required=True)
    args = parser.parse_args()
    audit_root = None
    try:
        record_path = location(args.record)
        header = decode(record_path.read_bytes())
        generation_root = record_path.parents[2]
        base_root = location(header['inputs']['normal_record']['path']).parents[2]
        target = location(args.audit_root)
        for root in {PROJECT, generation_root, base_root}:
            for subtree in ('research', 'manuscript', 'data/sim', 'data/sim-scenarios', 'records'):
                insist(not target.is_relative_to(root / subtree), 'invalid_audit_root')
            insist(not target.is_relative_to(root / 'data/sim-reference' / header['catalog_version'] / 'sim-normal-1.0.0'),
                   'invalid_audit_root')
        insist(not target.exists(), 'audit_root_exists')
        target.mkdir(parents=True)
        audit_root = target
        record, requests, views, manifest_sha, request_bindings = public_package(record_path)
        reference = calculate(requests, views, manifest_sha, request_bindings)
        raw = b''.join(canonical(row) + b'\n' for row in reference)
        (audit_root / 'reference.jsonl').write_bytes(raw)
        rejections = Counter()
        for row in reference:
            for clause in row['clauses']:
                observations = clause['rejected'] + [action for head in clause['version_heads'] for action in head['actions']]
                rejections.update(item['reason'] for item in observations if item.get('reason') is not None)
        report = {'status': 'scenario_reference_complete', 'errors': [], 'reference_rows': len(reference),
            'outer_integrity': {'status': 'passed', 'public_components': len(record['components']), 'views': len(views)},
            'rejection_count_unit': 'clause_trace_occurrence', 'rejection_reason_counts': dict(sorted(rejections.items())),
            'state_counts': dict(Counter(row['candidate_state'] for row in reference)),
            'reference_sha256': sha(raw), 'reference_rule_version': 'scenario-reference-1.0.0',
            'program_sha256': sha(Path(__file__).read_bytes()), 'public_fact_manifest_sha256': manifest_sha,
            'runtime': {'python_version': platform.python_version(), 'conda_prefix': sys.prefix,
                        'at_utc': datetime.now(timezone.utc).isoformat()}}
        (audit_root / 'check.json').write_bytes(canonical(report) + b'\n')
        print(canonical(report).decode())
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        code = str(exc) if type(exc) is ValueError and str(exc).replace('_', '').isalnum() else 'invalid_package'
        report = {'status': 'failed', 'errors': [code]}
        if audit_root is not None:
            (audit_root / 'check.json').write_bytes(canonical(report) + b'\n')
        print(canonical(report).decode())
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
