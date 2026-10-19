"""Independent T0-A artifact/protection checker. Standard library only; no production imports."""
import argparse
from collections import Counter
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import time
import zlib

PROJECT = Path(__file__).resolve().parents[3]
BASE = '88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a'
MODEL = 'gpt-5.4-mini-2026-03-17'
VIEWS = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2')
MUTABLE_BASE = {'recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
    '.scratch/ticket12-budget-20261018/diagnostics/run_check.py'}
PILOT_CONTROL = '.scratch/ticket12-budget-20261018/recovery-pilot-package-20261019.json'
PILOT_SHA = '6da3c084bc2b1b298994f692db13d9b885dbd97cf180904e7a31cfefcb61c93b'
PILOT_FILES = ('t0_catalog.py', 'tests/test_t0_catalog.py',
    '.scratch/ticket12-budget-20261018/diagnostics/run_check.py',
    '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py',
    'model_adapter.py', 'provider_openai.py', 'token_counting.py', 'recommendation_runner.py',
    'evidence_access.py', 'joint_access.py', 'joint_tasks.py', 'evidence_verification.py', 'quality_fusion.py',
    'sim_normal.py', 'sim_scenarios.py')


def pilot_program(auth, package):
    ref = auth['program_acceptance']
    if not isinstance(ref, dict) or ref.get('path') != '.scratch/ticket12-budget-20261018/acceptance-t0-a-recovery-pilot-program-20261019.json':
        raise ValueError('pilot_program_record_path_not_allowed')
    if (auth['scope'] != 'development_catalog_only' or auth['old_catalog'] != package['old_catalog']
            or not re.fullmatch('[0-9a-f]{40}', auth['candidate']) or os.environ.get('THESIS_RESOURCE_DOMAIN') != 't0'
            or os.environ.get('THESIS_RECOVERY_STAGE') not in ('G0', 'G1')
            or auth['resource_ledger'] != package['t0']['ledger']
            or project_path(os.environ.get('THESIS_RESOURCE_LEDGER', '')) != project_path(auth['resource_ledger'])):
        raise ValueError('pilot_execution_binding_mismatch')
    if file_info(ref['path']) != {k: ref[k] for k in ('bytes', 'sha256')}:
        raise ValueError('pilot_program_acceptance_required')
    accepted = json_file(ref['path'])
    if (accepted['status'] != 'T0_A_recovery_pilot_program_accepted' or accepted['base'] != package['base']
            or accepted['candidate'] != auth['candidate'] or accepted['resource_package'] != auth['resource_package']
            or set(accepted['source_sha256']) != set(PILOT_FILES)):
        raise ValueError('pilot_program_acceptance_required')
    for name, expected in accepted['source_sha256'].items():
        if file_info(name)['sha256'] != expected:
            raise ValueError('program_source_changed')
    for axis in ('Standards', 'Spec'):
        review = accepted['reviews'][axis]
        if (review['candidate'] != auth['candidate'] or review['blocking_findings'] != 0
                or review['record']['path'] != '.scratch/ticket12-budget-20261018/verification-recovery-pilot-'
                    + axis.lower() + '-' + auth['candidate'][:7] + '.md'
                or file_info(review['record']['path']) != {k: review['record'][k] for k in ('bytes', 'sha256')}):
            raise ValueError('program_review_required')
    if subprocess.check_output(['git', 'diff', '--name-only', auth['candidate'], '--', *PILOT_FILES], cwd=PROJECT).strip():
        raise ValueError('program_source_changed')


def pilot_authorization(auth):
    package = json_file(PILOT_CONTROL)
    if sha(project_path(PILOT_CONTROL).read_bytes()) != PILOT_SHA:
        raise ValueError('pilot_package_binding_changed')
    if (auth.get('schema_version') != 't0-a-recovery-authorization-0.1.0'
            or auth.get('execution_stage') != 'pilot' or auth.get('operation') != 'controlled_recovery'):
        raise ValueError('pilot_stage_not_authorized')
    if set(auth) != set(('schema_version approved scope contract human_confirmation base candidate program_acceptance '
            'sources budget_candidate resource_ledger api_limits operation execution_stage resource_package source_receipt old_catalog').split()):
        raise ValueError('invalid_pilot_authorization')
    if (not auth.get('approved') or auth.get('base') != package['base']
            or auth.get('contract') != package['contract'] or auth.get('human_confirmation') != package['human_confirmation']
            or auth.get('api_limits') != package['api_limits'] or auth.get('budget_candidate') != 'B02-A+B03'
            or auth.get('resource_package') != {'path': PILOT_CONTROL, 'sha256': PILOT_SHA}
            or os.environ.get('THESIS_RECOVERY_PILOT_PACKAGE') != str(project_path(PILOT_CONTROL))):
        raise ValueError('pilot_authorization_mismatch')
    public = auth.get('scope') == 'public_catalog_test'
    if auth.get('sources') != package['public_sources' if public else 'development_sources']:
        raise ValueError('pilot_source_set_mismatch')
    if not public:
        pilot_program(auth, package)
    elif (auth.get('candidate') != 'PUBLIC' or auth.get('sources') != package['public_sources']
            or os.environ.get('THESIS_RESOURCE_DOMAIN') != 'offline'
            or auth.get('resource_ledger') != package['offline']['ledger']):
        raise ValueError('public_pilot_binding_mismatch')
    for ref in (auth['contract'], auth['human_confirmation']):
        if file_info(ref['path']) != {k: ref[k] for k in ('bytes', 'sha256')}:
            raise ValueError('pilot_confirmation_changed')
    return package


def pilot_snapshot(auth):
    started = time.perf_counter()
    package = pilot_authorization(auth)
    sources = auth['sources']
    public = auth['scope'] == 'public_catalog_test'
    if not public and os.environ.get('THESIS_RECOVERY_STAGE') != 'G0':
        raise ValueError('pilot_identity_stage_not_authorized')
    old_ref = auth['old_catalog']
    expected_old = {'path': '.tmp/ticket12-t0/diagnosis-20261019/catalog-baseline/catalog.json',
        'sha256': '901c13945cbfaa8d839badfb6dfdfdd72d2c850e1926ad37d3e4cd053f6e9040'} if public else package['old_catalog']
    if old_ref['path'] != expected_old['path'] or old_ref['sha256'] != expected_old['sha256']:
        raise ValueError('pilot_original_catalog_not_allowed')
    if file_info(old_ref['path']) != {k: old_ref[k] for k in ('bytes', 'sha256')}:
        raise ValueError('original_catalog_changed')
    stamps = {name: {'bytes': project_path(ref['path']).stat().st_size,
        'mtime_ns': project_path(ref['path']).stat().st_mtime_ns} for name, ref in sources.items()}
    files = {}
    for name, ref in sources.items():
        if name != 'identity_key':
            actual = file_info(ref['path'])
            if actual != {k: ref[k] for k in ('bytes', 'sha256')}:
                raise ValueError('pilot_source_changed')
            files[ref['path']] = actual
    old = json_file(old_ref['path'])
    directory = project_path(old_ref['path']).parent
    def metadata(name):
        if file_info(directory / name) != old['components'][name]:
            raise ValueError('original_metadata_changed')
        return json_file(directory / name)
    index, coverage = metadata('source-index.json'), metadata('coverage.json')
    views = sorted({name.rsplit('/', 1)[0] for name in coverage['by_view_method']})
    if (index['selection_sources'] != {k: sources[k] for k in ('accounts', 'identity_key')}
            or old['sources'] != sources or len(index['selected_roots']) != (1 if public else 320)
            or not public and set(views) != set(VIEWS)):
        raise ValueError('pilot_selection_mismatch')
    legacy = {} if public else pilot_legacy_metadata(auth, old, index, directory)
    protected = {} if public else protection()
    ref = sources['identity_key']
    key = project_path(ref['path']).read_bytes()
    if len(key) != ref['bytes'] or sha(key) != ref['sha256']:
        raise ValueError('pilot_identity_binding_mismatch')
    selected = sorted(hmac.new(key, b'preference-task-1.0.1\0' + row['user_id'].encode(), hashlib.sha256).hexdigest()
                      for row in rows(sources['accounts']['path']) if row['split'] == 'dev')
    del key
    if selected != index['selected_roots'] or len(set(selected)) != len(selected):
        raise ValueError('pilot_selection_mismatch')
    if any(stamps[name] != {'bytes': project_path(ref['path']).stat().st_size,
            'mtime_ns': project_path(ref['path']).stat().st_mtime_ns} for name, ref in sources.items()):
        raise ValueError('pilot_source_changed_during_snapshot')
    return {'schema_version': 't0-recovery-pilot-receipt-0.1.0',
        'status': 'PUBLIC_recovery_source_bound_only' if public else 'T0_A_recovery_G0_bound_only',
        'complete': True, 'base': package['base'], 'candidate': auth['candidate'],
        'authorization_binding': sha(canonical({k: v for k, v in auth.items() if k != 'source_receipt'})),
        'source_sha256': {name: file_info(name)['sha256'] for name in PILOT_FILES},
        'selected_roots': selected, 'pilot_roots': selected if public else legacy['pilot_roots'],
        'views': views, 'source_index': index, 'legacy': legacy, 'protection': protected, 'source_stamps': stamps,
        'files': files, 'identity_key_body_reads': 1, 'full_catalog_accepted': False,
        'identity_key_stamp': {'bytes': project_path(ref['path']).stat().st_size, 'mtime_ns': project_path(ref['path']).stat().st_mtime_ns},
        'original_T0_status': 'T0_A_incomplete', 'seconds': time.perf_counter() - started,
        'source_bytes': sum(r['bytes'] for r in sources.values()), 'provider_api_calls': auth['api_limits']}


def pilot_legacy_metadata(auth, catalog, index, directory):
    """Only the two declared metadata streams; never enumerate or open old objects."""
    expected = {(r, v, m, 1) for r in index['selected_roots'] for v in VIEWS for m in ('R', 'S', 'M')}
    components, plans, requests, by_root, wire = {}, {}, {}, {}, Counter()
    def metadata(name):
        digest, size = hashlib.sha256(), 0
        path = project_path(directory / name)
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        with path.open('rb') as stream:
            while raw := stream.readline(64 * 1024**2 + 1):
                if len(raw) > 64 * 1024**2 or not raw.endswith(b'\n'):
                    raise ValueError('legacy_metadata_line_limit_or_partial')
                digest.update(raw)
                size += len(raw)
                yield json.loads(raw)
        actual = {'bytes': size, 'sha256': digest.hexdigest()}
        if actual != catalog['components'][name] or before != (path.stat().st_size, path.stat().st_mtime_ns):
            raise ValueError('original_metadata_changed')
        components[name] = {**actual, 'mtime_ns': before[1]}
    for row in metadata('roots.jsonl'):
        key = (row['root_task_id'], row['view_label'], row['method'], row['repeat'])
        if key not in expected or key in plans:
            raise ValueError('legacy_plan_key_mismatch')
        complete = row.get('planned_terminal') != 'T0_A_incomplete' and not row.get('failure_reason')
        plans[key] = {'key': key, 'marked_complete': complete, 'request_count': row['request_count'],
            'plan_sha256': sha(canonical(row)) if complete else None}
        by_root.setdefault(key[0], []).append(key)
    for row in metadata('requests.jsonl'):
        key = (row['root_task_id'], row['view_label'], row['method'], 1)
        if key not in plans or key[2] == 'R':
            raise ValueError('legacy_request_plan_mismatch')
        requests.setdefault(key, []).append({'prepared_id': row['prepared_id'], 'wire_bytes': row['wire_bytes'],
            'count_payload_bytes': row['count_payload_bytes'], 'request_sha256': sha(canonical(row))})
        wire[key[0]] += row['wire_bytes']
    if any(row['request_count'] != len(requests.get(key, [])) for key, row in plans.items()):
        raise ValueError('legacy_request_count_mismatch')
    complete_roots = sorted(r for r, keys in by_root.items() if len(keys) == 30 and all(plans[k]['marked_complete'] for k in keys))
    partial = [key for key, row in plans.items() if not row['marked_complete']]
    counts = {'plans': len(plans), 'marked_complete': sum(p['marked_complete'] for p in plans.values()),
        'interrupted': len(partial), 'missing': len(expected - set(plans)),
        'complete_roots': len(complete_roots), 'roots_with_plans': len(by_root), 'requests': sum(map(len, requests.values()))}
    if counts != {'plans': 2403, 'marked_complete': 2402, 'interrupted': 1, 'missing': 7197,
            'complete_roots': 80, 'roots_with_plans': 81, 'requests': 22113}:
        raise ValueError('legacy_inventory_changed')
    first = complete_roots[0]
    heaviest = min((r for r in complete_roots if r != first), key=lambda r: (-wire[r], r))
    missing = min(set(index['selected_roots']) - set(by_root))
    chosen = [first, heaviest, partial[0][0], missing]
    if len(set(chosen)) != 4:
        raise ValueError('pilot_distinct_root_selection_failed')
    for key, row in plans.items():
        row['requests'] = requests.get(key, [])
    return {'inventory': counts, 'pilot_roots': chosen,
        'selection': [{'rule': rule, 'root_task_id': root, 'old_wire_bytes': wire[root],
            'old_plans': len(by_root.get(root, []))} for rule, root in zip(
            ('smallest_complete', 'max_wire_other_complete', 'interrupted', 'smallest_absent'), chosen)],
        'plans': [row for key, row in sorted(plans.items()) if key[0] in chosen], 'metadata': components,
        'old_object_bodies_read': 0, 'old_dependencies_read': 0, 'old_probes_read': 0,
        'old_markers_independently_accepted': False}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def project_path(value):
    path = Path(value)
    if '..' in path.parts:
        raise ValueError('unsafe_path')
    path = path if path.is_absolute() else PROJECT / path
    if not path.is_relative_to(PROJECT):
        raise ValueError('unsafe_path')
    for part in (path, *path.parents):
        if part.exists() and (part.is_symlink() or part.is_junction() or part.lstat().st_file_attributes & 1024):
            raise ValueError('reparse_path')
        if part == PROJECT:
            break
    return path


def file_info(path):
    digest, size = hashlib.sha256(), 0
    with project_path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def json_file(path):
    return json.loads(project_path(path).read_bytes())


def t0_path(value):
    path = project_path(value)
    if not any(path.is_relative_to(PROJECT / root) for root in ('data/ticket12-t0', '.tmp/ticket12-t0')):
        raise ValueError('T0_input_path_required')
    return path


def rows(path):
    with project_path(path).open('rb') as stream:
        for line in stream:
            yield json.loads(line)


def protection():
    names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE], cwd=PROJECT).decode().split('\0')
    return {name: file_info(name) for name in names if name and name not in MUTABLE_BASE}


def stored_objects(directory):
    """Independent decoder: no imports from the producer or provider mapper."""
    manifest_path = project_path(directory / 'objects/manifest.json')
    if not manifest_path.exists():
        if (directory / 'objects/requests.pack').exists():
            raise ValueError('missing_store_manifest')
        catalog = json_file(directory / 'catalog.json')
        if catalog['schema_version'] != 'T0-request-catalog-0.1.0':
            raise ValueError('unsupported_legacy_catalog')
        for name, expected in sorted(catalog['components'].items()):
            if name.startswith('objects/'):
                if not re.fullmatch(r'objects/[0-9a-f]{64}\.json', name):
                    raise ValueError('invalid_legacy_object_path')
                path = project_path(directory / name)
                if file_info(path) != expected:
                    raise ValueError('legacy_object_digest_mismatch')
                yield json_file(path)
        return
    manifest = json_file(manifest_path)
    omit = ('max_output_tokens', 'service_tier', 'store', 'stream')
    if (manifest['schema_version'] != 'T0-single-W-store-0.1.0' or manifest['codec'] != 'zlib-level1'
            or manifest['count_projection'] != 'openai-count-from-W-0.1.0' or manifest['count_omit'] != list(omit)
            or manifest['complete'] is not True):
        raise ValueError('unsupported_or_incomplete_store')
    path = project_path(directory / 'objects/requests.pack')
    info = file_info(path)
    if info['sha256'] != manifest['pack_sha256']:
        raise ValueError('pack_digest_mismatch')
    seen, offset = set(), 0
    with path.open('rb') as stream:
        for record in manifest['records']:
            if (not all(type(record[k]) is int for k in ('offset', 'bytes', 'raw_bytes', 'count_bytes'))
                    or record['offset'] != offset or not 0 < record['bytes'] <= 16 * 1024**2 + 65536
                    or offset + record['bytes'] > info['bytes'] or not 0 < record['raw_bytes'] <= 16 * 1024**2
                    or not 0 < record['count_bytes'] <= 16 * 1024**2):
                raise ValueError('invalid_object_index')
            meta = record['metadata']
            pid = meta['prepared_id']
            if (not re.fullmatch('[0-9a-f]{64}', pid) or pid in seen
                    or any(k in meta for k in ('wire_body', 'count_body', 'wire_utf8', 'count_utf8'))):
                raise ValueError('invalid_object_identity')
            seen.add(pid)
            stream.seek(offset)
            decoder = zlib.decompressobj()
            try:
                body = decoder.decompress(stream.read(record['bytes']), record['raw_bytes'] + 1)
            except zlib.error:
                raise ValueError('invalid_compressed_object') from None
            if (len(body) != record['raw_bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail):
                raise ValueError('invalid_compressed_object')
            wire = json.loads(body)
            count = {k: v for k, v in wire.items() if k not in omit}
            payload = canonical(count)
            if len(payload) != record['count_bytes']:
                raise ValueError('count_bytes_mismatch')
            yield {**meta, 'wire_body': wire, 'count_body': count, 'wire_utf8': body.decode(), 'count_utf8': payload.decode()}
            offset += record['bytes']
    if offset != info['bytes']:
        raise ValueError('unindexed_pack_bytes')


def object_info(prepared):
    wire, count = prepared['wire_body'], prepared['count_body']
    wb, pb = canonical(wire), canonical(count)
    if (prepared['schema_version'] != 'openai-prepared-0.1.0' or prepared['status'] != 'prepared'
            or prepared['mapper_version'] != 'openai-responses-mapper-0.1.0'
            or prepared['model_id'] != wire['model'] or wire['model'] != MODEL
            or wb.decode() != prepared['wire_utf8'] or pb.decode() != prepared['count_utf8']
            or sha(wb) != prepared['wire_sha256'] or sha(pb) != prepared['count_payload_sha256']
            or len(wb) != prepared['wire_bytes'] or max(len(wb), len(pb)) > 16 * 1024**2
            or count != {k: v for k, v in wire.items() if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')}
            or prepared['role_schema_sha256'] != sha(canonical(wire['text']['format']['schema']))
            or sha(canonical({k: prepared[k] for k in ('wire_sha256', 'count_payload_sha256', 'mapper_version',
                'tool_schema_sha256', 'role_schema_sha256', 'project_id')})) != prepared['prepared_id']
            or wire['reasoning'] != {'effort': 'none'} or wire['parallel_tool_calls'] is not False
            or wire['truncation'] != 'disabled' or wire['service_tier'] != 'default'
            or wire['store'] is not False or wire['stream'] is not False):
        raise ValueError('prepared_contract_mismatch')
    return (len(wb), len(pb), wire['max_output_tokens'])


def check_objects(directory):
    seen, wire_bytes, count_bytes = set(), 0, 0
    for prepared in stored_objects(directory):
        wb, pb, cap = object_info(prepared)
        if prepared['prepared_id'] in seen:
            raise ValueError('duplicate_prepared_object')
        seen.add(prepared['prepared_id'])
        wire_bytes += wb
        count_bytes += pb
    return {'schema_version': 't0-object-store-check-0.1.0', 'status': 'object_store_verified_only',
        'complete': True, 'objects_verified': len(seen), 'wire_bytes': wire_bytes, 'count_payload_bytes': count_bytes,
        'full_catalog_accepted': False, 'provider_api_calls': {'count': 0, 'generate': 0, 'other': 0},
        'capacity_judgment': 'not_performed', 'root_plans_generated': 0}


def check(auth, directory, protected, *, pilot=None):
    errors = []
    def need(value, code):
        if not value and code not in errors:
            errors.append(code)
    catalog = json_file(directory / 'catalog.json')
    coverage = json_file(directory / 'coverage.json')
    need(pilot is not None or not catalog.get('pilot_only'), 'pilot_not_full_delivery')
    need(catalog['schema_version'] in ('T0-request-catalog-0.1.0', 'T0-request-catalog-0.2.0'), 'wrong_catalog_schema')
    need(auth['api_limits'] == {'count': 0, 'generate': 0, 'other': 0} and auth['approved'] is True, 'authorization_mismatch')
    need(catalog['scope'] == auth['scope'] and catalog['candidate'] == auth['candidate'] and catalog['sources'] == auth['sources'], 'source_binding_mismatch')
    need(catalog['project_id'] == 'UNBOUND-T0-DEV-CATALOG' and catalog['external_count_ready'] is False
        and catalog['execution_budget'] is None and catalog['execution_authorized'] is False, 'execution_gate_mismatch')
    missing_objects = set()
    for name, expected in catalog['components'].items():
        if name not in ('roots.jsonl', 'requests.jsonl', 'dependencies.jsonl', 'source-index.json', 'coverage.json',
                         'objects/requests.pack', 'objects/manifest.json') and not re.fullmatch(r'objects/[0-9a-f]{64}\.json', name):
            need(False, 'component_path_not_allowed')
            continue
        path = project_path(directory / name)
        if not path.is_file():
            need(False, 'missing_object' if name.startswith('objects/') else 'missing_component')
            if name.startswith('objects/'):
                missing_objects.add(Path(name).stem)
        else:
            need(file_info(path) == expected, 'component_digest_mismatch')
    selection = json_file(directory / 'source-index.json')
    root_ids = selection['selected_roots']
    need(len(root_ids) == len(set(root_ids)), 'duplicate_selection')
    plans = list(rows(directory / 'roots.jsonl'))
    keys = [(p['root_task_id'], p['view_label'], p['method'], p['repeat']) for p in plans]
    plan_keys = set(keys)
    need(len(keys) == len(plan_keys), 'duplicate_plan')
    development = auth['scope'] == 'development_catalog_only'
    expected = {(root, view, method, 1) for root in root_ids for view in VIEWS for method in ('R', 'S', 'M')} if development else set(keys)
    if development and pilot is None:
        need(len(root_ids) == 320 and len(expected) == 9600, 'wrong_development_scale')
        need(bool(protected), 'protection_snapshot_required')
        need(os.environ.get('THESIS_RESOURCE_DOMAIN') == 't0', 'wrong_resource_domain')
    need(set(keys) == expected and len(plans) == coverage['plans'] == coverage['expected_plans'], 'plan_coverage_mismatch')
    if pilot is not None:
        expected = {(root, view, method, 1) for root in pilot['pilot_roots'] for view in pilot['views'] for method in ('R', 'S', 'M')}
        need(set(keys) == expected and set(root_ids) == set(pilot['pilot_roots']), 'pilot_coverage_mismatch')
    counts, roles, profiles, stages, failures, caps = Counter(), {}, {}, {}, Counter(), Counter()
    original_w, original_p, unique_w, unique_p = 0, 0, 0, 0
    objects, objects_info = set(), {}
    forbidden = ('user_id', 'assignment_reason', 'split_hash', 'component_path')
    for prepared in stored_objects(directory):
        sizes = object_info(prepared)
        pid = prepared['prepared_id']
        need(pid not in objects_info and prepared['input_tokens'] is None, 'duplicate_object_or_invented_count')
        initial, profile = [], set()
        for item in prepared['wire_body']['input']:
            if 'role' not in item:
                continue
            try:
                content = json.loads(item['content'])
            except (ValueError, TypeError):
                continue
            if isinstance(content, dict) and 'root_task_id' in content:
                initial.append((content['root_task_id'], 'H' in content and 'history' not in content
                                and not any(name in content for name in forbidden)))
                if pilot is not None:
                    need(sha(canonical(content)) in pilot['_initial_hashes'], 'pilot_complete_history_projection_mismatch')
            if isinstance(content, dict) and isinstance(content.get('runtime'), dict):
                if content['runtime']['stage'] == '农产品画像':
                    profile.update(content['runtime']['profile_candidates'])
        need(not any(('"' + name + '":') in prepared['wire_utf8'] for name in forbidden), 'host_metadata_in_wire')
        need(len(initial) == 1, 'initial_projection_missing_or_duplicate')
        objects_info[pid] = (*sizes, initial, profile)
        unique_w += sizes[0]
        unique_p += sizes[1]
    for row in rows(directory / 'requests.jsonl'):
        key = (row['root_task_id'], row['view_label'], row['method'], 1)
        need(key in plan_keys and row['method'] in ('S', 'M'), 'orphan_or_R_request')
        need(row['provenance'] == 'synthetic' and row['input_tokens'] is None and row['output_tokens'] is None
            and row['cost_microusd'] is None, 'invented_usage')
        counts[key] += 1
        roles.setdefault(key, set()).add(row['semantic_role'])
        stages.setdefault(key, []).append(row['output_kind'])
        failures[key] += row['script_response']['status'] == 'format_error'
        need(row['effective_role'] == ('单智能体' if row['method'] == 'S' else row['semantic_role']), 'role_mismatch')
        pid = row['prepared_id']
        if not isinstance(pid, str) or not re.fullmatch('[0-9a-f]{64}', pid):
            need(False, 'object_path_not_allowed')
            continue
        if pid not in objects_info:
            need(False, 'missing_object')
            continue
        wb, pb, cap, initial, profile = objects_info[pid]
        need(all(root == row['root_task_id'] and safe for root, safe in initial), 'unsafe_initial_projection')
        profiles.setdefault(key, set()).update(profile)
        caps[key] += cap
        original_w += wb
        original_p += pb
        objects.add(pid)
        if row['output_kind'] == 'final_submit':
            need(cap == 1500, 'final_cap_mismatch')
        else:
            need(cap == 8192, 'work_cap_mismatch')
    semantic_roles = {'需求解析', '用户画像', '推荐管理', '生命周期追溯', '农产品画像', '推荐依据核验'}
    for plan, key in zip(plans, keys):
        need(plan['request_count'] == counts[key], 'root_request_count_mismatch')
        need(plan['execution_budget'] is None and plan['execution_authorized'] is False, 'root_execution_authorized')
        if plan['method'] == 'R':
            need(counts[key] == 0 and plan['complete_input_tokens'] == plan['actual_output_tokens'] == 0, 'R_model_work')
        else:
            need(counts[key] <= 17 and failures[key] == 2 and stages.get(key, [])[-1:] == ['final_submit'], 'trace_slots_or_repairs_missing')
            need(roles.get(key) == semantic_roles and profiles.get(key, set()) == set(plan.get('processed', [])), 'roles_or_profiles_missing')
            need(caps[key] == plan['sum_requested_output_caps'] and plan['dynamic_budget_admission'] is None, 'invented_dynamic_admission')
        processed = plan.get('processed', [])
        need(len(processed) <= 64 and len(processed) == len(set(processed)), 'candidate_prefix_mismatch')
        steps = plan.get('steps', [])
        need([s['candidate_id'] for s in steps if s['operation'] == 'assess_current'] == processed, 'missing_item_assessment')
        need(all(s.get('candidate_id') in processed or s.get('candidate_id') is None for s in steps), 'unrequested_tail_evidence')
        need(sum(s['usage_delta']['logical_tools'] for s in steps) == plan.get('planned_cold_usage', {}).get('logical_tools')
            and sum(s['usage_delta']['physical_tools'] for s in steps) == plan.get('planned_cold_usage', {}).get('physical_tools'), 'item_metering_mismatch')
        need(plan['budget_candidate']['final_reserve']['model_calls'] == (0 if plan['method'] == 'R' else 1)
            and plan['budget_candidate']['final_reserve']['logical_tools'] == 1, 'final_reserve_mismatch')
    need(sum(counts.values()) == coverage['N'] <= 108800 and len(objects) == coverage['U'] <= coverage['N'], 'N_U_mismatch')
    need(set(objects_info) == objects, 'unreferenced_objects')
    need((original_w, original_p, unique_w, unique_p) == tuple(coverage[k] for k in
        ('original_wire_bytes', 'original_count_payload_bytes', 'unique_wire_bytes', 'unique_count_payload_bytes')), 'byte_totals_mismatch')
    need(coverage['complete_input_tokens'] is None and coverage['actual_output_tokens'] is None
        and coverage['actual_generation_cost_microusd'] is None, 'invented_capacity_or_fee')
    need(catalog['complete'] is True and coverage['complete'] is True and not coverage['reasons'], 'catalog_incomplete')
    if protected:
        before = json_file(protected)
        need(before['base'] == BASE and before['files'] == protection(), 'protected_files_changed')
    stored = sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
    return {'schema_version': 't0-delivery-check-0.1.0', 'complete': not errors, 'errors': errors,
        'scope': auth['scope'], 'plans': len(plans), 'expected_plans': len(expected), 'N': sum(counts.values()), 'U': len(objects),
        'by_method': dict(Counter(p['method'] for p in plans)), 'original_wire_bytes': original_w,
        'original_count_payload_bytes': original_p, 'unique_wire_bytes': unique_w, 'unique_count_payload_bytes': unique_p,
        'stored_bytes_before_this_check_record': stored, 'protected_files': len(json_file(protected)['files']) if protected else None,
        'full_action_chain_replays': 0, 'complete_input_tokens': None, 'actual_output_tokens': None,
        'provider_api_calls': {'count': 0, 'generate': 0, 'other': 0}, 'capacity_judgment': 'not_performed'}


def check_pilot(auth, directory):
    package = pilot_authorization(auth)
    public = auth['scope'] == 'public_catalog_test'
    if not public and os.environ.get('THESIS_RECOVERY_STAGE') != 'G1':
        raise ValueError('pilot_check_stage_not_authorized')
    ref = auth['source_receipt']
    if (not isinstance(ref, dict) or not project_path(ref['path']).is_relative_to(project_path(package['output_roots'][0 if public else 1]))
            or not str(ref['path']).endswith('.json') or not 0 < ref['bytes'] <= 16 * 1024**2):
        raise ValueError('pilot_receipt_path_not_allowed')
    if file_info(ref['path']) != {k: ref[k] for k in ('bytes', 'sha256')}:
        raise ValueError('pilot_receipt_changed')
    receipt = json_file(ref['path'])
    if (receipt['authorization_binding'] != sha(canonical({k: v for k, v in auth.items() if k != 'source_receipt'}))
            or receipt.get('complete') is not True or receipt.get('schema_version') != 't0-recovery-pilot-receipt-0.1.0'
            or set(receipt['source_sha256']) != set(PILOT_FILES)
            or any(file_info(name)['sha256'] != expected for name, expected in receipt['source_sha256'].items())):
        raise ValueError('pilot_receipt_binding_mismatch')
    if ((len(receipt['pilot_roots']) != 1 or receipt['pilot_roots'] != receipt['selected_roots']) if public else
            (len(set(receipt['selected_roots'])) != 320 or len(set(receipt['pilot_roots'])) != 4
            or not set(receipt['pilot_roots']) <= set(receipt['selected_roots']) or set(receipt['views']) != set(VIEWS))):
        raise ValueError('pilot_selection_mismatch')
    key = project_path(auth['sources']['identity_key']['path'])
    if receipt['identity_key_stamp'] != {'bytes': key.stat().st_size, 'mtime_ns': key.stat().st_mtime_ns}:
        raise ValueError('pilot_identity_source_changed')
    for role, source in auth['sources'].items():
        if role != 'identity_key' and file_info(source['path']) != {k: source[k] for k in ('bytes', 'sha256')}:
            raise ValueError('pilot_source_changed')
    inputs = pilot_inputs(auth, receipt)
    initial_hashes = set()
    roots = {r['root_task_id']: r for r in inputs['model_roots']}
    for view in inputs['view_bindings']:
        quality = view['arm'] == 'quality'
        payload = {**roots[view['root_task_id']], 'session_handle': 'synthetic-session:' + sha(canonical([view['root_task_id'], view['label']])),
            'K': 10, 'verify_at_ms': 1791417600000, 'request': {'source': 'experiment_design',
                'text': view['request']['design_text'], 'necessary_clauses': view['request']['necessary_clauses']},
            'source_disclosure': 'SIM', 'alpha': .5 if quality else 1, 'beta': [.25, .5, .25],
            'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'] if quality else [],
                'weights': {'retail_stock': 1} if quality else {}},
            'tool_version': 'pending', 'model_version': 'pending', 'prompt_version': 'pending'}
        payload['H'] = payload.pop('history')
        payload.pop('input_fingerprint', None)
        payload['input_fingerprint'] = sha(canonical(payload))
        initial_hashes.add(sha(canonical(payload)))
    receipt['_initial_hashes'] = initial_hashes
    report = check(auth, directory, None, pilot=receipt)
    if report['complete']:
        report['dependency_templates_verified'] = pilot_dependencies(auth, receipt, directory, inputs)
        if not public:
            report['legacy_comparison'] = pilot_legacy_comparison(receipt, directory)
            if receipt['protection'] != protection():
                raise ValueError('protected_files_changed')
            report['protected_files'] = len(receipt['protection'])
            prefix = json_file(directory / 'checks/pilot-prefix.json')
            checkpoint = json_file(directory / 'checkpoint.json')
            if len(prefix['committed']) != 3 or checkpoint['committed'][:3] != prefix['committed'] or len(checkpoint['committed']) != 120:
                raise ValueError('pilot_resume_prefix_changed')
            reproduction = json_file(directory / 'checks/reproduction.json')
            if (reproduction['complete'] is not True or reproduction['match'] is not True or reproduction['recomputed_N'] != report['N']
                    or reproduction['recomputed_U'] != report['U'] or reproduction['changed_components']
                    or reproduction['recomputed_catalog_sha256'] != file_info(directory / 'catalog.json')['sha256']):
                raise ValueError('pilot_reproduction_not_verified')
            for name, before in receipt['legacy']['metadata'].items():
                path = project_path(auth['old_catalog']['path']).parent / name
                if (path.stat().st_size, path.stat().st_mtime_ns) != (before['bytes'], before['mtime_ns']):
                    raise ValueError('original_metadata_changed')
    report.update(status=('PUBLIC_recovery_pilot_verified_only' if public else 'T0_A_recovery_pilot_verified_only')
                  if report['complete'] else 'T0_A_incomplete', full_catalog_accepted=False,
                  original_T0_status='T0_A_incomplete')
    return report


def pilot_inputs(auth, receipt):
    sources, selected = auth['sources'], set(receipt['pilot_roots'])
    metadata = {}
    for role in ('model_roots', 'model_candidates', 'view_bindings'):
        ref = sources[role]
        found = []
        with project_path(ref['path']).open('rb') as stream:
            for item in receipt['source_index']['intervals']:
                if item['component'] == ref and item['root_task_id'] in selected:
                    stream.seek(item['offset'])
                    raw = stream.read(item['bytes'])
                    row = json.loads(raw)
                    if row['root_task_id'] != item['root_task_id']:
                        raise ValueError('pilot_source_interval_mismatch')
                    found.append(row)
        metadata[role] = found
    return metadata


def pilot_legacy_comparison(receipt, directory):
    plans = {(r['root_task_id'], r['view_label'], r['method'], r['repeat']): r for r in rows(directory / 'roots.jsonl')}
    requests = {}
    for row in rows(directory / 'requests.jsonl'):
        key = (row['root_task_id'], row['view_label'], row['method'], 1)
        requests.setdefault(key, []).append({'prepared_id': row['prepared_id'], 'wire_bytes': row['wire_bytes'],
            'count_payload_bytes': row['count_payload_bytes'], 'request_sha256': sha(canonical(row))})
    complete, partial, compared = 0, 0, 0
    for old in receipt['legacy']['plans']:
        key = tuple(old['key'])
        actual = requests.get(key, [])
        if old['marked_complete']:
            if old['plan_sha256'] != sha(canonical(plans[key])) or old['requests'] != actual:
                raise ValueError('pilot_legacy_complete_plan_mismatch')
            complete += 1
        else:
            if actual[:len(old['requests'])] != old['requests']:
                raise ValueError('pilot_legacy_partial_prefix_mismatch')
            partial += 1
        compared += len(old['requests'])
    return {'marked_complete_metadata_matched': complete, 'partial_prefix_matched': partial,
        'old_request_id_W_P_and_semantic_metadata_matched': compared, 'old_object_bodies_admitted': 0,
        'comparison_limit': 'new decoded W/P verified against old metadata identities and lengths; old bodies were not read or accepted'}


def pilot_probe_equivalent(actual, planned, namespace):
    """Compare full probe bodies with a one-to-one renaming of receipt capabilities."""
    bindings, targets = {}, set()
    def same(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            if len(a) != len(b):
                return False
            common = sorted(set(a) & set(b), key=lambda k: (k == 'acquired', k != 'operations', k))
            if not all(same(a[k], b[k]) for k in common):
                return False
            return all(bindings.get(k, k) in b and same(v, b[bindings.get(k, k)]) for k, v in a.items() if k not in common)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
        if isinstance(a, str) and isinstance(b, str) and b.startswith(namespace):
            if a not in bindings:
                if b in targets:
                    return False
                bindings[a] = b
                targets.add(b)
            return bindings[a] == b
        return a == b
    return same(actual, planned)


def pilot_dependencies(auth, receipt, directory, metadata):
    """Bind template scope, probe lineage and every returned fact body to authenticated sources."""
    views = metadata['view_bindings']
    allowed_scopes = {sha(canonical([v['label'], v['snapshot'], v['principal_id'], v['verify_at_ms'], v['request']])) for v in views}
    file_cache, template_scopes, probes = {}, {}, {}
    checkpoint = json_file(directory / 'checkpoint.json')
    if checkpoint['source_receipt'] != auth['source_receipt'] or checkpoint['source_sha256'] != receipt['source_sha256']:
        raise ValueError('pilot_checkpoint_binding_mismatch')
    for item in checkpoint['committed']:
        if not re.fullmatch(r'staging/[0-9a-f]{64}-[0-2]', item['path']):
            raise ValueError('pilot_checkpoint_path_not_allowed')
        leaf = project_path(directory / item['path'])
        if (file_info(leaf / 'checks/probes.jsonl') != item['probes'] or file_info(leaf / 'commit.json') != item['commit']
                or file_info(leaf / 'catalog.json') != item['catalog']):
            raise ValueError('pilot_committed_probe_changed')
        for probe in rows(leaf / 'checks/probes.jsonl'):
            if probe['template_id'] in probes:
                raise ValueError('pilot_duplicate_committed_probe')
            probes[probe['template_id']] = probe
    old_root = Path('C:/Users/Kane/Documents/CodexProject/Thesis')
    def locator(value):
        path = Path(value)
        return project_path(PROJECT / path.relative_to(old_root) if path.is_relative_to(old_root) else path)
    def source_bytes(path, expected):
        key = (str(path), expected['sha256'])
        if key not in file_cache:
            raw = project_path(path).read_bytes()
            if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
                raise ValueError('pilot_dependency_source_mismatch')
            file_cache[key] = raw
        return file_cache[key]
    for template in rows(directory / 'dependencies.jsonl'):
        scope, tid = template['scope'], template['template_id']
        if (len(scope) != 7 or sha(canonical(scope)) != tid or tid in template_scopes
                or sha(canonical(scope[:5])) not in allowed_scopes):
            raise ValueError('pilot_dependency_binding_mismatch')
        template_scopes[tid] = scope
        probe = probes.get(tid)
        if not probe or not pilot_probe_equivalent({'operations': probe['operations'], 'acquired': probe['audit']['acquired']},
                {k: template[k] for k in ('operations', 'acquired')}, 'synthetic-template:' + tid + ':'):
            raise ValueError('pilot_probe_template_mismatch')
        snapshot_path = locator(scope[1]['path'])
        snapshot_raw = source_bytes(snapshot_path, scope[1])
        snapshot = json.loads(snapshot_raw)
        allowed = {snapshot_path.relative_to(PROJECT).as_posix(): scope[1]}
        allowed.update({(snapshot_path.parent / name).relative_to(PROJECT).as_posix(): value
                        for name, value in snapshot['components'].items()})
        def visit(value):
            if isinstance(value, dict):
                if 'raw_utf8' in value and isinstance(value.get('source'), dict) and 'component_path' in value['source']:
                    source = value['source']
                    name = source['component_path']
                    if name not in allowed:
                        raise ValueError('pilot_dependency_source_mismatch')
                    expected = allowed[name]
                    if source['component_sha256'] != expected['sha256'] or source['bytes'] != expected['bytes']:
                        raise ValueError('pilot_dependency_source_mismatch')
                    raw = source_bytes(project_path(name), expected)
                    body = value['raw_utf8'].encode()
                    if 'offset' in source:
                        offset = source['offset']
                        valid = (type(offset) is int and offset >= 0 and raw[offset:offset + len(body)] == body
                            and (offset == 0 or raw[offset - 1:offset] == b'\n')
                            and raw[:offset].count(b'\n') + 1 == source['line'])
                    else:
                        valid = raw == body
                    if not valid:
                        raise ValueError('pilot_dependency_source_mismatch')
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(template)
        operations = template['operations']
        if (not operations or operations[0]['operation'] != 'list_evidence'
                or operations[-1]['operation'] != 'assess_current'
                or any(row['result']['status'] != 'ok' for row in operations)
                or not operations[-1]['result']['assessment']['advance_allowed']):
            raise ValueError('pilot_dependency_operations_mismatch')
    roots = {r['root_task_id']: r for r in metadata['model_roots']}
    candidates = {r['root_task_id']: r for r in metadata['model_candidates']}
    referenced = set()
    for plan in rows(directory / 'roots.jsonl'):
        root, candidate = roots[plan['root_task_id']], candidates[plan['root_task_id']]
        if (plan['C_sha256'] != sha(canonical(candidate['C'])) or plan['C_count'] != len(candidate['C'])
                or plan['H_sha256'] != sha(canonical(root['history']))
                or plan['base_scores_sha256'] != sha(canonical(list(zip(candidate['C'], candidate['b']))))):
            raise ValueError('pilot_projection_binding_mismatch')
        refs = plan['dependency_refs']
        if len(refs) != len(plan['processed']):
            raise ValueError('pilot_dependency_binding_mismatch')
        for tid, parent in zip(refs, plan['processed']):
            scope = template_scopes.get(tid)
            position = candidate['C'].index(parent)
            if (not scope or scope[0] != plan['view_label'] or scope[5] != parent
                    or scope[6] != candidate['batches'][position]):
                raise ValueError('pilot_dependency_binding_mismatch')
            referenced.add(tid)
    if referenced != set(template_scopes):
        raise ValueError('pilot_dependency_binding_mismatch')
    if set(probes) != set(template_scopes):
        raise ValueError('pilot_orphan_probe')
    return len(template_scopes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('snapshot', 'check', 'check-objects', 'check-pilot'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--authorization')
    parser.add_argument('--catalog')
    parser.add_argument('--protection')
    args = parser.parse_args()
    output = project_path(args.output)
    if os.environ.get('THESIS_RECOVERY_PILOT_PACKAGE'):
        root = project_path(json_file(PILOT_CONTROL)['output_roots'][1 if os.environ.get('THESIS_RESOURCE_DOMAIN') == 't0' else 0])
        if output == root or not output.is_relative_to(root):
            raise SystemExit('pilot_output_not_allowed')
    allowed = (PROJECT / 'data/ticket12-t0', PROJECT / '.tmp/ticket12-t0')
    if not any(output.is_relative_to(p) for p in allowed) or output.exists():
        raise SystemExit('new_output_in_T0_directory_required')
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.operation == 'snapshot':
            report = pilot_snapshot(json_file(t0_path(args.authorization))) if args.authorization else {
                'base': BASE, 'files': protection(), 'complete': True}
        elif args.operation == 'check-objects':
            report = check_objects(t0_path(args.catalog))
        elif args.operation == 'check-pilot':
            report = check_pilot(json_file(t0_path(args.authorization)), t0_path(args.catalog))
        else:
            authorization = t0_path(args.authorization)
            if not re.fullmatch('authorization(?:-[a-z0-9-]+)?\\.json', authorization.name):
                raise ValueError('authorization_path_not_allowed')
            catalog = t0_path(args.catalog)
            protected = t0_path(args.protection) if args.protection else None
            if protected and not re.fullmatch('protection(?:-[a-z0-9-]+)?\\.json', protected.name):
                raise ValueError('protection_path_not_allowed')
            report = check(json_file(authorization), catalog, protected)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        report = {'complete': False, 'errors': ['delivery_check_incomplete', type(exc).__name__, str(exc)]}
    output.write_bytes(canonical(report) + b'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('files', 'source_index', 'selected_roots', 'source_sha256',
        'legacy', 'protection', 'source_stamps')}, ensure_ascii=False, sort_keys=True))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
