"""Independent, read-only test100/public-trace checks. No production imports."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / '.tmp/recommendation-runtime'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def location(value):
    path = (ROOT / value).absolute()
    require('..' not in path.parts and path.is_relative_to(ROOT), 'outside_project')
    require(not any(p.exists() and (p.is_symlink() or p.is_junction()) for p in (path, *path.parents)), 'reparse_path')
    return path


def bound(ref):
    raw = location(ref['path']).read_bytes()
    require(len(raw) == ref['bytes'] and sha(raw) == ref['sha256'], 'content_binding_mismatch')
    return raw


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def check_plan(directory):
    directory = location(directory)
    manifest = json.loads((directory / 'plan.json').read_bytes())
    scope = 'ticket12-test100-on-demand-0.1.0'
    require(manifest['schema_version'] == scope and manifest['seed'] == '20261019'
        and manifest['plan_id'] == sha(canonical({k: v for k, v in manifest.items() if k != 'plan_id'})), 'invalid_plan')
    require(manifest['model_binding'] == dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget'))
        and manifest['execution_authorized'] is False and manifest['recommendation_runs'] == 0
        and manifest['provider_requests_sent'] == 0, 'execution_binding_not_null')
    names = ('sample-users.jsonl', 'root-references.jsonl', 'scenes.jsonl', 'user-scenarios.jsonl', 'tasks.jsonl')
    require(set(manifest['components']) == set(names), 'unexpected_plan_components')
    files = {name: [json.loads(line) for line in bound({'path': str(directory / name), **manifest['components'][name]}).splitlines()]
             for name in names}
    source = manifest['sources']
    if manifest['source_scope'] == 'accepted_test_pool':
        package_file = ROOT / '.scratch/ticket12-budget-20261018/on-demand-package-20261019.json'
        require(sha(package_file.read_bytes()) == '2c785971e00379bd51fbc15a3be0b14cc346f14b5dfb65ab7bd847aad92eaee3', 'package_changed')
        pins = {ref['path']: ref for ref in json.loads(package_file.read_bytes())['protected']}
        paths = ('records/splits/grain-A-1.1.15-user-split-1.0.0.json',
            'records/splits/grain-A-1.1.15-user-split-1.0.0-acceptance.json',
            'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1.json',
            'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1-acceptance.json',
            'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json',
            'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0-acceptance.json',
            'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json')
        require(len(source['authority']) == 7 and {r['path'] for r in source['authority']} == set(paths), 'missing_authority')
        for ref in source['authority']:
            require(ref == pins[ref['path']], 'unpinned_authority')
            bound(ref)
        pref = json.loads(bound(pins[paths[2]]))
        joint = json.loads(bound(pins[paths[4]]))
        require(source['cohort'] == pref['components']['evaluation'] and source['scenarios'] == pins[paths[6]], 'source_not_accepted')
        for name, component in (('roots', 'model/roots.jsonl'), ('candidates', 'model/candidates.jsonl'),
                ('view_bindings', 'view-bindings.jsonl'), ('catalog', 'model/catalog.jsonl'), ('candidate_map', 'candidate-map.jsonl')):
            require(source[name] == joint['components'][component], 'source_not_accepted')
        bound(source['catalog'])
        bound(source['candidate_map'])
    else:
        require(manifest['source_scope'] == 'public_fixture' and directory.is_relative_to(PUBLIC), 'invalid_scope')
        require(all(location(ref['path']).is_relative_to(PUBLIC) for ref in source.values()
                    if isinstance(ref, dict) and 'path' in ref), 'fixture_source_scope')
    cohort_raw = location(source['cohort']['path']).read_bytes()
    require(sha(cohort_raw) == source['cohort']['sha256'], 'cohort_changed')
    cohort = [json.loads(line) for line in cohort_raw.splitlines()]
    groups = {row['task_id']: row['split'] for row in cohort}
    require(len(groups) == len(cohort) == 1603 and sum(v == 'dev' for v in groups.values()) == 320
        and sum(v == 'test' for v in groups.values()) == 1283, 'cohort_counts')
    tests = sorted(key for key, split in groups.items() if split == 'test')
    ranked = sorted((hashlib.sha256(b'Thesis|ticket12|test100|v1\0' + b'20261019\0' + key.encode('ascii')).hexdigest(), key)
                    for key in tests)
    expected_users = [{'selection_rank': i + 1, 'root_task_id': key, 'selection_digest': digest}
                      for i, (digest, key) in enumerate(ranked[:100])]
    require(files['sample-users.jsonl'] == expected_users, 'sample_rule_or_list_mismatch')
    users = {row['root_task_id'] for row in expected_users}
    require(not any(groups[key] == 'dev' for key in users), 'development_overlap')
    require(manifest['test_pool_count'] == 1283 and manifest['test_pool_sha256'] == sha(canonical(tests)), 'pool_binding')
    roots = {row['root_task_id']: row for row in files['root-references.jsonl']}
    require(set(roots) == users and len(files['root-references.jsonl']) == 100, 'root_reference_counts')
    require(all(set(row) == {'root_task_id', 'root_ref', 'candidate_ref', 'C_sha256', 'H_sha256', 'base_scores_sha256'}
                for row in roots.values()), 'inlined_root_data')
    labels = tuple(f'V{i:02d}' for i in range(16)) + ('Q1', 'Q2')
    scenes = {row['view_id']: row for row in files['scenes.jsonl']}
    require(len(scenes) == 18 and [row['label'] for row in files['scenes.jsonl']] == list(labels), 'scene_mapping')
    scenario = json.loads(location(source['scenarios']['path']).read_bytes())
    require(sha(location(source['scenarios']['path']).read_bytes()) == source['scenarios']['sha256'], 'scenario_authority_changed')
    for row in scenes.values():
        snapshot = json.loads(bound(row['snapshot']))
        require(snapshot['snapshot_id'] == row['snapshot_id'], 'snapshot_id_mismatch')
        if row['label'].startswith('V'):
            require(row['view_id'] == 'q_' + sha(b'Thesis|ticket11|view|v1\0' + b'20261015\0' + row['label'][1:].encode()), 'V_id_mapping')
            accepted = scenario['components']['views/' + row['view_id'] + '/snapshot.json']
            require(row['snapshot'] == {k: accepted[k] for k in ('path', 'bytes', 'sha256')}, 'scene_not_from_accepted_view')
    bindings = {row['binding_id']: row for row in files['user-scenarios.jsonl']}
    require(len(bindings) == len(files['user-scenarios.jsonl']) == 1800
        and {(row['root_task_id'], row['view_id']) for row in bindings.values()} == {(u, v) for u in users for v in scenes}, 'binding_coverage')
    old_refs = {}
    original = {'V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2'}
    for identity, row in bindings.items():
        require(identity == sha(canonical([scope, row['root_task_id'], row['view_id']])), 'binding_identity')
        label = scenes[row['view_id']]['label']
        require(set(row) == ({'binding_id', 'root_task_id', 'view_id', 'existing_binding_ref'} if label in original else
                            {'binding_id', 'root_task_id', 'view_id'}), 'inlined_binding_data')
        if label in original:
            old_refs[row['existing_binding_ref']['offset']] = (row['existing_binding_ref'], row['root_task_id'], row['view_id'])

    def located(ref, wanted):
        path, digest, offset, found = location(ref['path']), hashlib.sha256(), 0, {}
        with path.open('rb') as stream:
            for line, raw in enumerate(stream, 1):
                digest.update(raw)
                if offset in wanted:
                    expected, key, view = wanted[offset]
                    require(expected == {'path': path.relative_to(ROOT).as_posix(), 'line': line,
                        'offset': offset, 'bytes': len(raw), 'sha256': sha(raw)}, 'source_locator')
                    record = json.loads(raw)
                    require(record['root_task_id'] == key and (view is None or record['view_id'] == view), 'source_row_identity')
                    found[key, view] = record
                offset += len(raw)
        require(digest.hexdigest() == ref['sha256'] and len(found) == len(wanted), 'source_file_or_locator_mismatch')
        return found
    source_roots = located(source['roots'], {row['root_ref']['offset']: (row['root_ref'], key, None) for key, row in roots.items()})
    for key, row in roots.items():
        require(all(row[k] == source_roots[key, None][k] for k in ('C_sha256', 'H_sha256', 'base_scores_sha256')), 'root_fingerprint')
    located(source['candidates'], {row['candidate_ref']['offset']: (row['candidate_ref'], key, None) for key, row in roots.items()})
    old_rows = located(source['view_bindings'], old_refs)
    require(all(all(record[k] == scenes[view][k] for k in ('view_id', 'snapshot_id', 'snapshot', 'arm'))
                for (key, view), record in old_rows.items()), 'existing_scene_binding_mismatch')
    tasks = files['tasks.jsonl']
    expected = {(identity, method) for identity, row in bindings.items()
                for method in (('M',) if scenes[row['view_id']]['label'].startswith('Q') else ('R', 'S', 'M'))}
    require(len(tasks) == len({row['task_key'] for row in tasks}) == 5000
        and {(row['binding_id'], row['method']) for row in tasks} == expected, 'task_coverage')
    for row in tasks:
        require(set(row) == {'task_key', 'binding_id', 'method', 'repeat', 'uses_model'}
            and type(row['repeat']) is int and row['repeat'] == 1
            and type(row['uses_model']) is bool and row['uses_model'] == (row['method'] != 'R'), 'task_fields')
        binding = bindings[row['binding_id']]
        require(row['task_key'] == sha(canonical([scope, binding['root_task_id'], binding['view_id'], row['method'], 1])), 'task_identity')
    counts = {'users': 100, 'development_overlap': 0, 'scenarios': 18, 'bindings': 1800, 'tasks': 5000,
              'model_tasks': sum(row['uses_model'] for row in tasks)}
    require(counts == manifest['counts'] and counts['model_tasks'] == 3400, 'count_summary')
    return {'status': 'passed_reference_preparation_only', 'plan_id': manifest['plan_id'],
            'counts': counts, 'provider_requests_sent': 0, 'recommendation_runs': 0}


def check_audit(path):
    path = location(path)
    audit = json.loads(path.read_bytes())
    binding, budget = audit['binding'], audit['budget']
    require(binding['execution_kind'] == 'on_demand_public'
        and binding['plan_source_scope'] == 'public_fixture'
        and binding['root_task_id'].startswith('PUBLIC-'), 'not_a_public_on_demand_audit')
    require(audit['terminal'] is not None and budget['binding'] == binding, 'audit_root_mismatch')
    contents, null_scopes = {}, 0

    def source_bytes(source):
        file = location(source['component_path'])
        require(file.is_relative_to(PUBLIC), 'nonpublic_audit_source')
        if file not in contents:
            raw = file.read_bytes()
            require(len(raw) == source['bytes'] and sha(raw) == source['component_sha256'], 'source_changed')
            contents[file] = raw
        raw = contents[file]
        if 'offset' in source:
            offset = source['offset']
            require(raw[:offset].count(b'\n') + 1 == source['line'], 'source_line_mismatch')
            return raw[offset:].split(b'\n', 1)[0]
        return raw

    def ranges(value, route=()):
        nonlocal null_scopes
        if isinstance(value, dict):
            if 'raw_utf8' in value and value['raw_utf8'] is None:
                require(route and route[-1] == 'actions_scope' and value.get('empty') is False
                        and 'source' in value and bool(source_bytes(value['source'])), 'missing_original_not_scope')
                null_scopes += 1
            if 'raw_sha256' in value:
                raw = source_bytes(value['source'])
                require(len(raw) == value['raw_bytes'] and sha(raw) == value['raw_sha256'], 'raw_source_mismatch')
            for key, item in value.items():
                ranges(item, (*route, key))
        elif isinstance(value, list):
            for item in value:
                ranges(item, route)
    ranges(audit['evidence']['acquired'])
    attempts, totals = 0, dict.fromkeys(('input_tokens', 'output_tokens', 'cost_microusd'), 0)
    request_ids = set()
    preparations = {row['prepared_id']: row for row in audit.get('preparations', [])}
    journal_path = path.parent / 'budget.jsonl'
    journal = [json.loads(line) for line in journal_path.read_bytes().splitlines()] if journal_path.exists() else []
    settlements = {row['reservation_id']: row for row in journal if row.get('status') in ('settled', 'unresolved')}
    for message in audit['messages']:
        request = json.loads(bound(message['request_ref']))
        response = json.loads(bound(message['response_ref']))
        summary = message['response_summary']
        require(request['request_id'] not in request_ids and request['run_id'] == binding['run_id']
                and request['execution_kind'] == 'on_demand_public' and request['model_id'] is None,
                'request_root_or_model_mismatch')
        request_ids.add(request['request_id'])
        prepared = preparations[request['prepared_id']]
        count = prepared['count']
        logical = {k: v for k, v in request.items() if k not in
                   ('input_token_upper_bound', 'deadline_ms', 'reservation_id', 'prepared_id', 'count_receipt_id')}
        logical['schema_version'] = 'rsm-model-prepare-0.1.0'
        proof = {'schema_version': 'on-demand-fixture-prepared-0.1.0', 'status': 'prepared',
            'project_id': count['project_id'], 'model_id': None, 'request': logical, 'provenance': 'fixture'}
        require(sha(canonical(proof)) == request['prepared_id'] and prepared['request_ref'] == message['request_ref']
            and count['prepared_id'] == request['prepared_id'] and count['receipt_id'] == request['count_receipt_id']
            and sha(canonical({k: v for k, v in count.items() if k != 'receipt_id'})) == count['receipt_id']
            and count['basis'] == 'fixture' and count['provider_requests_sent'] == 0
            and count['input_tokens'] == request['input_token_upper_bound'], 'request_prepare_count_binding')
        require(summary['provider_requests_sent'] == 0 and type(summary['attempted']) is bool, 'invalid_attempt_origin')
        attempts += int(summary['attempted'])
        if summary['status'] == 'ok':
            require(response['request_id'] == request['request_id'] and response['model_id'] is None,
                    'response_request_mismatch')
        require(message['root_reservation_id'] in budget['reservations'], 'missing_model_reservation')
        settled = settlements[message['root_reservation_id']]
        require(settled['observation']['request_ref'] == message['request_ref']
                and settled['observation']['response_ref'] == message['response_ref']
                and settled['usage']['model_calls'] == int(summary['attempted']), 'journal_trace_binding')
        for key in totals:
            value = summary['usage'].get(key)
            require(value is None or type(value) is int and value >= 0, 'invalid_usage')
            if value is not None and summary['status'] != 'usage_mismatch':
                totals[key] += value
        if summary['status'] in ('usage_mismatch', 'unknown_usage'):
            require(not budget['usage_exact'] and budget['held']['input_tokens'] > 0, 'unknown_usage_was_released')
    require(budget['usage']['model_calls'] == attempts, 'model_attempts_do_not_balance')
    require(all(budget['usage'][key] == value for key, value in totals.items()), 'model_usage_does_not_balance')
    if binding['method'] == 'R':
        require(attempts == 0 and not audit['messages'], 'R_used_model')
    if audit['terminal'] in ('released', 'valid_empty'):
        require((path.parent / 'publication.json').is_file(), 'missing_publication')
        require(set(budget['reservations']) <= set(settlements)
                and all(settlements[key]['status'] == 'settled' for key in budget['reservations']), 'publication_unsettled')
    else:
        require(not (path.parent / 'publication.json').exists(), 'failed_run_published')
    return {'status': 'passed_public_audit_only', 'path': path.relative_to(ROOT).as_posix(),
            'audit_sha256': sha(path.read_bytes()), 'model_attempts': attempts,
            'null_scopes': null_scopes, 'provider_requests_sent': 0}


def main():
    if len(sys.argv) == 5 and sys.argv[1] == 'delivery':
        plan, cases, report = map(location, sys.argv[2:])
        result = {'schema_version': 'test100-independent-delivery-0.1.0', 'plan': check_plan(plan)}
        require(cases.is_relative_to(PUBLIC), 'invalid_public_cases')
        audits = sorted([*cases.rglob('audit.json'), *cases.rglob('audit.failed.json')])
        require(bool(audits), 'no_public_runtime_evidence')
        result['public_runs'] = [check_audit(path) for path in audits]
        package = json.loads((ROOT / '.scratch/ticket12-budget-20261018/on-demand-package-20261019.json').read_bytes())
        for ref in package['protected']:
            bound(ref)
        ledger = location(package['offline']['ledger']).read_bytes()
        require(sha(ledger[:package['offline']['bytes']]) == package['offline']['sha256'], 'old_ledger_prefix_changed')
        rows = [json.loads(line) for line in ledger.splitlines()]
        seconds = sum(row['seconds'] for row in rows) - package['offline']['baseline_seconds']
        writes = sum(json.loads(line)['bytes'] for line in location(package['disk_ledger']).read_bytes().splitlines())
        require(seconds <= 900 and sum(row['seconds'] for row in rows) <= 1800 and writes <= 1073741824, 'resource_limit')
        result.update(status='passed_100x18_offline_preparation_only', protected_files=len(package['protected']),
            api_calls={'generate': 0, 'count': 0, 'other': 0}, original_T0_status='T0_A_incomplete',
            old_G1='failed_not_accepted', resource_observed_before_checker_settlement={'package_seconds': seconds, 'charged_bytes': writes})
        require(report.is_relative_to(ROOT / 'data/recommendation-runtime-audit/ticket12-100x18'), 'report_output_scope')
        with report.open('xb') as stream:
            stream.write(canonical(result) + b'\n')
        return {'status': result['status'], 'plan_id': result['plan']['plan_id'], 'public_runs': len(audits),
                'report': report.relative_to(ROOT).as_posix()}
    require(len(sys.argv) == 3 and sys.argv[1] in ('audit', 'plan'),
            'usage: check_on_demand_delivery.py audit|plan PATH')
    return check_audit(sys.argv[2]) if sys.argv[1] == 'audit' else check_plan(sys.argv[2])


if __name__ == '__main__':
    try:
        print(json.dumps(main(), sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error)}))
        raise SystemExit(2)
