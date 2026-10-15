"""Fixed normal SIM profile behind the single data preparation CLI."""

import hashlib
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parent
STAGES = ('harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail')
KINDS = ('harvest_record', 'packaging_binding', 'storage_log', 'inspection_sample',
         'inspection_report', 'transport_dispatch', 'transport_receipt', 'retail_status')
MATERIAL_STAGES = ('harvest', 'packaging', 'storage', 'inspection', 'inspection', 'transport', 'transport', 'retail')
PROTOCOL = {
    'version': 'sim-evidence-protocol-1.0.0',
    'record_path': '.scratch/data-preparation/issues/09-evidence-protocol.md',
    'record_sha256': 'ef7f34e0868c879963287c4085418ed2748939f394ea61ea1751635b4da7abc6',
    'draft_path': '.scratch/data-preparation/ticket09-stage1-sim-evidence-request-review-draft-20261015.md',
    'draft_sha256': '6ae2dd42b943b65eda899560be8cffa68fac8570ad362439b2a100de76720461',
}
CONFIG_SHAPE = {
    **dict.fromkeys(('schema_version', 'version', 'profile', 'byte_contract', 'id_namespace'), str),
    'protocol_binding': dict.fromkeys(('version', 'record_path', 'record_sha256', 'draft_path', 'draft_sha256'), str),
    'catalog_binding': {**dict.fromkeys(('version', 'record_path', 'record_sha256', 'component_sha256'), str),
                        'expected_parent_count': int},
    'clock': dict.fromkeys(('batch_created_at_ms', 'batch_registered_at_ms', 'snapshot_sealed_at_ms',
                           'verify_at_ms', 'retail_valid_from_ms', 'retail_valid_to_ms', 'sampled_at_ms',
                           'test_started_at_ms', 'test_completed_at_ms'), int),
    'events': {stage: dict.fromkeys(('start_ms', 'end_ms', 'registered_at_ms'), int) for stage in STAGES},
    'materials': {kind: dict.fromkeys(('issued_at_ms', 'registered_at_ms'), int) for kind in KINDS},
    'issuers': [{'issuer_id': str, 'may_create_batch': bool, 'event_stages': [str], 'material_kinds': [str]}],
    'registry': dict.fromkeys(('registrar_id', 'backend', 'identity_mode', 'read_principal_id'), str),
    'facts': {**dict.fromkeys(('origin_area_id', 'warehouse_location_id', 'retail_location_id', 'quantity_unit',
                              'packaging_condition', 'storage_mode', 'report_conclusion', 'handover_status', 'retail_status'), str),
              'quantity_units': int, 'test_scope': [str]},
    'reference_request': {**dict.fromkeys(('profile_id', 'source', 'predicate', 'required_conclusion', 'time_scope'), str),
                          'required_test_scope': [str], 'required_kinds': [str]},
}


class SimError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='invalid_config'):
    if not condition:
        raise SimError(code)


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object,
                      parse_constant=lambda value: require(False))


def check_shape(value, shape):
    if isinstance(shape, dict):
        require(type(value) is dict and value.keys() == shape.keys())
        for key, child in shape.items():
            check_shape(value[key], child)
    elif isinstance(shape, list):
        require(type(value) is list)
        require(len({json_bytes(item) for item in value}) == len(value))
        for item in value:
            check_shape(item, shape[0])
    else:
        require(type(value) is shape)
        if shape is int:
            require(0 <= value <= 2**53 - 1)
        if shape is str:
            require(bool(value) and '\0' not in value)


def load_config(path):
    config = read_json(path)
    check_shape(config, CONFIG_SHAPE)
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', config['version']) is not None)
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', config['catalog_binding']['version']) is not None)
    require(config['profile'] == 'normal_six_stage_v1' and config['protocol_binding'] == PROTOCOL,
            'unapproved_protocol')
    for name in ('record', 'draft'):
        require(hashlib.sha256((PROJECT / PROTOCOL[name + '_path']).read_bytes()).hexdigest()
                == PROTOCOL[name + '_sha256'], 'unapproved_protocol')
    require(config['schema_version'] == 'sim-normal-config-1.0.0'
            and config['byte_contract'] == 'sim-jsonl-utf8-lf-1.0.0' and config['id_namespace'] == 'Thesis-SIM-1')
    expected_issuers = [
        {'issuer_id': 'SIM-' + name, 'may_create_batch': name == 'PRODUCER',
         'event_stages': [stage] if stage else [], 'material_kinds': [kind]}
        for name, stage, kind in zip(('PRODUCER', 'PACKER', 'WAREHOUSE', 'SAMPLER', 'LAB', 'CARRIER', 'RECEIVER', 'RETAIL'),
                                     ('harvest', 'packaging', 'storage', None, 'inspection', 'transport', None, 'retail'), KINDS)]
    require(config['issuers'] == expected_issuers)
    require(config['registry'] == {'registrar_id': 'SIM-REGISTRY', 'backend': 'local_sim_registry',
                                   'identity_mode': 'simulated_allowlist_no_crypto', 'read_principal_id': 'SIM-VERIFIER'})
    require(config['facts'] == {'origin_area_id': 'SIM-AREA-01', 'warehouse_location_id': 'SIM-WAREHOUSE-01',
            'retail_location_id': 'SIM-RETAIL-01', 'quantity_units': 100, 'quantity_unit': 'SIM_PACK',
            'packaging_condition': 'intact', 'storage_mode': 'SIM_DRY', 'test_scope': ['SIM-Q1'],
            'report_conclusion': 'pass', 'handover_status': 'accepted', 'retail_status': 'on_sale'})
    require(config['reference_request'] == {'profile_id': 'R1_SIM_Q1', 'source': 'experiment_design',
            'predicate': 'inspection_report_conclusion', 'required_test_scope': ['SIM-Q1'],
            'required_conclusion': 'pass', 'time_scope': 'sampling_event',
            'required_kinds': ['inspection_sample', 'inspection_report']})
    for binding, keys in ((config['catalog_binding'], ('record_sha256', 'component_sha256')),
                          (config['protocol_binding'], ('record_sha256', 'draft_sha256'))):
        for key in keys:
            require(re.fullmatch('[0-9a-f]{64}', binding[key]) is not None)
    validate_times(config)
    return config


def validate_times(config):
    clock, events, materials = config['clock'], config['events'], config['materials']
    seal, tau = clock['snapshot_sealed_at_ms'], clock['verify_at_ms']
    require(clock['batch_created_at_ms'] <= clock['batch_registered_at_ms'] <= seal <= tau)
    previous_end = clock['batch_created_at_ms']
    for stage in STAGES:
        event = events[stage]
        require(previous_end <= event['start_ms'] <= event['end_ms'] <= event['registered_at_ms'] <= seal)
        previous_end = event['end_ms']
    require(events['retail']['start_ms'] == events['retail']['end_ms'])
    require(events['inspection']['start_ms'] <= clock['sampled_at_ms'] <= clock['test_started_at_ms']
            <= clock['test_completed_at_ms'] <= events['inspection']['end_ms'])
    require(clock['retail_valid_from_ms'] <= events['retail']['start_ms']
            <= tau < clock['retail_valid_to_ms'])
    completed = (events['harvest']['end_ms'], events['packaging']['end_ms'], events['storage']['end_ms'],
                 clock['sampled_at_ms'], clock['test_completed_at_ms'], events['transport']['start_ms'],
                 events['transport']['end_ms'], events['retail']['start_ms'])
    for kind, stage, time in zip(KINDS, MATERIAL_STAGES, completed):
        material = materials[kind]
        require(time <= material['issued_at_ms'] <= material['registered_at_ms'] <= seal)
        require(events[stage]['registered_at_ms'] <= material['registered_at_ms'])


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_id(prefix, tag, *parts):
    return prefix + digest(('Thesis-SIM-1:' + tag + '\0' + '\0'.join(parts)).encode('utf-8'))


def input_binding(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'sha256': digest(raw), 'bytes': len(raw)}


def safe_path(value):
    path = PROJECT / value
    require('..' not in path.parts and path.is_relative_to(PROJECT), 'invalid_path')
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink() and not ancestor.is_junction(), 'invalid_path')
        if ancestor == PROJECT:
            break
    resolved = path.resolve()
    require(resolved.is_relative_to(PROJECT), 'invalid_path')
    return resolved


def load_catalog(path, binding):
    try:
        require(path == safe_path(binding['record_path']), 'invalid_catalog')
        require(digest(path.read_bytes()) == binding['record_sha256'], 'invalid_catalog')
        record = read_json(path)
        require(record['stage'] == 'catalog' and record['status'] == 'catalog_complete'
                and record['scope_version'] == binding['version'], 'invalid_catalog')
        catalog_path = safe_path(record['catalog_path'])
        raw = catalog_path.read_bytes()
        require(digest(raw) == record['catalog_sha256'] == binding['component_sha256'], 'invalid_catalog')
        parents = []
        seen = set()
        for line in raw.splitlines():
            row = json.loads(line, object_pairs_hook=unique_object)
            check_shape(row['parent_asin'], str)
            check_shape(row['crop'], str)
            require(row['status'] == 'included' and row['parent_asin'] not in seen, 'invalid_catalog')
            seen.add(row['parent_asin'])
            parents.append({'parent_asin': row['parent_asin'], 'crop': row['crop']})
        require(type(record['counts']['included']) is int
                and len(parents) == record['counts']['included'] == binding['expected_parent_count']
                and len(parents) > 0, 'invalid_catalog')
        return catalog_path, parents
    except (ValueError, KeyError, TypeError, OSError) as exc:
        if isinstance(exc, SimError) and exc.code == 'invalid_path':
            raise
        raise SimError('invalid_catalog') from None


def generate(config, parents):
    catalog_version = config['catalog_binding']['version']
    clock, times, facts = config['clock'], config['events'], config['facts']
    actors = {stage: issuer['issuer_id'] for issuer in config['issuers'] for stage in issuer['event_stages']}
    signers = {kind: issuer['issuer_id'] for issuer in config['issuers'] for kind in issuer['material_kinds']}
    creator = next(issuer['issuer_id'] for issuer in config['issuers'] if issuer['may_create_batch'])
    batches, events, materials, targets = [], [], [], []
    for parent in sorted(parents, key=lambda p: p['parent_asin'].encode('utf-8')):
        asin, crop = parent['parent_asin'], parent['crop']
        batch_id = object_id('b_', 'batch', catalog_version, asin)
        common = {'source': 'SIM', 'parent_asin': asin, 'sim_batch_id': batch_id, 'version': 1}
        batch = {**common, 'schema_version': 'sim-batch-1.0.0', 'crop': crop,
                 'catalog_version': catalog_version, 'sim_profile_id': config['profile'],
                 'protocol_version': config['protocol_binding']['version'], 'issuer_id': creator,
                 'created_at_ms': clock['batch_created_at_ms']}
        batches.append(batch)
        targets.append(('batch', batch, clock['batch_registered_at_ms']))
        event_ids = {stage: object_id('e_', 'event', batch_id, stage) for stage in STAGES}
        for index, stage in enumerate(STAGES):
            event = {**common, 'schema_version': 'sim-event-1.0.0', 'event_id': event_ids[stage],
                     'stage': stage, 'actor_id': actors[stage], 'event_start_ms': times[stage]['start_ms'],
                     'event_end_ms': times[stage]['end_ms'],
                     'predecessor_event_ids': [event_ids[STAGES[index - 1]]] if index else []}
            events.append(event)
            targets.append(('event', event, times[stage]['registered_at_ms']))
        sample_id = object_id('s_', 'sample', batch_id)
        route = {'transport_segment_id': object_id('t_', 'transport_segment', batch_id),
                 'from_location_id': facts['warehouse_location_id'], 'to_location_id': facts['retail_location_id'],
                 'quantity_units': facts['quantity_units'], 'unit': facts['quantity_unit']}
        material_facts = [
            {'crop': crop, 'origin_area_id': facts['origin_area_id'], 'harvested_at_ms': times['harvest']['end_ms']},
            {'harvest_event_id': event_ids['harvest'], 'packaged_at_ms': times['packaging']['end_ms'],
             'package_condition': facts['packaging_condition'], 'quantity_units': facts['quantity_units'], 'unit': facts['quantity_unit']},
            {'coverage_start_ms': times['storage']['start_ms'], 'coverage_end_ms': times['storage']['end_ms'],
             'segments': [{'start_ms': times['storage']['start_ms'], 'end_ms': times['storage']['end_ms'], 'mode': facts['storage_mode']}]},
            {'sample_id': sample_id, 'sampled_at_ms': clock['sampled_at_ms']},
            {'sample_id': sample_id, 'test_scope': facts['test_scope'], 'test_started_at_ms': clock['test_started_at_ms'],
             'test_completed_at_ms': clock['test_completed_at_ms'], 'conclusion': facts['report_conclusion']},
            {**route, 'departed_at_ms': times['transport']['start_ms']},
            {**route, 'arrived_at_ms': times['transport']['end_ms'], 'handover_status': facts['handover_status']},
            {'observed_at_ms': times['retail']['start_ms'], 'location_id': facts['retail_location_id'],
             'status': facts['retail_status'], 'stock_units': facts['quantity_units'], 'unit': facts['quantity_unit']},
        ]
        for kind, stage, values in zip(KINDS, MATERIAL_STAGES, material_facts):
            material = {**common, 'schema_version': 'sim-material-1.0.0', 'event_id': event_ids[stage],
                        'evidence_id': object_id('d_', 'evidence', batch_id, kind, signers[kind]),
                        'kind': kind, 'issuer_id': signers[kind], 'facts': values,
                        'issued_at_ms': config['materials'][kind]['issued_at_ms'],
                        'temporal_mode': 'current_assertion' if kind == 'retail_status' else 'historical_fact'}
            if kind == 'retail_status':
                material.update(valid_from_ms=clock['retail_valid_from_ms'], valid_to_ms=clock['retail_valid_to_ms'])
            materials.append(material)
            targets.append(('material', material, config['materials'][kind]['registered_at_ms']))
    registrations = []
    for kind, row, time in targets:
        target_id = row[{'batch': 'sim_batch_id', 'event': 'event_id', 'material': 'evidence_id'}[kind]]
        registrations.append({
            'schema_version': 'sim-registration-1.0.0', 'source': 'SIM', 'registry_backend': 'local_sim_registry',
            'registration_id': object_id('g_', 'registration', kind, target_id, '1'), 'target_kind': kind,
            'target_id': target_id, 'version': 1, 'parent_asin': row['parent_asin'], 'sim_batch_id': row['sim_batch_id'],
            'event_id': None if kind == 'batch' else row['event_id'],
            'issuer_id': row['actor_id'] if kind == 'event' else row['issuer_id'], 'content_sha256': digest(json_bytes(row)),
            'registrar_id': 'SIM-REGISTRY', 'receipt_status': 'accepted', 'registered_at_ms': time})
    registrations.sort(key=lambda row: (row['registered_at_ms'], ('batch', 'event', 'material').index(row['target_kind']),
                                        row['target_id'].encode('utf-8'), row['version']))
    for sequence, row in enumerate(registrations, 1):
        row['sequence'] = sequence
    policy = {'schema_version': 'sim-policy-1.0.0', 'source': 'SIM', 'policy_id': 'sim-normal-policy-1.0.0',
              'catalog_version': catalog_version, 'sim_version': config['version'],
              'identity_mode': config['registry']['identity_mode'], 'creation_source': 'project_constructed_simulation',
              'issuers': config['issuers'], 'registrar_id': config['registry']['registrar_id'],
              'read_principal_id': config['registry']['read_principal_id'],
              'read_scope': {'target_kinds': ['batch', 'event', 'material'], 'material_kinds': list(KINDS), 'scope': 'current_snapshot_only'},
              'status_change_authority': 'issuer_own_lineage_only'}
    rows = {'batches.jsonl': batches, 'events.jsonl': events, 'materials.jsonl': materials,
            'registrations.jsonl': registrations, 'policy.json': [policy]}
    files = {name: b''.join(json_bytes(row) + b'\n' for row in values) for name, values in rows.items()}
    components = {name: {'sha256': digest(raw), 'bytes': len(raw), 'records': len(rows[name])} for name, raw in files.items()}
    snapshot = {'schema_version': 'sim-snapshot-1.0.0', 'source': 'SIM', 'protocol_version': config['protocol_binding']['version'],
                'catalog_version': catalog_version, 'sim_version': config['version'], 'registry_backend': 'local_sim_registry',
                'cutoff_sequence': len(registrations), 'sealed_at_ms': clock['snapshot_sealed_at_ms'],
                'verify_at_ms': clock['verify_at_ms'], 'policy_id': policy['policy_id'],
                'reference_request': config['reference_request'], 'components': components}
    snapshot_id = 'n_' + digest(b'Thesis-SIM-1:snapshot\0' + json_bytes(snapshot))
    snapshot['snapshot_id'] = snapshot_id
    files['snapshot.json'] = json_bytes(snapshot) + b'\n'
    components['snapshot.json'] = {'sha256': digest(files['snapshot.json']), 'bytes': len(files['snapshot.json']), 'records': 1}
    return files, components, snapshot_id


def prepare_normal(catalog_record, config_path, output_root):
    try:
        config_path = safe_path(config_path)
        catalog_record = safe_path(catalog_record)
        output_root = safe_path(output_root)
        config = load_config(config_path)
        catalog_path, parents = load_catalog(catalog_record, config['catalog_binding'])
        files, components, snapshot_id = generate(config, parents)
        catalog_version, version = config['catalog_binding']['version'], config['version']
        relative_dir = Path('data/sim') / catalog_version / version
        destination = safe_path(output_root / relative_dir)
        record_path = safe_path(output_root / 'records/sim' / f'{catalog_version}-{version}.json')
        safe_path(PROJECT / '.tmp')
        for path in (config_path, catalog_record, catalog_path, PROJECT / PROTOCOL['record_path'], PROJECT / PROTOCOL['draft_path']):
            safe_path(path)
            require(not path.is_relative_to(destination) and path != record_path, 'invalid_path')
        inputs = {name: input_binding(path) for name, path in {
            'config': config_path, 'catalog_record': catalog_record, 'catalog': catalog_path,
            'protocol_record': PROJECT / PROTOCOL['record_path'], 'protocol_draft': PROJECT / PROTOCOL['draft_path']}.items()}
        producers = {name: digest((PROJECT / name).read_bytes()) for name in ('prepare_data.py', 'sim_normal.py')}
        core = {'stage': 'sim_normal', 'catalog_version': catalog_version, 'sim_version': version,
                'profile': config['profile'], 'protocol_version': PROTOCOL['version'], 'inputs': inputs, 'producer_sha256': producers}
        record = {**core, 'status': 'normal_sim_prepared', 'reuse_fingerprint_sha256': digest(json_bytes(core)),
                  'code_state': {'git_head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip(),
                                 'worktree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=PROJECT))},
                  'components': {name: {**binding, 'path': (relative_dir / name).as_posix()} for name, binding in components.items()},
                  'counts': {'parents': len(parents), 'batches': len(parents), 'events': 6 * len(parents),
                             'materials': 8 * len(parents), 'registrations': 15 * len(parents)},
                  'snapshot_id': snapshot_id, 'sim_verify_at_ms': config['clock']['verify_at_ms'],
                  'runtime': {'python_version': platform.python_version(), 'conda_prefix': sys.prefix,
                              'generated_at_utc': datetime.now(timezone.utc).isoformat()},
                  'normal_component_status': 'prepared', 'independent_acceptance': 'pending_separate_record',
                  'formal_package_status': 'not_built', 'model_execution_status': 'not_run',
                  'ledger_deployment_status': 'not_deployed', 'sample_sufficiency': 'not_determined'}
        if record_path.exists():
            try:
                old = read_json(record_path)
                require(old.keys() == record.keys(), 'output_conflict')
                require(all(old[key] == value for key, value in record.items() if key not in ('runtime', 'code_state')),
                        'output_conflict')
                for name, raw in files.items():
                    require(safe_path(destination / name).read_bytes() == raw, 'output_conflict')
            except (OSError, ValueError, KeyError, TypeError):
                raise SimError('output_conflict') from None
            print(json_bytes(old).decode('utf-8'))
            return 0
        require(not destination.exists(), 'output_conflict')
        staging = Path(tempfile.mkdtemp(prefix='sim-normal-', dir=PROJECT / '.tmp'))
        for name, raw in files.items():
            (staging / name).write_bytes(raw)
            require(digest((staging / name).read_bytes()) == components[name]['sha256'], 'io_error')
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, destination)
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open('xb') as stream:
            stream.write(json_bytes(record) + b'\n')
        print(json_bytes(record).decode('utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        code = exc.code if isinstance(exc, SimError) else ('io_error' if isinstance(exc, OSError) else 'invalid_config')
        print(json.dumps({'stage': 'sim_normal',
                          'status': 'needs_confirmation' if code == 'unapproved_protocol' else 'sim_normal_incomplete',
                          'error': {'code': code}}))
        return 2
