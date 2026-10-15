"""Independent ticket10 audit; no production imports or status/plan inputs."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys


PROJECT = Path(__file__).resolve().parents[3]
STAGES = 'harvest packaging storage inspection transport retail'.split()
KINDS = 'harvest_record packaging_binding storage_log inspection_sample inspection_report transport_dispatch transport_receipt retail_status'.split()
MATERIAL_STAGE = dict(zip(KINDS, 'harvest packaging storage inspection inspection transport transport retail'.split()))
SCHEMAS = {
    'batches.jsonl': 'schema_version source parent_asin crop catalog_version sim_batch_id sim_profile_id protocol_version issuer_id version created_at_ms',
    'events.jsonl': 'schema_version source event_id parent_asin sim_batch_id stage actor_id version event_start_ms event_end_ms predecessor_event_ids',
    'materials.jsonl': 'schema_version source evidence_id parent_asin sim_batch_id event_id kind issuer_id temporal_mode version issued_at_ms facts',
    'registrations.jsonl': 'schema_version source registry_backend registration_id target_kind target_id version sequence parent_asin sim_batch_id event_id issuer_id content_sha256 registrar_id receipt_status registered_at_ms',
    'policy.json': 'schema_version source policy_id catalog_version sim_version identity_mode creation_source issuers registrar_id read_principal_id read_scope status_change_authority',
    'snapshot.json': 'schema_version source protocol_version catalog_version sim_version registry_backend cutoff_sequence sealed_at_ms verify_at_ms policy_id reference_request components snapshot_id',
}
FACT_KEYS = {
    'harvest_record': 'origin_area_id crop harvested_at_ms',
    'packaging_binding': 'harvest_event_id packaged_at_ms package_condition quantity_units unit',
    'storage_log': 'coverage_start_ms coverage_end_ms segments',
    'inspection_sample': 'sample_id sampled_at_ms',
    'inspection_report': 'sample_id test_scope test_started_at_ms test_completed_at_ms conclusion',
    'transport_dispatch': 'transport_segment_id departed_at_ms from_location_id to_location_id quantity_units unit',
    'transport_receipt': 'transport_segment_id arrived_at_ms from_location_id to_location_id quantity_units unit handover_status',
    'retail_status': 'observed_at_ms location_id status stock_units unit',
}


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    obj = {}
    for key, value in pairs:
        check(key not in obj, 'duplicate_json_key')
        obj[key] = value
    return obj


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda value: check(False, 'nonfinite_json'))


def keys(obj, expected):
    check(type(obj) is dict and set(obj) == set(expected.split()), 'closed_fields')


def primitives(value):
    if type(value) is dict:
        for child in value.values():
            primitives(child)
    elif type(value) is list:
        check(len({wire(child) for child in value}) == len(value), 'duplicate_array_entry')
        for child in value:
            primitives(child)
    elif type(value) is int:
        check(0 <= value <= 2**53 - 1, 'integer_range')
    else:
        check(value is None or type(value) is bool or (type(value) is str and value and '\0' not in value), 'primitive_type')


def integer(value):
    check(type(value) is int and 0 <= value <= 2**53 - 1, 'integer_type')


def location(value):
    path = PROJECT / value
    check('..' not in path.parts and path.is_relative_to(PROJECT), 'invalid_path')
    for part in [path, *path.parents]:
        check(not part.is_symlink() and not part.is_junction(), 'invalid_path')
        if part == PROJECT:
            break
    check(path.resolve().is_relative_to(PROJECT), 'invalid_path')
    return path.resolve()


def binding(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw)}


def identifier(tag, *parts):
    # This implements the published NUL-delimited identifier contract independently.
    payload = ('Thesis-SIM-1:' + tag).encode() + b'\0' + b'\0'.join(part.encode('utf-8') for part in parts)
    return {'batch': 'b_', 'event': 'e_', 'evidence': 'd_', 'sample': 's_', 'transport_segment': 't_', 'registration': 'g_'}[tag] + sha(payload)


def audit(record_path):
    check(record_path.parent.name == 'sim' and record_path.parent.parent.name == 'records', 'record_layout')
    generation_root = record_path.parents[2]
    record = parse(record_path.read_bytes())
    for count in record['counts'].values():
        integer(count)
    integer(record['sim_verify_at_ms'])
    check(record['stage'] == 'sim_normal' and record['status'] == 'normal_sim_prepared', 'record_status')
    cv, sv = record['catalog_version'], record['sim_version']
    check(record_path.name == f'{cv}-{sv}.json', 'record_layout')
    keys(record['inputs'], 'config protocol_record protocol_draft catalog_record catalog')
    for source in record['inputs'].values():
        keys(source, 'path sha256 bytes')
        integer(source['bytes'])
        check(binding(location(source['path'])) == source, 'input_binding')
    config = parse(location(record['inputs']['config']['path']).read_bytes())
    integer(config['catalog_binding']['expected_parent_count'])
    integer(config['facts']['quantity_units'])
    for value in config['clock'].values():
        integer(value)
    for schedule in (config['events'], config['materials']):
        for times in schedule.values():
            for value in times.values():
                integer(value)
    check(config['schema_version'] == 'sim-normal-config-1.0.0' and config['profile'] == 'normal_six_stage_v1'
          and config['version'] == sv and config['catalog_binding']['version'] == cv, 'config_version')
    check(record['protocol_version'] == config['protocol_binding']['version'] == 'sim-evidence-protocol-1.0.0', 'protocol_version')
    for name, expected in [('record', 'ef7f34e0868c879963287c4085418ed2748939f394ea61ea1751635b4da7abc6'),
                           ('draft', '6ae2dd42b943b65eda899560be8cffa68fac8570ad362439b2a100de76720461')]:
        check(record['inputs']['protocol_' + name]['sha256'] == config['protocol_binding'][name + '_sha256'] == expected,
              'protocol_binding')
    for name, expected in record['producer_sha256'].items():
        check(sha(location(name).read_bytes()) == expected, 'producer_binding')
    keys(record['producer_sha256'], 'prepare_data.py sim_normal.py')
    core = {key: record[key] for key in ('stage', 'catalog_version', 'sim_version', 'profile', 'protocol_version', 'inputs', 'producer_sha256')}
    check(sha(wire(core)) == record['reuse_fingerprint_sha256'], 'fingerprint')
    catalog_record = parse(location(record['inputs']['catalog_record']['path']).read_bytes())
    integer(catalog_record['counts']['included'])
    cb = config['catalog_binding']
    check(catalog_record['stage'] == 'catalog' and catalog_record['status'] == 'catalog_complete'
          and catalog_record['scope_version'] == cv, 'catalog_status')
    check(record['inputs']['catalog_record']['path'] == cb['record_path']
          and record['inputs']['catalog_record']['sha256'] == cb['record_sha256'], 'catalog_record_binding')
    check(record['inputs']['catalog']['path'] == catalog_record['catalog_path']
          and record['inputs']['catalog']['sha256'] == catalog_record['catalog_sha256'] == cb['component_sha256'], 'catalog_binding')
    catalog = [parse(line) for line in location(catalog_record['catalog_path']).read_bytes().splitlines()]
    parents = {row['parent_asin']: row['crop'] for row in catalog if row['status'] == 'included'}
    check(len(parents) == len(catalog) == cb['expected_parent_count'] == catalog_record['counts']['included'], 'catalog_count')
    rows, originals, actual_components = {}, {}, {}
    keys(record['components'], 'batches.jsonl events.jsonl materials.jsonl registrations.jsonl policy.json snapshot.json')
    for name, spec in record['components'].items():
        keys(spec, 'path sha256 bytes records')
        integer(spec['bytes'])
        integer(spec['records'])
        expected_path = f'data/sim/{cv}/{sv}/{name}'
        check(spec['path'] == expected_path, 'component_path')
        raw = location(generation_root / spec['path']).read_bytes()
        check(sha(raw) == spec['sha256'] and len(raw) == spec['bytes'], 'component_digest')
        check(raw.endswith(b'\n') and b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'), 'byte_contract')
        lines = raw[:-1].split(b'\n')
        check(len(lines) == spec['records'], 'component_count')
        values = [parse(line) for line in lines]
        for line, obj in zip(lines, values):
            if name in ('batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl'):
                integer(obj['version'])
                for field, value in obj.items():
                    if field.endswith('_ms') or field == 'sequence':
                        integer(value)
            if name == 'materials.jsonl':
                for field, value in obj['facts'].items():
                    if field.endswith('_ms') or field in ('quantity_units', 'stock_units'):
                        integer(value)
                if obj['kind'] == 'storage_log':
                    for segment in obj['facts']['segments']:
                        integer(segment['start_ms'])
                        integer(segment['end_ms'])
            if name == 'snapshot.json':
                for field in ('cutoff_sequence', 'sealed_at_ms', 'verify_at_ms'):
                    integer(obj[field])
                for component in obj['components'].values():
                    integer(component['bytes'])
                    integer(component['records'])
            primitives(obj)
            check(wire(obj) == line, 'canonical_bytes')
            extra = ' valid_from_ms valid_to_ms' if name == 'materials.jsonl' and obj['kind'] == 'retail_status' else ''
            keys(obj, SCHEMAS[name] + extra)
            check(obj['source'] == 'SIM', 'source_disclosure')
        rows[name], originals[name] = values, lines
        actual_components[name] = {key: spec[key] for key in ('sha256', 'bytes', 'records')}
    check(len(rows['policy.json']) == len(rows['snapshot.json']) == 1, 'single_object_components')
    policy, snapshot = rows['policy.json'][0], rows['snapshot.json'][0]
    check(policy['schema_version'] == 'sim-policy-1.0.0' and snapshot['schema_version'] == 'sim-snapshot-1.0.0', 'global_schema')
    snapshot_core = {key: value for key, value in snapshot.items() if key != 'snapshot_id'}
    check(snapshot['snapshot_id'] == record['snapshot_id'] == 'n_' + sha(b'Thesis-SIM-1:snapshot\0' + wire(snapshot_core)), 'snapshot_id')
    check(snapshot['components'] == {name: value for name, value in actual_components.items() if name != 'snapshot.json'}, 'snapshot_components')
    clock, ct, facts = config['clock'], config['events'], config['facts']
    tau, seal = snapshot['verify_at_ms'], snapshot['sealed_at_ms']
    integer(tau)
    integer(seal)
    check(seal <= tau == clock['verify_at_ms'] == record['sim_verify_at_ms'] and seal == clock['snapshot_sealed_at_ms'], 'snapshot_time')
    check(policy['catalog_version'] == snapshot['catalog_version'] == cv and policy['sim_version'] == snapshot['sim_version'] == sv,
          'scope_version')
    check(snapshot['protocol_version'] == record['protocol_version'] and snapshot['registry_backend'] == 'local_sim_registry', 'snapshot_scope')
    check(policy['policy_id'] == snapshot['policy_id'] == 'sim-normal-policy-1.0.0'
          and policy['identity_mode'] == 'simulated_allowlist_no_crypto' and policy['creation_source'] == 'project_constructed_simulation'
          and policy['status_change_authority'] == 'issuer_own_lineage_only', 'policy_identity')
    check(policy['issuers'] == config['issuers'] and policy['registrar_id'] == 'SIM-REGISTRY'
          and policy['read_principal_id'] == 'SIM-VERIFIER', 'policy_subjects')
    check(policy['read_scope'] == {'target_kinds': ['batch', 'event', 'material'], 'material_kinds': KINDS,
                                  'scope': 'current_snapshot_only'}, 'read_scope')
    by_issuer = {}
    for subject in policy['issuers']:
        keys(subject, 'issuer_id may_create_batch event_stages material_kinds')
        check(type(subject['may_create_batch']) is bool and subject['issuer_id'] not in by_issuer, 'issuer_schema')
        by_issuer[subject['issuer_id']] = subject
    approved_rights = {
        'SIM-PRODUCER': (True, ['harvest'], ['harvest_record']),
        'SIM-PACKER': (False, ['packaging'], ['packaging_binding']),
        'SIM-WAREHOUSE': (False, ['storage'], ['storage_log']),
        'SIM-SAMPLER': (False, [], ['inspection_sample']),
        'SIM-LAB': (False, ['inspection'], ['inspection_report']),
        'SIM-CARRIER': (False, ['transport'], ['transport_dispatch']),
        'SIM-RECEIVER': (False, [], ['transport_receipt']),
        'SIM-RETAIL': (False, ['retail'], ['retail_status']),
    }
    check(list(by_issuer) == list(approved_rights), 'approved_subject_order')
    for issuer, rights in approved_rights.items():
        subject = by_issuer[issuer]
        check((subject['may_create_batch'], subject['event_stages'], subject['material_kinds']) == rights, 'approved_authority')
    request = snapshot['reference_request']
    keys(request, 'profile_id source predicate required_test_scope required_conclusion time_scope required_kinds')
    check(request == config['reference_request'] and request['profile_id'] == 'R1_SIM_Q1'
          and request['source'] == 'experiment_design' and request['predicate'] == 'inspection_report_conclusion'
          and request['required_conclusion'] == 'pass' and request['required_test_scope'] == ['SIM-Q1']
          and request['required_kinds'] == ['inspection_sample', 'inspection_report'] and request['time_scope'] == 'sampling_event', 'request_contract')
    batch_rows, event_rows, material_rows = rows['batches.jsonl'], rows['events.jsonl'], rows['materials.jsonl']
    n = len(parents)
    counts = {'parents': n, 'batches': len(batch_rows), 'events': len(event_rows), 'materials': len(material_rows),
              'registrations': len(rows['registrations.jsonl'])}
    check(counts == record['counts'] == {'parents': n, 'batches': n, 'events': 6*n, 'materials': 8*n, 'registrations': 15*n}, 'full_counts')
    check([b['parent_asin'] for b in batch_rows] == sorted(parents, key=lambda x: x.encode('utf-8')), 'batch_coverage_order')
    check(event_rows == sorted(event_rows, key=lambda obj: (obj['parent_asin'].encode('utf-8'), STAGES.index(obj['stage']))), 'event_order')
    check(material_rows == sorted(material_rows, key=lambda obj: (obj['parent_asin'].encode('utf-8'), KINDS.index(obj['kind']))), 'material_order')
    batches = {b['sim_batch_id']: b for b in batch_rows}
    check(len(batches) == n, 'batch_unique')
    grouped_events, grouped_materials, targets = defaultdict(dict), defaultdict(dict), {}
    for name, kind, id_key in [('batches.jsonl', 'batch', 'sim_batch_id'), ('events.jsonl', 'event', 'event_id'), ('materials.jsonl', 'material', 'evidence_id')]:
        for obj, raw in zip(rows[name], originals[name]):
            check(obj['version'] == 1 and type(obj['version']) is int, 'business_version')
            check(obj['sim_batch_id'] in batches and obj['parent_asin'] == batches[obj['sim_batch_id']]['parent_asin'], 'object_binding')
            key = (kind, obj[id_key], obj['version'])
            check(key not in targets, 'duplicate_original')
            targets[key] = (obj, sha(raw))
            check(obj['schema_version'] == {'batch': 'sim-batch-1.0.0', 'event': 'sim-event-1.0.0', 'material': 'sim-material-1.0.0'}[kind], 'original_schema')
            if kind == 'event':
                check(obj['stage'] not in grouped_events[obj['sim_batch_id']], 'duplicate_event_stage')
                grouped_events[obj['sim_batch_id']][obj['stage']] = obj
            elif kind == 'material':
                check(obj['kind'] not in grouped_materials[obj['sim_batch_id']], 'duplicate_material_kind')
                grouped_materials[obj['sim_batch_id']][obj['kind']] = obj
    receipts = {}
    registrations = rows['registrations.jsonl']
    check(snapshot['cutoff_sequence'] == len(registrations), 'cutoff_sequence')
    ordered = sorted(registrations, key=lambda r: (r['registered_at_ms'], ['batch', 'event', 'material'].index(r['target_kind']), r['target_id'].encode(), r['version']))
    check(ordered == registrations, 'registration_order')
    for sequence, receipt in enumerate(registrations, 1):
        integer(receipt['version'])
        integer(receipt['registered_at_ms'])
        integer(receipt['sequence'])
        check(receipt['sequence'] == sequence and receipt['registered_at_ms'] <= seal, 'registration_time_sequence')
        key = (receipt['target_kind'], receipt['target_id'], receipt['version'])
        check(key in targets and key not in receipts, 'registration_target')
        obj, raw_sha = targets[key]
        check(receipt['content_sha256'] == raw_sha, 'original_digest')
        check(receipt['parent_asin'] == obj['parent_asin'] and receipt['sim_batch_id'] == obj['sim_batch_id']
              and receipt['event_id'] == (None if key[0] == 'batch' else obj['event_id']), 'registration_object')
        issuer = obj['actor_id'] if key[0] == 'event' else obj['issuer_id']
        check(receipt['issuer_id'] == issuer and issuer in by_issuer, 'receipt_issuer')
        subject = by_issuer[issuer]
        check((key[0] == 'batch' and subject['may_create_batch']) or
              (key[0] == 'event' and obj['stage'] in subject['event_stages']) or
              (key[0] == 'material' and obj['kind'] in subject['material_kinds']), 'issuer_authority')
        check(receipt['registration_id'] == identifier('registration', key[0], key[1], '1')
              and receipt['schema_version'] == 'sim-registration-1.0.0' and receipt['receipt_status'] == 'accepted'
              and receipt['registrar_id'] == 'SIM-REGISTRY' and receipt['registry_backend'] == 'local_sim_registry', 'receipt_contract')
        receipts[key] = receipt
    check(set(receipts) == set(targets), 'registration_completeness')
    references = []
    normal_errors = []
    for batch in batch_rows:
        bid, asin = batch['sim_batch_id'], batch['parent_asin']
        check(bid == identifier('batch', cv, asin) and batch['crop'] == parents[asin] and batch['catalog_version'] == cv
              and batch['sim_profile_id'] == config['profile'] and batch['protocol_version'] == record['protocol_version'], 'batch_identity')
        integer(batch['created_at_ms'])
        check(batch['created_at_ms'] == clock['batch_created_at_ms'] <= receipts[('batch', bid, 1)]['registered_at_ms']
              == clock['batch_registered_at_ms'], 'batch_time')
        ev, mats = grouped_events[bid], grouped_materials[bid]
        check(set(ev) == set(STAGES) and set(mats) == set(KINDS), 'slots_complete')
        previous, last_end = [], batch['created_at_ms']
        for stage in STAGES:
            event = ev[stage]
            for field in ('event_start_ms', 'event_end_ms'):
                integer(event[field])
            check(event['event_id'] == identifier('event', bid, stage) and event['predecessor_event_ids'] == previous, 'event_path')
            reg_time = receipts[('event', event['event_id'], 1)]['registered_at_ms']
            check(last_end <= event['event_start_ms'] == ct[stage]['start_ms'] <= event['event_end_ms']
                  == ct[stage]['end_ms'] <= reg_time == ct[stage]['registered_at_ms'], 'event_time')
            previous, last_end = [event['event_id']], event['event_end_ms']
        for kind in KINDS:
            mat = mats[kind]
            stage = MATERIAL_STAGE[kind]
            keys(mat['facts'], FACT_KEYS[kind])
            check(mat['event_id'] == ev[stage]['event_id'] and mat['evidence_id'] == identifier('evidence', bid, kind, mat['issuer_id']), 'material_identity')
            integer(mat['issued_at_ms'])
            reg_time = receipts[('material', mat['evidence_id'], 1)]['registered_at_ms']
            check(mat['issued_at_ms'] == config['materials'][kind]['issued_at_ms'] <= reg_time == config['materials'][kind]['registered_at_ms']
                  and receipts[('event', mat['event_id'], 1)]['registered_at_ms'] <= reg_time, 'material_registration_time')
            if kind == 'retail_status':
                integer(mat['valid_from_ms'])
                integer(mat['valid_to_ms'])
                check(mat['temporal_mode'] == 'current_assertion' and mat['valid_from_ms'] == clock['retail_valid_from_ms']
                      <= tau < mat['valid_to_ms'] == clock['retail_valid_to_ms'], 'retail_validity')
            else:
                check(mat['temporal_mode'] == 'historical_fact', 'historical_no_ttl')
        h, p, storage, sample, report, dispatch, received, retail = [mats[k]['facts'] for k in KINDS]
        check(h['crop'] == batch['crop'] and h['origin_area_id'] == facts['origin_area_id']
              and h['harvested_at_ms'] == ev['harvest']['event_end_ms'] <= mats[KINDS[0]]['issued_at_ms'], 'harvest_facts')
        check(p['harvest_event_id'] == ev['harvest']['event_id'] and p['packaged_at_ms'] == ev['packaging']['event_end_ms']
              <= mats[KINDS[1]]['issued_at_ms'] and p['package_condition'] == facts['packaging_condition'], 'packaging_facts')
        check(storage['coverage_start_ms'] == ev['storage']['event_start_ms'] and storage['coverage_end_ms'] == ev['storage']['event_end_ms']
              <= mats[KINDS[2]]['issued_at_ms'] and storage['segments'] == [{'start_ms': storage['coverage_start_ms'],
                  'end_ms': storage['coverage_end_ms'], 'mode': facts['storage_mode']}], 'storage_coverage')
        check(sample['sampled_at_ms'] == clock['sampled_at_ms'] and report['test_started_at_ms'] == clock['test_started_at_ms']
              and report['test_completed_at_ms'] == clock['test_completed_at_ms'], 'inspection_clock')
        time_ok = (ev['inspection']['event_start_ms'] <= sample['sampled_at_ms'] <= mats['inspection_sample']['issued_at_ms']
                   and sample['sampled_at_ms'] <= report['test_started_at_ms'] <= report['test_completed_at_ms']
                   <= ev['inspection']['event_end_ms'] and report['test_completed_at_ms'] <= mats['inspection_report']['issued_at_ms'])
        check(time_ok, 'inspection_time')
        check(dispatch['transport_segment_id'] == received['transport_segment_id'] == identifier('transport_segment', bid)
              and dispatch['departed_at_ms'] == ev['transport']['event_start_ms'] <= mats['transport_dispatch']['issued_at_ms']
              and received['arrived_at_ms'] == ev['transport']['event_end_ms'] <= mats['transport_receipt']['issued_at_ms'], 'transport_segment')
        for route in (dispatch, received):
            check(route['from_location_id'] == facts['warehouse_location_id'] and route['to_location_id'] == facts['retail_location_id'], 'transport_route')
        check(received['handover_status'] == facts['handover_status'] and retail['location_id'] == facts['retail_location_id']
              and retail['observed_at_ms'] == ev['retail']['event_start_ms'] == ev['retail']['event_end_ms'] <= mats['retail_status']['issued_at_ms']
              and retail['status'] == facts['retail_status'], 'retail_observation')
        for quantity, field in ((p, 'quantity_units'), (dispatch, 'quantity_units'), (received, 'quantity_units'), (retail, 'stock_units')):
            integer(quantity[field])
            check(quantity[field] == facts['quantity_units'] and quantity['unit'] == facts['quantity_unit'], 'quantity_binding')
        same_sample = sample['sample_id'] == report['sample_id'] == identifier('sample', bid)
        covered = set(request['required_test_scope']).issubset(report['test_scope'])
        binding_ok = all(mats[k]['parent_asin'] == asin and mats[k]['sim_batch_id'] == bid
                         and mats[k]['event_id'] == ev['inspection']['event_id'] for k in request['required_kinds'])
        read_authorized = (policy['read_principal_id'] == 'SIM-VERIFIER'
                           and set(request['required_kinds']).issubset(policy['read_scope']['material_kinds']))
        authorized = read_authorized and all(k in by_issuer[mats[k]['issuer_id']]['material_kinds'] for k in request['required_kinds'])
        related = [receipts[('batch', bid, 1)], receipts[('event', ev['inspection']['event_id'], 1)]]
        adopted, rejected = [], []
        for kind, pointers in [('inspection_sample', ['/facts/sample_id']),
                               ('inspection_report', ['/facts/sample_id', '/facts/test_scope', '/facts/conclusion'])]:
            mat = mats[kind]
            receipt = receipts[('material', mat['evidence_id'], 1)]
            related.append(receipt)
            if same_sample:
                adopted.append({'evidence_id': mat['evidence_id'], 'version': mat['version'],
                                'content_sha256': receipt['content_sha256'], 'fact_pointers': pointers})
            else:
                rejected.append({'evidence_id': mat['evidence_id'], 'version': mat['version'], 'reason': 'sample_binding'})
        complete = len(related) == 4
        support = binding_ok and authorized and same_sample and covered and time_ok and report['conclusion'] == request['required_conclusion']
        refute = binding_ok and authorized and same_sample and covered and time_ok and report['conclusion'] == 'fail'
        state = 'Conflict' if support and refute else 'Refuted' if refute else 'Supported' if support and complete else 'Pending'
        if (not same_sample or not covered or report['test_scope'] != facts['test_scope']
                or report['conclusion'] != facts['report_conclusion']):
            normal_errors.append('normal_r1_facts:' + asin)
        references.append({'schema_version': 'sim-r1-reference-1.0.0', 'source': 'SIM', 'reference_rule_version': 'r1-reference-1.0.0',
            'parent_asin': asin, 'sim_batch_id': bid, 'snapshot_id': snapshot['snapshot_id'], 'request_profile_id': request['profile_id'],
            'adopted_evidence': sorted(adopted, key=lambda a: a['evidence_id'].encode()),
            'rejected_evidence': sorted(rejected, key=lambda a: a['evidence_id'].encode()),
            'registration_ids': sorted(r['registration_id'] for r in related), 'scope_complete': complete,
            'support_present': support, 'refutation_present': refute, 'state': state,
            'derivation': {'batch_event_binding': binding_ok, 'sample_id_match': same_sample, 'required_project_covered': covered,
                'material_time_valid': time_ok, 'issuer_and_read_authorized': authorized, 'observed_report_conclusion': report['conclusion'],
                'requested_conclusion': request['required_conclusion'], 'selected_versions': {'sample': mats['inspection_sample']['version'],
                'report': mats['inspection_report']['version']}, 'related_registration_count': len(related)}})
    return references, counts, normal_errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True)
    parser.add_argument('--audit-root', required=True)
    args = parser.parse_args()
    try:
        audit_root = location(args.audit_root)
        record_path = location(args.record)
        check(not audit_root.exists() or (audit_root.is_dir() and not any(audit_root.iterdir())), 'audit_root_occupied')
        check(not record_path.is_relative_to(audit_root) and not audit_root.is_relative_to(record_path.parent), 'audit_overlap')
        if record_path.parent.name == 'sim' and record_path.parent.parent.name == 'records':
            original_area = location(record_path.parents[2] / 'data/sim')
            check(not audit_root.is_relative_to(original_area) and not original_area.is_relative_to(audit_root), 'audit_overlap')
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'status': 'failed', 'errors': ['invalid_audit_path']}))
        return 2
    audit_root.mkdir(parents=True, exist_ok=True)
    result = {'schema_version': 'sim-normal-check-1.0.0', 'status': 'failed', 'errors': [],
              'program': binding(Path(__file__)), 'runtime': {'python_version': platform.python_version(),
              'conda_prefix': sys.prefix, 'checked_at_utc': datetime.now(timezone.utc).isoformat()}}
    try:
        result['generation_record'] = binding(record_path)
        refs, counts, errors = audit(record_path)
        raw = b''.join(wire(row) + b'\n' for row in refs)
        with (audit_root / 'reference-r1.jsonl').open('xb') as stream:
            stream.write(raw)
        states = Counter(row['state'] for row in refs)
        result.update(counts=counts, audited_batches=len(refs), reference_sha256=sha(raw),
                      state_counts={state: states[state] for state in ('Supported', 'Refuted', 'Pending', 'Conflict')}, errors=errors)
        result['status'] = 'passed' if not errors and states['Supported'] == counts['parents'] else 'failed'
    except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
        result['errors'].append(str(exc) if isinstance(exc, ValueError) else type(exc).__name__)
    with (audit_root / 'check.json').open('xb') as stream:
        stream.write(wire(result) + b'\n')
    print(json.dumps({'status': result['status'], 'errors': result['errors']}))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
