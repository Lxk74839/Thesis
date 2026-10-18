"""Independent T0-A artifact/protection checker. Standard library only; no production imports."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

PROJECT = Path(__file__).resolve().parents[3]
BASE = '88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a'
MODEL = 'gpt-5.4-mini-2026-03-17'
VIEWS = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2')
MUTABLE_BASE = {'recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
    '.scratch/ticket12-budget-20261018/diagnostics/run_check.py'}


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


def rows(path):
    with project_path(path).open('rb') as stream:
        for line in stream:
            yield json.loads(line)


def protection():
    names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE], cwd=PROJECT).decode().split('\0')
    return {name: file_info(name) for name in names if name and name not in MUTABLE_BASE}


def check(auth, directory, protected):
    errors = []
    def need(value, code):
        if not value and code not in errors:
            errors.append(code)
    catalog = json_file(directory / 'catalog.json')
    coverage = json_file(directory / 'coverage.json')
    need(catalog['schema_version'] == 'T0-request-catalog-0.1.0', 'wrong_catalog_schema')
    need(auth['api_limits'] == {'count': 0, 'generate': 0, 'other': 0} and auth['approved'] is True, 'authorization_mismatch')
    need(catalog['scope'] == auth['scope'] and catalog['candidate'] == auth['candidate'] and catalog['sources'] == auth['sources'], 'source_binding_mismatch')
    need(catalog['project_id'] == 'UNBOUND-T0-DEV-CATALOG' and catalog['external_count_ready'] is False
        and catalog['execution_budget'] is None and catalog['execution_authorized'] is False, 'execution_gate_mismatch')
    missing_objects = set()
    for name, expected in catalog['components'].items():
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
    need(len(keys) == len(set(keys)), 'duplicate_plan')
    development = auth['scope'] == 'development_catalog_only'
    expected = {(root, view, method, 1) for root in root_ids for view in VIEWS for method in ('R', 'S', 'M')} if development else set(keys)
    if development:
        need(len(root_ids) == 320 and len(expected) == 9600, 'wrong_development_scale')
        need(bool(protected), 'protection_snapshot_required')
        need(os.environ.get('THESIS_RESOURCE_DOMAIN') == 't0', 'wrong_resource_domain')
    need(set(keys) == expected and len(plans) == coverage['plans'] == coverage['expected_plans'], 'plan_coverage_mismatch')
    counts, roles, profiles, stages, failures, caps = Counter(), {}, {}, {}, Counter(), Counter()
    original_w, original_p, unique_w, unique_p = 0, 0, 0, 0
    objects, objects_info = set(), {}
    forbidden = ('user_id', 'assignment_reason', 'split_hash', 'component_path')
    for row in rows(directory / 'requests.jsonl'):
        key = (row['root_task_id'], row['view_label'], row['method'], 1)
        need(key in set(keys) and row['method'] in ('S', 'M'), 'orphan_or_R_request')
        need(row['provenance'] == 'synthetic' and row['input_tokens'] is None and row['output_tokens'] is None
            and row['cost_microusd'] is None, 'invented_usage')
        counts[key] += 1
        roles.setdefault(key, set()).add(row['semantic_role'])
        stages.setdefault(key, []).append(row['output_kind'])
        failures[key] += row['script_response']['status'] == 'format_error'
        need(row['effective_role'] == ('单智能体' if row['method'] == 'S' else row['semantic_role']), 'role_mismatch')
        pid = row['prepared_id']
        if pid in missing_objects:
            continue
        if pid not in objects_info:
            prepared = json_file(directory / 'objects' / (pid + '.json'))
            wire, payload = prepared['wire_body'], prepared['count_body']
            wb, pb = canonical(wire), canonical(payload)
            need(prepared['model_id'] == wire['model'] == MODEL and prepared['input_tokens'] is None, 'model_or_token_mismatch')
            need(wb.decode() == prepared['wire_utf8'] and pb.decode() == prepared['count_utf8'], 'incomplete_W_or_P')
            need(sha(wb) == prepared['wire_sha256'] and sha(pb) == prepared['count_payload_sha256'], 'body_digest_mismatch')
            need(len(wb) == prepared['wire_bytes'] and max(len(wb), len(pb)) <= 16 * 1024**2, 'body_limit_exceeded')
            need(payload == {k: v for k, v in wire.items() if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')}, 'wrong_count_projection')
            need(sha(canonical({k: prepared[k] for k in ('wire_sha256', 'count_payload_sha256', 'mapper_version',
                'tool_schema_sha256', 'role_schema_sha256', 'project_id')})) == pid, 'prepared_id_mismatch')
            need(prepared['role_schema_sha256'] == sha(canonical(wire['text']['format']['schema'])), 'role_schema_mismatch')
            need(wire['reasoning'] == {'effort': 'none'} and wire['parallel_tool_calls'] is False
                and wire['truncation'] == 'disabled' and wire['store'] is False and wire['stream'] is False, 'wire_setting_mismatch')
            for item in wire['input']:
                if 'role' in item:
                    try:
                        content = json.loads(item['content'])
                    except (ValueError, TypeError):
                        continue
                    if isinstance(content, dict) and 'root_task_id' in content:
                        need(content['root_task_id'] == row['root_task_id'] and 'H' in content and 'history' not in content
                            and not any(name in content for name in forbidden), 'unsafe_initial_projection')
                    if isinstance(content, dict) and isinstance(content.get('runtime'), dict):
                        runtime = content['runtime']
                        if runtime['stage'] == '农产品画像':
                            profiles.setdefault(key, set()).update(runtime['profile_candidates'])
            need(not any(('"' + name + '":') in prepared['wire_utf8'] for name in forbidden), 'host_metadata_in_wire')
            objects_info[pid] = (len(wb), len(pb), wire['max_output_tokens'])
            unique_w += len(wb)
            unique_p += len(pb)
        wb, pb, cap = objects_info[pid]
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('snapshot', 'check'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--authorization')
    parser.add_argument('--catalog')
    parser.add_argument('--protection')
    args = parser.parse_args()
    output = project_path(args.output)
    allowed = (PROJECT / 'data/ticket12-t0', PROJECT / '.tmp/ticket12-t0')
    if not any(output.is_relative_to(p) for p in allowed) or output.exists():
        raise SystemExit('new_output_in_T0_directory_required')
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = {'base': BASE, 'files': protection(), 'complete': True} if args.operation == 'snapshot' else check(
            json_file(args.authorization), project_path(args.catalog), args.protection)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        report = {'complete': False, 'errors': ['delivery_check_incomplete', type(exc).__name__]}
    output.write_bytes(canonical(report) + b'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, ensure_ascii=False, sort_keys=True))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
