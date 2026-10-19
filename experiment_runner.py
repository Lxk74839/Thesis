"""Frozen reference-only test100 plan and bounded public-fixture dispatch."""
import hashlib
import json
import os
from pathlib import Path
import re

from evidence_access import PROJECT, digest, encoded

SCOPE = 'ticket12-test100-on-demand-0.1.0'
ORIGINAL = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2')
LABELS = tuple(f'V{i:02d}' for i in range(16)) + ('Q1', 'Q2')
UNBOUND = dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget'))
AUDIT = PROJECT / 'data/recommendation-runtime-audit/ticket12-100x18'
PUBLIC = PROJECT / '.tmp/recommendation-runtime'


def _path(value):
    path = Path(value).absolute()
    if '..' in path.parts or not path.is_relative_to(PROJECT):
        raise ValueError('outside_project')
    if any(p.exists() and (p.is_symlink() or p.is_junction()) for p in (path, *path.parents)):
        raise ValueError('reparse_path')
    return path


def _json(ref):
    raw = _path(ref['path']).read_bytes()
    if digest(raw) != ref['sha256'] or len(raw) != ref.get('bytes', len(raw)):
        raise ValueError('source_binding_mismatch')
    return json.loads(raw)


def _scan(ref):
    path, sha, offset = _path(ref['path']), hashlib.sha256(), 0
    with path.open('rb') as stream:
        for line, raw in enumerate(stream, 1):
            sha.update(raw)
            yield json.loads(raw), {'path': path.relative_to(PROJECT).as_posix(), 'line': line,
                'offset': offset, 'bytes': len(raw), 'sha256': digest(raw)}
            offset += len(raw)
    if sha.hexdigest() != ref['sha256'] or offset != ref.get('bytes', offset):
        raise ValueError('source_binding_mismatch')


def _write(path, rows):
    raw = b''.join(encoded(row) + b'\n' for row in rows)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'sha256': digest(raw), 'bytes': len(raw), 'records': len(rows)}


def accepted_sources():
    """Resolve only the source records pinned by the human-authorized package."""
    package_path = PROJECT / '.scratch/ticket12-budget-20261018/on-demand-package-20261019.json'
    raw = package_path.read_bytes()
    if digest(raw) != '2c785971e00379bd51fbc15a3be0b14cc346f14b5dfb65ab7bd847aad92eaee3':
        raise ValueError('authorization_binding_mismatch')
    package = json.loads(raw)
    pins = {ref['path']: ref for ref in package['protected']}
    names = {'split': 'records/splits/grain-A-1.1.15-user-split-1.0.0',
        'preference': 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1',
        'joint': 'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0',
        'scenarios': 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0'}
    authority = [pins[name + suffix] for role, name in names.items()
                 for suffix in (('-acceptance.json',) if role == 'scenarios' else ('.json', '-acceptance.json'))]
    for ref in authority:
        _json(ref)
    pref, joint = (_json(pins[names[role] + '.json']) for role in ('preference', 'joint'))
    joint_accept = _json(pins[names['joint'] + '-acceptance.json'])
    pref_accept = _json(pins[names['preference'] + '-acceptance.json'])
    if (joint_accept['status'] != 'accepted_joint_preparation_component_only'
            or pref_accept['status'] != 'accepted_ticket08_preference_trial_api_only'
            or pref_accept['component_sha256']['evaluation'] != pref['components']['evaluation']['sha256']):
        raise ValueError('unaccepted_source')
    return {'scope': 'accepted_test_pool', 'authority': authority,
        'cohort': pref['components']['evaluation'],
        **{name: joint['components'][source] for name, source in
           (('roots', 'model/roots.jsonl'), ('candidates', 'model/candidates.jsonl'),
            ('view_bindings', 'view-bindings.jsonl'), ('catalog', 'model/catalog.jsonl'),
            ('candidate_map', 'candidate-map.jsonl'))},
        'scenarios': pins[names['scenarios'] + '-acceptance.json']}


def build_plan(source_refs, seed, output_root):
    """Freeze exactly 100 test accounts and references, without running recommendations."""
    if seed != '20261019' or source_refs['scope'] not in ('public_fixture', 'accepted_test_pool'):
        raise ValueError('unapproved_sampling_rule')
    public = source_refs['scope'] == 'public_fixture'
    if not public and source_refs != accepted_sources():
        raise ValueError('unapproved_real_sources')
    output = _path(output_root)
    if not output.is_relative_to(PUBLIC if public else AUDIT):
        raise ValueError('plan_output_scope_mismatch')
    if public and any(not _path(ref['path']).is_relative_to(PUBLIC) for key, ref in source_refs.items()
                      if isinstance(ref, dict) and 'path' in ref):
        raise ValueError('fixture_source_scope_mismatch')
    cohort = {}
    for row, _ in _scan(source_refs['cohort']):
        key, split = row['task_id'], row['split']
        if key in cohort or not re.fullmatch('[0-9a-f]{64}', key) or split not in ('dev', 'test'):
            raise ValueError('invalid_cohort')
        cohort[key] = split
    tests = [key for key in cohort if cohort[key] == 'test']
    if len(cohort) != 1603 or len(tests) != 1283:
        raise ValueError('invalid_cohort_counts')
    order = sorted(tests, key=lambda key: (hashlib.sha256(
        b'Thesis|ticket12|test100|v1\0' + seed.encode() + b'\0' + key.encode('ascii')).digest(), key.encode('ascii')))
    users = [{'selection_rank': i + 1, 'root_task_id': key, 'selection_digest': hashlib.sha256(
        b'Thesis|ticket12|test100|v1\0' + seed.encode() + b'\0' + key.encode('ascii')).hexdigest()}
        for i, key in enumerate(order[:100])]
    selected = {u['root_task_id'] for u in users}
    roots, all_roots = {}, set()
    for row, ref in _scan(source_refs['roots']):
        key = row['root_task_id']
        if key in all_roots:
            raise ValueError('duplicate_root')
        all_roots.add(key)
        if key in selected:
            roots[key] = {'root_task_id': key, 'root_ref': ref,
                **{k: row[k] for k in ('C_sha256', 'H_sha256', 'base_scores_sha256')}}
    if all_roots != set(cohort):
        raise ValueError('root_cohort_mismatch')
    candidates = set()
    for row, ref in _scan(source_refs['candidates']):
        key = row['root_task_id']
        if key in candidates:
            raise ValueError('duplicate_candidates')
        candidates.add(key)
        if key in selected:
            roots[key]['candidate_ref'] = ref
    if candidates != all_roots:
        raise ValueError('candidate_root_mismatch')
    old, scenes = {}, {}
    for row, ref in _scan(source_refs['view_bindings']):
        key, label = row['root_task_id'], row['label']
        if key not in selected:
            continue
        if label not in ORIGINAL or (key, label) in old:
            raise ValueError('invalid_existing_view_binding')
        if (row['request_profile_id'] != 'R1_AND_R5_SIM_Q1_ON_SALE'
                or row['principal_id'] != 'SIM-VERIFIER' or row['verify_at_ms'] != 1791417600000):
            raise ValueError('request_binding_mismatch')
        old[key, label] = ref
        scene = {k: row[k] for k in ('label', 'view_id', 'snapshot', 'snapshot_id', 'arm')}
        if label in scenes and scenes[label] != scene:
            raise ValueError('inconsistent_scene')
        scenes[label] = scene
    if set(old) != {(key, label) for key in selected for label in ORIGINAL}:
        raise ValueError('missing_existing_view_binding')
    scenario = _json(source_refs['scenarios'])
    for i in range(16):
        label = f'V{i:02d}'
        view_id = 'q_' + digest(b'Thesis|ticket11|view|v1\0' + b'20261015\0' + f'{i:02d}'.encode())
        snapshot = {k: scenario['components']['views/' + view_id + '/snapshot.json'][k]
                    for k in ('path', 'bytes', 'sha256')}
        snap = _json(snapshot)
        scene = {'label': label, 'view_id': view_id, 'snapshot': snapshot,
                 'snapshot_id': snap['snapshot_id'], 'arm': 'necessary'}
        if label in scenes and scenes[label] != scene:
            raise ValueError('scenario_binding_mismatch')
        scenes[label] = scene
    for label in ('Q1', 'Q2'):
        if _json(scenes[label]['snapshot'])['snapshot_id'] != scenes[label]['snapshot_id']:
            raise ValueError('quality_binding_mismatch')
    bindings, tasks = [], []
    for user in users:
        key = user['root_task_id']
        for label in LABELS:
            view = scenes[label]['view_id']
            identity = digest(encoded([SCOPE, key, view]))
            binding = {'binding_id': identity, 'root_task_id': key, 'view_id': view}
            if (key, label) in old:
                binding['existing_binding_ref'] = old[key, label]
            bindings.append(binding)
            for method in (('M',) if label.startswith('Q') else ('R', 'S', 'M')):
                tasks.append({'task_key': digest(encoded([SCOPE, key, view, method, 1])),
                    'binding_id': identity, 'method': method, 'repeat': 1, 'uses_model': method != 'R'})
    if output.exists() or output.with_name(output.name + '.pending').exists():
        raise ValueError('plan_output_exists')
    staging = output.with_name(output.name + '.pending')
    staging.mkdir(parents=True)
    files = {'sample-users.jsonl': users, 'root-references.jsonl': [roots[u['root_task_id']] for u in users],
        'scenes.jsonl': [scenes[label] for label in LABELS], 'user-scenarios.jsonl': bindings, 'tasks.jsonl': tasks}
    components = {name: _write(staging / name, rows) for name, rows in files.items()}
    plan = {'schema_version': SCOPE, 'source_scope': source_refs['scope'], 'seed': seed,
        'sampling_rule': 'test100-sha256-order-0.1.0', 'test_pool_count': 1283,
        'test_pool_sha256': digest(encoded(sorted(tests))), 'sources': source_refs, 'components': components,
        'counts': {'users': 100, 'development_overlap': 0, 'scenarios': 18, 'bindings': 1800,
                   'tasks': 5000, 'model_tasks': 3400}, 'model_binding': UNBOUND.copy(),
        'execution_authorized': False, 'recommendation_runs': 0, 'provider_requests_sent': 0}
    plan['plan_id'] = digest(encoded(plan))
    _write(staging / 'plan.json', [plan])
    output.parent.mkdir(parents=True, exist_ok=True)
    os.rename(staging, output)
    return plan


def run_task(plan, task_key, *, runtime=None, output_root=None):
    """Dispatch only public handwritten runtimes; real test100 remains preparation-only."""
    directory = _path(plan)
    manifest = json.loads((directory / 'plan.json').read_bytes())
    if (manifest['schema_version'] != SCOPE or manifest['plan_id'] != digest(encoded(
            {k: v for k, v in manifest.items() if k != 'plan_id'}))):
        raise ValueError('invalid_plan')
    rows = {}
    for name in ('tasks.jsonl', 'user-scenarios.jsonl', 'scenes.jsonl'):
        path = _path(directory / name)
        rows[name] = [json.loads(line) for line in _json_lines(path, manifest['components'][name])]
    tasks = [row for row in rows['tasks.jsonl'] if row['task_key'] == task_key]
    if len(tasks) != 1:
        raise ValueError('unknown_or_duplicate_task')
    task = tasks[0]
    if manifest['source_scope'] != 'public_fixture' or runtime is None:
        return {'terminal': 'configuration_required', 'task_key': task_key,
                'missing': [k for k, v in manifest['model_binding'].items() if v is None],
                'provider_requests_sent': 0}
    from recommendation_runner import RecommendationRun
    if not isinstance(runtime, RecommendationRun):
        raise ValueError('invalid_public_runtime')
    binding = next(row for row in rows['user-scenarios.jsonl'] if row['binding_id'] == task['binding_id'])
    scene = next(row for row in rows['scenes.jsonl'] if row['view_id'] == binding['view_id'])
    output = _path(output_root)
    if (not directory.is_relative_to(PUBLIC) or not output.is_relative_to(PUBLIC)
            or output != runtime.output_root or runtime.binding['execution_kind'] != 'on_demand_public'
            or not binding['root_task_id'].startswith('PUBLIC-')
            or any(runtime.binding[k] != v for k, v in
                   (('root_task_id', binding['root_task_id']), ('method', task['method']),
                    ('snapshot_id', scene['snapshot_id'])))):
        raise ValueError('public_task_binding_mismatch')
    checkpoint = output / 'task.json'
    if checkpoint.exists():
        result = json.loads(checkpoint.read_bytes())
        if result['plan_id'] != manifest['plan_id'] or result['task_key'] != task_key:
            raise ValueError('checkpoint_binding_mismatch')
        return result
    intent = output / 'task.intent.json'
    if intent.exists():
        return {'terminal': 'unresolved_attempt', 'task_key': task_key, 'provider_requests_sent': 0}
    _write(intent, [{'task_key': task_key, 'plan_id': manifest['plan_id']}])
    observed = runtime.run()
    result = {'task_key': task_key, 'plan_id': manifest['plan_id'], 'run_id': runtime.binding['run_id'],
        'terminal': observed['terminal'], 'reason': observed['reason'], 'delivered': observed['delivered'],
        'usage': observed['budget']['usage'], 'provider_requests_sent': 0,
        'audit_path': observed['audit_path'], 'publication_path': observed['publication_path']}
    _write(checkpoint, [result])
    return result


def _json_lines(path, expected):
    raw = path.read_bytes()
    if digest(raw) != expected['sha256'] or len(raw) != expected['bytes']:
        raise ValueError('plan_component_mismatch')
    return raw.splitlines()


if __name__ == '__main__':
    import sys
    if sys.argv[1:] != ['build']:
        raise SystemExit('usage: experiment_runner.py build')
    result = build_plan(accepted_sources(), '20261019', AUDIT / 'plan')
    print(json.dumps({'status': 'frozen_references_only', 'plan_id': result['plan_id'],
                      'counts': result['counts'], 'provider_requests_sent': 0}))
