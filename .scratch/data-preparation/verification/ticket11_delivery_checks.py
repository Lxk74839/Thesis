"""Independent release checks against ticket11's approved literals and matrix."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


PROJECT = Path(__file__).resolve().parents[3]
KINDS = 'harvest_record packaging_binding storage_log inspection_sample inspection_report transport_dispatch transport_receipt retail_status'.split()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def wire(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path(value):
    result = PROJECT / value
    check('..' not in result.parts and result.is_relative_to(PROJECT), 'path_escape')
    for item in (result, *result.parents):
        check(not item.is_symlink() and not item.is_junction(), 'reparse_path')
        if item == PROJECT:
            break
    return result.resolve()


def load(value):
    return json.loads(path(value).read_bytes())


def rows(value):
    return [json.loads(line) for line in path(value).read_bytes().splitlines()]


def identity(prefix, tag, *parts):
    return prefix + sha(('Thesis-SIM-1:' + tag + '\0' + '\0'.join(parts)).encode())


def protect(before_path):
    before = load(before_path)
    changed = []
    for item in before['files']:
        item_path = path(item['path'])
        if not item_path.is_file():
            changed.append(item['path'])
            continue
        with item_path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != item['sha256'] or item_path.stat().st_size != item['bytes']:
            changed.append(item['path'])
    check(path('.gitattributes').read_bytes().startswith(bytes.fromhex(before['gitattributes_prefix_bytes'])), 'attribute_prefix')
    check(not changed, 'protected_bytes_changed')
    return {'status': 'passed', 'protected_files': len(before['files']), 'changed_files': changed,
            'gitattributes_prefix_preserved': True}


def conformance(record_path, audit_root):
    record_path = path(record_path)
    record = load(record_path)
    root = record_path.parents[2]
    package = root / Path(record['components']['manifest.json']['path']).parent
    baseline_path = path(record['inputs']['normal_record']['path'])
    baseline = load(baseline_path)
    baseline_root = baseline_path.parents[2]
    base = {name: rows(baseline_root / spec['path']) for name, spec in baseline['components'].items()}
    base_raw = {name: path(baseline_root / spec['path']).read_bytes() for name, spec in baseline['components'].items()}
    for group in (record['components'], record['audit_private']):
        for spec in group.values():
            raw = path(root / spec['path']).read_bytes()
            check(sha(raw) == spec['sha256'] and len(raw) == spec['bytes'] and len(raw.splitlines()) == spec['records'], 'published_binding')
    material = {(r['evidence_id'], r['version']): r for r in base['materials.jsonl']}
    by_parent = {(r['parent_asin'], r['kind']): r for r in base['materials.jsonl']}
    batches = {r['parent_asin']: r['sim_batch_id'] for r in base['batches.jsonl']}
    order = sorted(batches, key=lambda p: (bytes.fromhex(sha(('Thesis|ticket11|select|v1\0' + '20261015\0' + p).encode())), p.encode()))
    m, n = (len(order) + 9) // 10, len(order)
    selected = order[:m]
    first, second = set(selected[:m // 2]), set(selected[m // 2:])
    donor = dict(zip(selected, order[m:2 * m]))
    ids = {'V' + f'{i:02d}': 'q_' + sha(('Thesis|ticket11|view|v1\0' + '20261015\0' + f'{i:02d}').encode()) for i in range(16)}
    index = {r['view_id']: r for r in rows(package / 'view-index.jsonl')}
    check(set(index) == set(ids.values()), 'view_identity_set')
    plans = rows(package / 'private/mutation-plan.jsonl')
    check(len(plans) == 16, 'plan_count')
    plan_map = {r['view_name']: r for r in plans}
    distributions = {}
    for name, view_id in ids.items():
        number = int(name[1:])
        directory = package / Path(index[view_id]['snapshot_path']).parent
        actual = {key: rows(directory / key) for key in ('materials.jsonl', 'registrations.jsonl', 'change-actions.jsonl', 'policy.json')}
        for filename in ('batches.jsonl', 'events.jsonl'):
            check(path(directory / filename).read_bytes() == base_raw[filename], 'business_identity_or_event_changed')
        expected = dict(material)
        additions, actions = [], []
        for parent in selected:
            original = by_parent[parent, 'inspection_report']
            key = original['evidence_id'], 1
            if number == 1 or number == 13 and parent in first:
                del expected[key]
            elif number == 2:
                wrong = copy.deepcopy(original)
                other = by_parent[donor[parent], 'inspection_report']
                for field in ('parent_asin', 'sim_batch_id', 'event_id'):
                    wrong[field] = other[field]
                wrong['facts']['sample_id'] = other['facts']['sample_id']
                expected[key] = wrong
            elif number in (3, 5):
                negative = copy.deepcopy(original)
                negative['facts']['conclusion'] = 'fail'
                expected[key] = negative
            conflict = number in (6, 14) or number == 13 and parent in second
            revision = number in (9, 10, 15)
            if conflict or revision:
                report = copy.deepcopy(original)
                report['issued_at_ms'] = 1791372000000
                report['facts']['conclusion'] = 'pass' if number == 10 else 'fail'
                if conflict:
                    report['evidence_id'] = identity('d_', 'evidence', original['sim_batch_id'], 'inspection_report', 'SIM-LAB', 'record-2')
                else:
                    report['version'] = 2
                expected[report['evidence_id'], report['version']] = report
                additions.append(('material', report))
            if number in (7, 14, 15):
                retail = copy.deepcopy(by_parent[parent, 'retail_status'])
                retail['valid_to_ms'] = 1791417600000
                expected[retail['evidence_id'], 1] = retail
            if number == 12:
                harvest = copy.deepcopy(by_parent[parent, 'harvest_record'])
                harvest['facts']['origin_area_id'] = 'SIM-AREA-02'
                expected[harvest['evidence_id'], 1] = harvest
            if number == 8 or revision:
                action_type = 'supersedes' if revision else 'revokes'
                version = 2 if revision else 1
                action = {'schema_version': 'sim-change-action-1.0.0', 'source': 'SIM', 'action_type': action_type,
                    'target_kind': 'material', 'target_id': original['evidence_id'], 'target_version': version,
                    'supersedes_version': 1 if revision else None, 'parent_asin': parent,
                    'sim_batch_id': original['sim_batch_id'], 'event_id': original['event_id'], 'issuer_id': 'SIM-LAB',
                    'issued_at_ms': 1791372120000, 'effective_from_ms': 1791372120000}
                action['action_id'] = identity('a_', 'change_action', original['evidence_id'], str(version), action_type, '1791372120000')
                actions.append(action)
                additions.append(('change_action', action))
        actual_materials = {(r['evidence_id'], r['version']): r for r in actual['materials.jsonl']}
        check(len(actual_materials) == len(actual['materials.jsonl']) and actual_materials == expected, name + '_material_diff')
        check(actual['materials.jsonl'] == sorted(actual['materials.jsonl'], key=lambda r: (r['parent_asin'].encode(), KINDS.index(r['kind']), r['evidence_id'].encode(), r['version'])), 'material_order')
        check(actual['change-actions.jsonl'] == sorted(actions, key=lambda r: r['action_id']), name + '_actions')
        expected_receipts = {}
        for receipt in base['registrations.jsonl']:
            receipt = dict(receipt)
            receipt.pop('sequence')
            key = receipt['target_id'], receipt['version']
            if receipt['target_kind'] == 'material' and key in expected:
                if not (number == 3 and receipt['parent_asin'] in selected
                        and by_parent[receipt['parent_asin'], 'inspection_report']['evidence_id'] == receipt['target_id']):
                    receipt['content_sha256'] = sha(wire(expected[key]))
            if number == 4 and receipt['parent_asin'] in selected and receipt['target_id'] == by_parent[receipt['parent_asin'], 'inspection_report']['evidence_id']:
                receipt['issuer_id'] = 'SIM-RETAIL'
            expected_receipts[receipt['registration_id']] = receipt
        for kind, obj in additions:
            target = obj['evidence_id'] if kind == 'material' else obj['action_id']
            version = obj['version'] if kind == 'material' else 1
            receipt = {'schema_version': 'sim-registration-1.0.0' if kind == 'material' else 'sim-scenario-registration-1.0.0',
                'source': 'SIM', 'registry_backend': 'local_sim_registry', 'target_kind': kind, 'target_id': target,
                'version': version, 'parent_asin': obj['parent_asin'], 'sim_batch_id': obj['sim_batch_id'],
                'event_id': obj['event_id'], 'issuer_id': 'SIM-LAB', 'content_sha256': sha(wire(obj)),
                'registrar_id': 'SIM-REGISTRY', 'receipt_status': 'accepted',
                'registered_at_ms': 1791372060000 if kind == 'material' else 1791372180000,
                'registration_id': identity('g_', 'registration', kind, target, str(version))}
            expected_receipts[receipt['registration_id']] = receipt
        actual_receipts = {}
        for sequence, receipt in enumerate(actual['registrations.jsonl'], 1):
            check(type(receipt['sequence']) is int and receipt['sequence'] == sequence, 'registry_sequence')
            actual_receipts[receipt['registration_id']] = {k: v for k, v in receipt.items() if k != 'sequence'}
        check(len(actual_receipts) == len(actual['registrations.jsonl']) and actual_receipts == expected_receipts, name + '_registration_diff')
        check(actual['registrations.jsonl'] == sorted(actual['registrations.jsonl'], key=lambda r: (r['registered_at_ms'],
            ['batch', 'event', 'material', 'change_action'].index(r['target_kind']), r['target_id'].encode(), r['version'])), 'registry_order')
        if number != 11:
            check(path(directory / 'policy.json').read_bytes() == base_raw['policy.json'], 'policy_changed')
        else:
            policy = copy.deepcopy(base['policy.json'][0])
            policy.update(schema_version='sim-scenario-policy-1.0.0', base_policy_sha256=sha(base_raw['policy.json']),
                read_denials=sorted([{'principal_id': 'SIM-VERIFIER', 'target_kind': 'material',
                    'target_id': by_parent[p, 'inspection_report']['evidence_id'], 'version': 1} for p in selected], key=lambda r: r['target_id']))
            policy.pop('policy_id')
            policy['policy_id'] = 'p_' + sha(wire(policy))
            check(actual['policy.json'] == [policy], 'read_scope_escalation')
        plan = plan_map[name]
        check(plan['view_id'] == view_id and plan['selected_parents'] == selected, 'plan_selection')
        trace_bytes = {'before': {name: raw.splitlines() for name, raw in base_raw.items()},
                       'after': {filename: path(directory / filename).read_bytes().splitlines()
                                 for filename in ('materials.jsonl', 'registrations.jsonl', 'change-actions.jsonl')}}
        for change in plan['changes']:
            check(change['parent_asin'] in selected, 'plan_object')
            if change['operation'] == 'mismatch':
                check(change['donor_parent_asin'] == donor[change['parent_asin']], 'plan_donor')
            for side in ('before', 'after'):
                check(change[side]['policy_sha256'] == sha(base_raw['policy.json'] if side == 'before'
                    else path(directory / 'policy.json').read_bytes()), 'trace_policy')
                for group in ('materials', 'registrations', 'actions'):
                    for loc in change[side][group]:
                        check(loc['file'] in ('materials.jsonl', 'registrations.jsonl', 'change-actions.jsonl'), 'trace_path')
                        check(type(loc['line']) is int and loc['line'] > 0, 'trace_line')
                        raw = trace_bytes[side][loc['file']][loc['line'] - 1]
                        check(sha(raw) == loc['sha256'], 'trace_digest')
                        body = json.loads(raw)
                        check(loc['id'] in (body.get('evidence_id'), body.get('registration_id'), body.get('action_id')), 'trace_identity')
        distributions[name] = {'R1_SIM_Q1': Counter(), 'R1_AND_R5_SIM_Q1_ON_SALE': Counter()}
    check(n == 1494 and m == 150, 'formal_population')
    check(record['counts'] == {'business_parents': 1494, 'business_batches': 1494, 'views': 16,
        'request_profiles': 2, 'batch_rows': 23904, 'event_rows': 143424, 'material_rows': 191832,
        'registration_rows': 359985, 'change_action_rows': 600}, 'formal_counts')
    id_names = {v: k for k, v in ids.items()}
    seen, normal_states, controls, expiry_control = set(), {}, {}, {}
    reference_path = path(audit_root) / 'reference.jsonl'
    digest = hashlib.sha256()
    with reference_path.open('rb') as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            name, parent, profile = id_names[row['view_id']], row['parent_asin'], row['request_profile_id']
            check(parent in batches and row['sim_batch_id'] == batches[parent], 'reference_identity')
            expected_state = 'Supported'
            if parent in selected:
                if name in ('V01', 'V02', 'V03', 'V04', 'V08', 'V11'):
                    expected_state = 'Pending'
                elif name in ('V05', 'V09', 'V15'):
                    expected_state = 'Refuted'
                elif name in ('V06', 'V14'):
                    expected_state = 'Conflict'
                elif name == 'V13':
                    expected_state = 'Pending' if parent in first else 'Conflict'
                elif name == 'V07' and profile == 'R1_AND_R5_SIM_Q1_ON_SALE':
                    expected_state = 'Pending'
            check(row['candidate_state'] == expected_state and row['eligible'] is (expected_state == 'Supported'), 'reference_matrix')
            key = name, parent, profile
            check(key not in seen, 'reference_duplicate')
            seen.add(key)
            distributions[name][profile][row['candidate_state']] += 1
            if name == 'V00':
                normal_states[parent, profile] = row['candidate_state'], row['eligible']
            elif name == 'V12':
                controls[parent, profile] = row['candidate_state'], row['eligible']
            elif name == 'V07' and profile == 'R1_SIM_Q1':
                expiry_control[parent, profile] = row['candidate_state'], row['eligible']
    check(len(seen) == 47808 and controls == normal_states, 'unrelated_candidate_invariance')
    check(all(value == normal_states[key] for key, value in expiry_control.items()) and len(expiry_control) == 1494, 'expiry_r1_invariance')
    check_json = load(path(audit_root) / 'check.json')
    check(check_json['status'] == 'scenario_reference_complete' and check_json['reference_sha256'] == digest.hexdigest(), 'independent_reference_check')
    return {'status': 'passed', 'counts': record['counts'], 'reference_rows': len(seen), 'selected_parents': m,
        'selection_version': 'sha256-order-v1', 'distributions': distributions, 'reference_sha256': digest.hexdigest(),
        'unrelated_comparisons': len(controls), 'expiry_r1_comparisons': len(expiry_control),
        'business_identity_preserved': True, 'new_issuers': 0, 'broadened_permissions': 0}


def reproduce(first_record, second_record, first_audit, second_audit):
    left_path, right_path = path(first_record), path(second_record)
    left, right = load(left_path), load(right_path)
    check(left['reuse_fingerprint_sha256'] == right['reuse_fingerprint_sha256'], 'reproduction_inputs')
    compared = 0
    for group in ('components', 'audit_private'):
        check(set(left[group]) == set(right[group]), 'reproduction_component_set')
        for name, spec in left[group].items():
            one = path(left_path.parents[2] / spec['path']).read_bytes()
            two = path(right_path.parents[2] / right[group][name]['path']).read_bytes()
            check(one == two, 'reproduction_bytes_' + name)
            compared += 1
    one = path(first_audit) / 'reference.jsonl'
    two = path(second_audit) / 'reference.jsonl'
    with one.open('rb') as lhs, two.open('rb') as rhs:
        while chunk := lhs.read(1024 * 1024):
            check(chunk == rhs.read(len(chunk)), 'reference_reproduction')
        check(not rhs.read(1), 'reference_reproduction_length')
    return {'status': 'passed', 'stable_files_compared': compared, 'reference_bytes_equal': True}


def pairing(record_path):
    record_path = path(record_path)
    record = load(record_path)
    package = record_path.parents[2] / Path(record['components']['manifest.json']['path']).parent
    index = rows(package / 'view-index.jsonl')
    first = package / Path(index[0]['snapshot_path']).parent
    catalog = [{'parent_asin': r['parent_asin'], 'crop': r['crop']} for r in rows(first / 'batches.jsonl')[:4]]
    candidates = [r['parent_asin'] for r in catalog[1:]]
    request = next(r for r in rows(package / 'requests.jsonl') if r['profile_id'] == 'R1_AND_R5_SIM_Q1_ON_SALE')
    fixture = {'root_task_id': 'PUBLIC-PX-ROOT-1', 'split': 'development',
        'history': [{'parent_asin': catalog[0]['parent_asin'], 'rating': 4, 'text': 'PUBLIC SYNTHETIC HISTORY'}],
        'seen_parent_asins': [catalog[0]['parent_asin']], 'candidate_parent_asins': candidates,
        'catalog_projection': catalog, 'raw_request': request['design_text'], 'structured_request': request,
        'base_scores': dict(zip(candidates, [0.3, 0.2, 0.1])), 'base_score_version': 'fixture-only',
        'output_k': 1, 'model_version': 'fixture-only-no-model', 'tool_version': 'fixture-only-no-tool',
        'budget': {'fixture_units': 0}, 'failure_accounting': 'fixture-only-no-calls'}
    expected = {key: sha(wire(value)) for key, value in fixture.items()}
    handles = []
    for item in index:
        snapshot = load(package / item['snapshot_path'])
        batches = rows(package / Path(item['snapshot_path']).parent / 'batches.jsonl')
        check(set(candidates) <= {r['parent_asin'] for r in batches}, 'pairing_candidate_coverage')
        check(snapshot['scenario_version'] == record['scenario_version']
              and request['profile_id'] in snapshot['request_profiles'], 'pairing_snapshot_request')
        paired = copy.deepcopy(fixture)
        paired['candidate_parent_asins'] = [r['parent_asin'] for r in batches if r['parent_asin'] in candidates]
        projected = {r['parent_asin']: {'parent_asin': r['parent_asin'], 'crop': r['crop']} for r in batches}
        paired['catalog_projection'] = [projected[r['parent_asin']] for r in catalog]
        paired['structured_request'] = next(r for r in rows(package / 'requests.jsonl')
                                             if r['profile_id'] == snapshot['request_profiles'][1])
        paired['raw_request'] = paired['structured_request']['design_text']
        actual = {key: sha(wire(value)) for key, value in paired.items()}
        check(actual == expected, 'pairing_invariants')
        handles.append({'root_task_id': paired['root_task_id'], 'scenario_version': snapshot['scenario_version'],
            'snapshot_id': snapshot['snapshot_id'], 'request_profile_id': request['profile_id'],
            'view_id': item['view_id'], 'split': paired['split'], 'field_sha256': actual})
    rejected_controls = []
    for field in fixture:
        altered = copy.deepcopy(fixture)
        altered[field] = {'deliberate_public_fixture_mismatch': field}
        check({key: sha(wire(value)) for key, value in altered.items()} != expected, 'pairing_negative_control')
        rejected_controls.append(field)
    check(len(handles) == 16 and len({r['snapshot_id'] for r in handles}) == 16, 'pairing_handle_count')
    return {'status': 'passed', 'fixture_scope': 'synthetic_contract_only_not_ticket12_defaults',
        'fixture': fixture, 'handles': handles, 'field_comparisons': len(handles) * len(fixture),
        'rejected_mismatch_controls': rejected_controls, 'real_user_joins': 0, 'model_calls': 0, 'tool_calls': 0,
        'independent_users_added': 0, 'ticket13_runtime_integration': 'not_implemented'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['protection', 'conformance', 'reproduction', 'pairing'])
    parser.add_argument('--before')
    parser.add_argument('--record')
    parser.add_argument('--audit-root')
    parser.add_argument('--other-record')
    parser.add_argument('--other-audit-root')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    check(Path(sys.prefix).resolve() == PROJECT / '.conda/envs/Thesis', 'runtime')
    if args.mode == 'protection':
        result = protect(args.before)
    elif args.mode == 'conformance':
        result = conformance(args.record, args.audit_root)
    elif args.mode == 'pairing':
        result = pairing(args.record)
    else:
        result = reproduce(args.record, args.other_record, args.audit_root, args.other_audit_root)
    result.update(program_sha256=sha(Path(__file__).read_bytes()),
                  git_head_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip())
    output = path(args.report)
    check(not output.exists(), 'report_exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(wire(result) + b'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'distributions'}))


if __name__ == '__main__':
    main()
