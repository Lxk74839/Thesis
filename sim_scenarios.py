"""The fixed ticket11 evidence-view profile behind prepare_data.py."""

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from sim_normal import (CONFIG_SHAPE, KINDS, PROJECT, PROTOCOL, SimError, check_shape, digest, json_bytes,
                        object_id, read_json, require, safe_path, unique_object)


VERSION = 'sim-scenarios-1.0.0'
PROFILES = ['R1_SIM_Q1', 'R1_AND_R5_SIM_Q1_ON_SALE']
DRAFT = '.scratch/data-preparation/ticket11-stage1-evidence-scenarios-review-draft-20261015.md'
DRAFT_SHA = 'a79381ac48041ff7fd3e6b4e6ddc5a36a30cfd17e9f8ce813e631f5c9ffe0931'
AUTHORIZATION = '.scratch/data-preparation/ticket11-implementation-authorization-20261015.md'
SELECTION = {'population': 'baseline_parent_asin', 'algorithm': 'sha256-order-v1', 'seed': '20261015',
             'numerator': 1, 'denominator': 10, 'rounding': 'ceil',
             'donor_rule': 'next_disjoint_block', 'shared_set': True}
CLOCK = {'verify_at_ms': 1791417600000, 'sealed_at_ms': 1791375000000,
         'new_report_issued_at_ms': 1791372000000, 'new_report_registered_at_ms': 1791372060000,
         'action_issued_at_ms': 1791372120000, 'action_effective_from_ms': 1791372120000,
         'action_registered_at_ms': 1791372180000, 'expired_retail_valid_to_ms': 1791417600000}
IDENTITY = {'new_issuers': [], 'additional_report_slot': 'record-2',
            'status_change_authority': 'issuer_own_lineage_only',
            'read_principal_id': 'SIM-VERIFIER', 'registrar_id': 'SIM-REGISTRY'}
PUBLICATION = {'layout': 'self_contained_full_views_v1', 'repeat_count': 1,
               'extra_replicates': 0, 'overwrite': False}
SHAPE = {'schema_version': str, 'version': str, 'profile': str, 'byte_contract': str,
         'normal_binding': {name: {'path': str, 'sha256': str} for name in ('record', 'acceptance', 'config')},
         'protocol_binding': {key: str for key in PROTOCOL},
         'approval_binding': dict.fromkeys(('draft_path', 'draft_sha256', 'record_path', 'record_sha256'), str),
         'request_profile_ids': [str], 'selection': {key: type(value) for key, value in SELECTION.items()},
         'view_ids': [str], 'clock': {key: int for key in CLOCK},
         'identity': {**{key: str for key in IDENTITY if key != 'new_issuers'}, 'new_issuers': [str]},
         'publication': {key: type(value) for key, value in PUBLICATION.items()}}


def load_config(path):
    config = read_json(path)
    check_shape(config, SHAPE)
    require(config['protocol_binding'] == PROTOCOL, 'unapproved_protocol')
    approval = config['approval_binding']
    require(approval['draft_path'] == DRAFT and approval['draft_sha256'] == DRAFT_SHA
            and approval['record_path'] == AUTHORIZATION, 'unapproved_protocol')
    for name in ('draft', 'record'):
        require(digest(safe_path(approval[name + '_path']).read_bytes()) == approval[name + '_sha256'],
                'unapproved_protocol')
    for name in ('draft', 'record'):
        require(digest(safe_path(PROTOCOL[name + '_path']).read_bytes()) == PROTOCOL[name + '_sha256'],
                'unapproved_protocol')
    fixed = {'schema_version': 'sim-scenarios-config-1.0.0', 'version': VERSION,
             'profile': 'paired_evidence_views_v1', 'byte_contract': 'sim-jsonl-utf8-lf-1.0.0',
             'request_profile_ids': PROFILES, 'view_ids': [f'V{i:02d}' for i in range(16)],
             'selection': SELECTION, 'clock': CLOCK, 'identity': IDENTITY, 'publication': PUBLICATION}
    require(all(config[key] == value for key, value in fixed.items()))
    return config


def binding(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}


def baseline_types(value, key=''):
    if key.endswith('_ms') or key in ('bytes', 'records', 'version', 'sequence', 'cutoff_sequence',
            'quantity_units', 'stock_units', 'tests', 'audited_batches', 'blocking_findings', 'nonblocking_findings'):
        require(type(value) is int and (1 if key in ('version', 'sequence') else 0) <= value <= 2**53 - 1, 'invalid_baseline')
    elif key in ('may_create_batch', 'worktree_dirty'):
        require(type(value) is bool, 'invalid_baseline')
    elif key in ('counts', 'state_counts'):
        require(type(value) is dict, 'invalid_baseline')
        for child in value.values():
            require(type(child) is int and 0 <= child <= 2**53 - 1, 'invalid_baseline')
    elif type(value) is dict:
        for field, child in value.items():
            baseline_types(child, field)
    elif type(value) is list:
        for child in value:
            baseline_types(child)
    else:
        require(value is None or type(value) is str or type(value) is int, 'invalid_baseline')


def load_baseline(record_path, config):
    try:
        paths = {name: safe_path(info['path']) for name, info in config['normal_binding'].items()}
        require(record_path == paths['record'], 'invalid_baseline')
        for name, path in paths.items():
            require(digest(path.read_bytes()) == config['normal_binding'][name]['sha256'], 'invalid_baseline')
        record, acceptance, normal_config = [read_json(paths[name]) for name in ('record', 'acceptance', 'config')]
        baseline_types(record)
        baseline_types(acceptance)
        check_shape(normal_config, CONFIG_SHAPE)
        require(record_path.parent.name == 'sim' and record_path.parent.parent.name == 'records', 'invalid_baseline')
        generation_root = record_path.parents[2]
        require(record['stage'] == 'sim_normal' and record['status'] == 'normal_sim_prepared'
                and record['sim_version'] == 'sim-normal-1.0.0'
                and record['protocol_version'] == PROTOCOL['version'], 'invalid_baseline')
        require(set(acceptance['validation']) == {'fresh_reproduction', 'independent_full_check',
                'public_cli_tests', 'upstream_protection'}, 'invalid_baseline')
        require(acceptance['status'] == 'accepted_ticket10_normal_sim_component_only'
                and acceptance['generation_record'] == config['normal_binding']['record']
                and acceptance['components'] == record['components']
                and acceptance['approved_contract']['config'] == config['normal_binding']['config']
                and all(item['status'] == 'passed' for item in acceptance['validation'].values())
                and all(acceptance['reviews'][axis]['blocking_findings'] == 0 for axis in ('Standards', 'Spec')),
                'invalid_baseline')
        require(normal_config['protocol_binding'] == PROTOCOL and record['sim_verify_at_ms'] == CLOCK['verify_at_ms'],
                'invalid_baseline')
        names = {'batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl', 'policy.json', 'snapshot.json'}
        require(set(record['components']) == names, 'invalid_baseline')
        files, rows = {}, {}
        for name, info in record['components'].items():
            check_shape(info, {'path': str, 'sha256': str, 'bytes': int, 'records': int})
            path = safe_path(generation_root / info['path'])
            require(path == generation_root / 'data/sim' / record['catalog_version'] / record['sim_version'] / name,
                    'invalid_baseline')
            raw = path.read_bytes()
            require(len(raw) == info['bytes'] and digest(raw) == info['sha256'], 'invalid_baseline')
            require(raw.endswith(b'\n') and len(raw.splitlines()) == info['records'], 'invalid_baseline')
            files[name] = raw
            rows[name] = [json.loads(line, object_pairs_hook=unique_object,
                                    parse_constant=lambda value: require(False, 'invalid_baseline')) for line in raw.splitlines()]
            for line, row in zip(raw.splitlines(), rows[name]):
                baseline_types(row)
                require(json_bytes(row) == line, 'invalid_baseline')
        count = len(rows['batches.jsonl'])
        require(count > 1 and all(type(v) is int for v in record['counts'].values()), 'invalid_baseline')
        require(record['counts'] == {'parents': count, 'batches': count, 'events': 6 * count,
                                    'materials': 8 * count, 'registrations': 15 * count}, 'invalid_baseline')
        require(all(len(rows[name]) == multiplier * count for name, multiplier in
                    [('events.jsonl', 6), ('materials.jsonl', 8), ('registrations.jsonl', 15)]), 'invalid_baseline')
        snapshot = rows['snapshot.json'][0]
        require(acceptance['independent_reference']['audited_batches'] == count, 'invalid_baseline')
        policy = rows['policy.json'][0]
        require(json_bytes(policy['issuers']) == json_bytes(normal_config['issuers'])
                and policy['registrar_id'] == normal_config['registry']['registrar_id']
                and policy['read_principal_id'] == normal_config['registry']['read_principal_id']
                and policy['status_change_authority'] == 'issuer_own_lineage_only', 'invalid_baseline')
        expected_config = {**config['normal_binding']['config'], 'bytes': paths['config'].stat().st_size}
        require(record['inputs']['config'] == expected_config, 'invalid_baseline')
        require(snapshot['snapshot_id'] == record['snapshot_id'] and snapshot['sealed_at_ms'] == CLOCK['sealed_at_ms'],
                'invalid_baseline')
        return record, files, rows, paths, generation_root
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, SimError) and exc.code == 'invalid_path':
            raise
        raise SimError('invalid_baseline') from None


def requests():
    inspection = {'clause_id': 'c1', 'source': 'experiment_design', 'predicate': 'inspection_report_conclusion',
        'parameters': {'required_conclusion': 'pass', 'required_test_scope': ['SIM-Q1']},
        'object_scope': {'candidate': 'current', 'event_selection': 'baseline_inspection_event',
                         'sample_binding': 'event_sample_id'},
        'time_scope': {'mode': 'sampling_event', 'ttl_ms': None}, 'evidence_profile_id': 'inspection_sample_report_v1'}
    retail = {'clause_id': 'c2', 'source': 'experiment_design', 'predicate': 'retail_status',
        'parameters': {'required_status': 'on_sale'},
        'object_scope': {'candidate': 'current', 'event_selection': 'baseline_retail_event', 'sample_binding': None},
        'time_scope': {'mode': 'current_assertion', 'verify_at_ms': CLOCK['verify_at_ms'],
                       'interval_rule': 'from_inclusive_to_exclusive'}, 'evidence_profile_id': 'retail_current_status_v1'}
    texts = ['按已有历史偏好排序，仅考虑指定采样的SIM-Q1报告结论为pass的候选',
             '按已有历史偏好排序，仅考虑指定采样的SIM-Q1报告结论为pass且在SIM核验时点有有效在售记录的候选']
    return [{'schema_version': 'sim-scenario-request-1.0.0', 'profile_id': profile,
             'source': 'experiment_design', 'design_text': text, 'necessary_clauses': clauses,
             'preference_policy': 'inherit_root_history'}
            for profile, text, clauses in zip(PROFILES, texts, [[inspection], [inspection, retail]])]


def encoded_rows(rows):
    return b''.join(json_bytes(row) + b'\n' for row in rows)


def changed_view(number, selected, population, files, rows):
    materials = copy.deepcopy(rows['materials.jsonl'])
    registrations = copy.deepcopy(rows['registrations.jsonl'])
    actions, changes, denials = [], [], []
    operation_name = {1: 'missing', 2: 'mismatch', 3: 'digest', 4: 'registration', 5: 'negative',
                      6: 'conflict', 7: 'expiry', 8: 'revoke', 9: 'version_fail', 10: 'version_pass',
                      11: 'permission', 12: 'unrelated'}.get(number)
    operations = [(operation_name, parent) for parent in selected] if operation_name else []
    if number == 13:
        half = len(selected) // 2
        operations = [('missing', parent) for parent in selected[:half]] + [('conflict', parent) for parent in selected[half:]]
    elif number in (14, 15):
        operations = [(operation, parent) for parent in selected
                      for operation in (('conflict' if number == 14 else 'version_fail'), 'expiry')]
    for operation, parent in operations:
        kind = {'expiry': 'retail_status', 'unrelated': 'harvest_record'}.get(operation, 'inspection_report')
        material = next(row for row in materials if row['parent_asin'] == parent and row['kind'] == kind)
        before = {'evidence_id': material['evidence_id'], 'version': material['version'],
                  'sha256': digest(json_bytes(material))}
        if operation == 'missing':
            materials.remove(material)
        elif operation == 'permission':
            denials.append({'principal_id': 'SIM-VERIFIER', 'target_kind': 'material',
                           'target_id': material['evidence_id'], 'version': 1})
        elif operation == 'mismatch':
            donor_parent = population[len(selected) + selected.index(parent)]
            donor = next(row for row in rows['materials.jsonl'] if row['parent_asin'] == donor_parent
                         and row['kind'] == 'inspection_report')
            for field in ('parent_asin', 'sim_batch_id', 'event_id'):
                material[field] = donor[field]
            material['facts']['sample_id'] = donor['facts']['sample_id']
            receipt = next(row for row in registrations if row['target_id'] == material['evidence_id'])
            receipt['content_sha256'] = digest(json_bytes(material))
        elif operation in ('digest', 'negative'):
            material['facts']['conclusion'] = 'fail'
            if operation == 'negative':
                receipt = next(row for row in registrations if row['target_id'] == material['evidence_id'])
                receipt['content_sha256'] = digest(json_bytes(material))
        elif operation == 'registration':
            receipt = next(row for row in registrations if row['target_id'] == material['evidence_id'])
            receipt['issuer_id'] = 'SIM-RETAIL'
        elif operation == 'expiry':
            material['valid_to_ms'] = CLOCK['expired_retail_valid_to_ms']
            receipt = next(row for row in registrations if row['target_id'] == material['evidence_id'])
            receipt['content_sha256'] = digest(json_bytes(material))
        elif operation == 'unrelated':
            material['facts']['origin_area_id'] = 'SIM-AREA-02'
            receipt = next(row for row in registrations if row['target_id'] == material['evidence_id'])
            receipt['content_sha256'] = digest(json_bytes(material))
        elif operation == 'conflict':
            second = copy.deepcopy(material)
            second.update(evidence_id=object_id('d_', 'evidence', material['sim_batch_id'],
                          'inspection_report', 'SIM-LAB', 'record-2'), issued_at_ms=CLOCK['new_report_issued_at_ms'])
            second['facts']['conclusion'] = 'fail'
            materials.append(second)
            receipt = copy.deepcopy(next(row for row in registrations if row['target_id'] == material['evidence_id']))
            receipt.update(target_id=second['evidence_id'], content_sha256=digest(json_bytes(second)),
                           registration_id=object_id('g_', 'registration', 'material', second['evidence_id'], '1'),
                           registered_at_ms=CLOCK['new_report_registered_at_ms'])
            registrations.append(receipt)
        elif operation in ('revoke', 'version_fail', 'version_pass'):
            is_version = operation != 'revoke'
            if is_version:
                second = copy.deepcopy(material)
                second.update(version=2, issued_at_ms=CLOCK['new_report_issued_at_ms'])
                second['facts']['conclusion'] = 'fail' if operation == 'version_fail' else 'pass'
                materials.append(second)
                receipt = copy.deepcopy(next(row for row in registrations if row['target_id'] == material['evidence_id']))
                receipt.update(version=2, content_sha256=digest(json_bytes(second)),
                    registration_id=object_id('g_', 'registration', 'material', second['evidence_id'], '2'),
                    registered_at_ms=CLOCK['new_report_registered_at_ms'])
                registrations.append(receipt)
            target_version = 2 if is_version else 1
            action_type = 'supersedes' if is_version else 'revokes'
            action = {'schema_version': 'sim-change-action-1.0.0', 'source': 'SIM',
                      'action_type': action_type, 'target_kind': 'material', 'target_id': material['evidence_id'],
                      'target_version': target_version, 'supersedes_version': 1 if is_version else None,
                      'parent_asin': parent, 'sim_batch_id': material['sim_batch_id'], 'event_id': material['event_id'],
                      'issuer_id': 'SIM-LAB', 'issued_at_ms': CLOCK['action_issued_at_ms'],
                      'effective_from_ms': CLOCK['action_effective_from_ms']}
            action['action_id'] = object_id('a_', 'change_action', action['target_id'], str(target_version),
                                            action_type, str(action['effective_from_ms']))
            actions.append(action)
            receipt = copy.deepcopy(next(row for row in registrations if row['target_id'] == material['evidence_id']))
            receipt.update(schema_version='sim-scenario-registration-1.0.0', target_kind='change_action',
                target_id=action['action_id'], version=1, content_sha256=digest(json_bytes(action)),
                registration_id=object_id('g_', 'registration', 'change_action', action['action_id'], '1'),
                registered_at_ms=CLOCK['action_registered_at_ms'])
            registrations.append(receipt)
        changes.append({'operation': operation, 'parent_asin': parent, 'before': before,
                        'after': None if operation == 'missing' else digest(json_bytes(material))})
        if operation == 'mismatch':
            changes[-1]['donor_parent_asin'] = donor_parent
    materials.sort(key=lambda row: (row['parent_asin'].encode(), KINDS.index(row['kind']),
                                    row['evidence_id'].encode(), row['version']))
    registrations.sort(key=lambda row: (row['registered_at_ms'],
        ('batch', 'event', 'material', 'change_action').index(row['target_kind']), row['target_id'].encode(), row['version']))
    for sequence, receipt in enumerate(registrations, 1):
        receipt['sequence'] = sequence
    actions.sort(key=lambda row: row['action_id'])
    result = {name: files[name] for name in ('batches.jsonl', 'events.jsonl', 'policy.json')}
    result.update({'materials.jsonl': encoded_rows(materials), 'registrations.jsonl': encoded_rows(registrations),
                   'change-actions.jsonl': encoded_rows(actions)})
    if denials:
        policy = copy.deepcopy(rows['policy.json'][0])
        policy.update(schema_version='sim-scenario-policy-1.0.0', base_policy_sha256=digest(files['policy.json']),
                      read_denials=sorted(denials, key=lambda row: row['target_id']))
        del policy['policy_id']
        policy['policy_id'] = 'p_' + digest(json_bytes(policy))
        result['policy.json'] = json_bytes(policy) + b'\n'
    for change in changes:
        parent = change['parent_asin']
        kind = {'expiry': 'retail_status', 'unrelated': 'harvest_record'}.get(change['operation'], 'inspection_report')
        original_ids = {r['evidence_id'] for r in rows['materials.jsonl'] if r['parent_asin'] == parent and r['kind'] == kind}
        for label, source in [('before', rows), ('after', {'materials.jsonl': materials,
                'registrations.jsonl': registrations, 'change-actions.jsonl': actions})]:
            material_ids = original_ids | {r['evidence_id'] for r in source['materials.jsonl']
                                           if r['parent_asin'] == parent and r['kind'] == kind}
            target_ids = material_ids | {r['action_id'] for r in source.get('change-actions.jsonl', [])
                                         if r['parent_asin'] == parent and r['target_id'] in material_ids}
            change[label] = {}
            for filename, short, id_key, ids in [
                    ('materials.jsonl', 'materials', 'evidence_id', material_ids),
                    ('registrations.jsonl', 'registrations', 'target_id', target_ids),
                    ('change-actions.jsonl', 'actions', 'target_id', material_ids)]:
                change[label][short] = [{'file': filename, 'line': line, 'sha256': digest(json_bytes(row)),
                                         'id': row.get('action_id', row.get('registration_id', row.get('evidence_id')))}
                                        for line, row in enumerate(source.get(filename, []), 1) if row[id_key] in ids]
            change[label]['policy_sha256'] = digest(files['policy.json'] if label == 'before' else result['policy.json'])
    return result, changes


def build_package(staging, baseline, files, rows):
    population = sorted((row['parent_asin'] for row in rows['batches.jsonl']),
        key=lambda parent: (bytes.fromhex(digest(('Thesis|ticket11|select|v1\0' + '20261015\0' + parent).encode())),
                            parent.encode()))
    require(len(set(population)) == len(population), 'invalid_baseline')
    size = (len(population) + 9) // 10
    selected = population[:size]
    require(len(population) >= 2 * size, 'invalid_baseline')
    components, index, plans = {}, [], []
    totals = {'business_parents': len(population), 'business_batches': len(population), 'views': 16,
              'request_profiles': 2, 'batch_rows': 0, 'event_rows': 0, 'material_rows': 0,
              'registration_rows': 0, 'change_action_rows': 0}

    def write(name, raw, count):
        path = staging / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        require(path.read_bytes() == raw, 'publication_incomplete')
        info = {'bytes': len(raw), 'records': count, 'sha256': digest(raw)}
        components[name] = info
        return info

    request_info = write('requests.jsonl', encoded_rows(requests()), 2)
    for number in range(16):
        view_id = 'q_' + digest(('Thesis|ticket11|view|v1\0' + '20261015\0' + f'{number:02d}').encode())
        view_path = 'views/' + view_id + '/'
        view_files, changes = changed_view(number, selected, population, files, rows)
        view_components = {name: write(view_path + name, raw, len(raw.splitlines()))
                           for name, raw in view_files.items()}
        snapshot = {'schema_version': 'sim-scenario-snapshot-1.0.0', 'source': 'SIM',
            'catalog_version': baseline['catalog_version'], 'scenario_version': VERSION,
            'base_sim_version': baseline['sim_version'], 'base_snapshot_id': baseline['snapshot_id'],
            'protocol_version': PROTOCOL['version'], 'policy_id': json.loads(view_files['policy.json'])['policy_id'],
            'sealed_at_ms': CLOCK['sealed_at_ms'], 'verify_at_ms': CLOCK['verify_at_ms'],
            'cutoff_sequence': view_components['registrations.jsonl']['records'],
            'request_profiles': PROFILES, 'requests_sha256': request_info['sha256'], 'components': view_components}
        snapshot['snapshot_id'] = 'n_' + digest(b'Thesis-SIM-1:scenario_snapshot\0' + json_bytes(snapshot))
        info = write(view_path + 'snapshot.json', json_bytes(snapshot) + b'\n', 1)
        index.append({'view_id': view_id, 'snapshot_path': view_path + 'snapshot.json',
                      'snapshot_sha256': info['sha256'], 'base_snapshot_id': baseline['snapshot_id']})
        plans.append({'view_name': f'V{number:02d}', 'view_id': view_id, 'base_snapshot_id': baseline['snapshot_id'],
                      'selected_parents': selected, 'selection_version': 'sha256-order-v1', 'changes': changes})
        for field, filename in [('batch_rows', 'batches.jsonl'), ('event_rows', 'events.jsonl'),
                                ('material_rows', 'materials.jsonl'), ('registration_rows', 'registrations.jsonl'),
                                ('change_action_rows', 'change-actions.jsonl')]:
            totals[field] += view_components[filename]['records']
    write('view-index.jsonl', encoded_rows(sorted(index, key=lambda row: row['view_id'])), 16)
    manifest = {'schema_version': 'sim-scenario-manifest-1.0.0', 'source': 'SIM',
                'catalog_version': baseline['catalog_version'], 'scenario_version': VERSION,
                'base_snapshot_id': baseline['snapshot_id'], 'counts': totals, 'components': copy.deepcopy(components)}
    write('manifest.json', json_bytes(manifest) + b'\n', 1)
    private_raw = encoded_rows(plans)
    (staging / 'private').mkdir()
    (staging / 'private/mutation-plan.jsonl').write_bytes(private_raw)
    return components, totals, {'bytes': len(private_raw), 'records': 16, 'sha256': digest(private_raw)}


def reuse_record(record_path, destination, output_root, relative, core, parent_count):
    try:
        old = read_json(record_path)
        require(set(old) == set(core) | {'schema_version', 'status', 'reuse_fingerprint_sha256', 'components',
            'audit_private', 'counts', 'code_state', 'runtime', 'independent_acceptance', 'formal_package_status',
            'model_execution_status', 'ledger_deployment_status', 'sample_sufficiency'})
        require(json_bytes({key: old[key] for key in core}) == json_bytes(core))
        require(old['reuse_fingerprint_sha256'] == digest(json_bytes(core)))
        require(old['status'] == 'evidence_scenarios_prepared' and old['schema_version'] == 'sim-scenario-record-1.0.0')
        for name, expected in {'independent_acceptance': 'pending_separate_record', 'formal_package_status': 'not_built',
                'model_execution_status': 'not_run', 'ledger_deployment_status': 'not_deployed',
                'sample_sufficiency': 'not_determined'}.items():
            require(old[name] == expected)
        check_shape(old['counts'], {key: int for key in ('business_parents', 'business_batches', 'views',
            'request_profiles', 'batch_rows', 'event_rows', 'material_rows', 'registration_rows', 'change_action_rows')})
        m = (parent_count + 9) // 10
        require(old['counts'] == {'business_parents': parent_count, 'business_batches': parent_count,
            'views': 16, 'request_profiles': 2, 'batch_rows': 16 * parent_count, 'event_rows': 96 * parent_count,
            'material_rows': 128 * parent_count + 5 * m - 2 * (m // 2),
            'registration_rows': 240 * parent_count + 10 * m - m // 2, 'change_action_rows': 4 * m})
        check_shape(old['code_state'], {'git_head_sha': str, 'worktree_dirty': bool})
        check_shape(old['runtime'], {'python_version': str, 'conda_prefix': str, 'generated_at_utc': str})
        require(len(old['components']) == 115 and set(old['audit_private']) == {'mutation-plan.jsonl'})
        specs = {**old['components'], 'private/mutation-plan.jsonl': old['audit_private']['mutation-plan.jsonl']}
        expected_paths = set()
        for name, info in specs.items():
            check_shape(info, {'path': str, 'sha256': str, 'bytes': int, 'records': int})
            require(info['path'] == (relative / name).as_posix())
            path = safe_path(output_root / info['path'])
            raw = path.read_bytes()
            require(len(raw) == info['bytes'] and digest(raw) == info['sha256']
                    and len(raw.splitlines()) == info['records'])
            expected_paths.add(path)
        actual_paths = {safe_path(path) for path in destination.rglob('*') if path.is_file()}
        require(actual_paths == expected_paths)
        return old
    except (OSError, ValueError, TypeError, KeyError):
        raise SimError('output_conflict') from None


def prepare_scenarios(sim_record, config_path, output_root):
    try:
        config_path = safe_path(config_path)
        config = load_config(config_path)
        sim_record, output_root = safe_path(sim_record), safe_path(output_root)
        baseline, files, rows, base_paths, base_root = load_baseline(sim_record, config)
        relative = Path('data/sim-scenarios') / baseline['catalog_version'] / VERSION
        destination = safe_path(output_root / relative)
        record_path = safe_path(output_root / 'records/sim-scenarios' / f'{baseline["catalog_version"]}-{VERSION}.json')
        for forbidden in (PROJECT / 'research', PROJECT / 'manuscript', PROJECT / 'data/sim',
                          PROJECT / 'records/sim', base_root / 'data/sim'):
            require(not output_root.is_relative_to(forbidden), 'invalid_path')
        inputs = {name: binding(path) for name, path in {
            'scenario_config': config_path, 'normal_record': base_paths['record'],
            'normal_acceptance': base_paths['acceptance'], 'normal_config': base_paths['config'],
            'protocol_draft': safe_path(PROTOCOL['draft_path']), 'protocol_record': safe_path(PROTOCOL['record_path']),
            'approval_draft': safe_path(DRAFT), 'authorization': safe_path(AUTHORIZATION)}.items()}
        producers = {name: digest((PROJECT / name).read_bytes())
                     for name in ('prepare_data.py', 'sim_scenarios.py', 'sim_normal.py')}
        core = {'stage': 'evidence_scenarios', 'catalog_version': baseline['catalog_version'],
                'scenario_version': VERSION, 'protocol_version': PROTOCOL['version'], 'profile': config['profile'],
                'inputs': inputs, 'producer_sha256': producers}
        if record_path.exists():
            old = reuse_record(record_path, destination, output_root, relative, core, len(rows['batches.jsonl']))
            print(json_bytes(old).decode())
            return 0
        require(not destination.exists(), 'output_conflict')
        staging = Path(tempfile.mkdtemp(prefix='sim-scenarios-', dir=safe_path(PROJECT / '.tmp')))
        components, counts, private = build_package(staging, baseline, files, rows)
        record = {**core, 'schema_version': 'sim-scenario-record-1.0.0', 'status': 'evidence_scenarios_prepared',
            'reuse_fingerprint_sha256': digest(json_bytes(core)),
            'components': {name: {**info, 'path': (relative / name).as_posix()} for name, info in components.items()},
            'audit_private': {'mutation-plan.jsonl': {**private, 'path': (relative / 'private/mutation-plan.jsonl').as_posix()}},
            'counts': counts, 'code_state': {
                'git_head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip(),
                'worktree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=PROJECT))},
            'runtime': {'python_version': platform.python_version(), 'conda_prefix': sys.prefix,
                        'generated_at_utc': datetime.now(timezone.utc).isoformat()},
            'independent_acceptance': 'pending_separate_record', 'formal_package_status': 'not_built',
            'model_execution_status': 'not_run', 'ledger_deployment_status': 'not_deployed',
            'sample_sufficiency': 'not_determined'}
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, destination)
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open('xb') as stream:
            stream.write(json_bytes(record) + b'\n')
        print(json_bytes(record).decode())
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        code = exc.code if isinstance(exc, SimError) else (
            'publication_incomplete' if isinstance(exc, OSError) else 'invalid_config')
        print(json.dumps({'stage': 'evidence_scenarios', 'status': 'evidence_scenarios_incomplete',
                          'error': {'code': code}}))
        return 2
