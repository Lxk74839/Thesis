"""Frozen reference-only test100 plan and bounded public-fixture dispatch."""
import hashlib
import copy
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


def run_task(plan, task_key, *, runtime=None, output_root=None, execution_record=None):
    """Dispatch only public handwritten runtimes; real test100 remains preparation-only."""
    directory = _path(plan)
    assembly = None
    if execution_record is not None or (directory / 'manifest.json').exists():
        assembly = assemble_task(plan, task_key, execution_record=execution_record)
        if assembly['status'] != 'assembled':
            return {k: assembly[k] for k in ('task_key', 'plan_id', 'terminal', 'missing', 'started', 'provider_requests_sent')}
        if runtime is None:
            return {'task_key': task_key, 'terminal': 'configuration_required', 'started': False,
                    'missing': ['public_runtime'], 'provider_requests_sent': 0}
        if any(runtime.binding.get(k) != v for k, v in assembly['binding'].items()):
            raise ValueError('assembled_runtime_binding_mismatch')
        if (runtime.budget.limits != execution_record.get('limits')
                or runtime.budget.final_reserve != execution_record.get('final_reserve')):
            raise ValueError('assembled_runtime_budget_mismatch')
        if (runtime.initial_messages != assembly['initial_messages']
                or runtime.evidence.source.snapshot_ref != assembly['snapshot_ref']):
            raise ValueError('assembled_runtime_source_mismatch')
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
        'started': True, 'terminal': observed['terminal'], 'reason': observed['reason'], 'delivered': observed['delivered'],
        'usage': observed['budget']['usage'], 'provider_requests_sent': 0,
        'audit_path': observed['audit_path'], 'publication_path': observed['publication_path']}
    if 'acquired_ref' in observed:
        result['acquired_ref'] = observed['acquired_ref']
    for name, path in (('audit_ref', observed['audit_path']), ('publication_ref', observed['publication_path']),
                       ('budget_ref', output / 'budget.jsonl')):
        if path is not None:
            raw = _path(path).read_bytes()
            result[name] = {'path': _path(path).relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}
    _write(checkpoint, [result])
    return result


def _json_lines(path, expected):
    raw = path.read_bytes()
    if digest(raw) != expected['sha256'] or len(raw) != expected['bytes']:
        raise ValueError('plan_component_mismatch')
    return raw.splitlines()


def _task_plan(plan):
    directory = _path(plan)
    manifest = json.loads((directory / ('manifest.json' if (directory / 'manifest.json').exists() else 'plan.json')).read_bytes())
    identity = 'pilot_id' if 'pilot_id' in manifest else 'plan_id'
    if manifest[identity] != digest(encoded({k: v for k, v in manifest.items() if k != identity})):
        raise ValueError('invalid_plan')
    names = {'tasks.jsonl', 'user-scenarios.jsonl', 'scenes.jsonl', 'root-references.jsonl', 'sample-users.jsonl'}
    if set(manifest['components']) != names:
        raise ValueError('invalid_assembly_components')
    rows = {name: [json.loads(raw) for raw in _json_lines(_path(directory / name), manifest['components'][name])]
            for name in names}
    return directory, manifest, rows


def _source_row(ref):
    with _path(ref['path']).open('rb') as stream:
        stream.seek(ref.get('offset', 0))
        raw = stream.read(ref['bytes'])
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise ValueError('source_binding_mismatch')
    return json.loads(raw)


def _accepted_assembly_sources(manifest, refs, view_ref, scene, relation, task):
    sources = manifest['sources']
    if sources != accepted_sources() or any(_path(ref['path']) != _path(sources[name]['path']) for ref, name in (
            (refs['root_ref'], 'roots'), (refs['candidate_ref'], 'candidates'), (view_ref, 'view_bindings'))):
        raise ValueError('unapproved_real_sources')
    parent_ref = {'path': str(AUDIT / 'plan/plan.json'), 'bytes': 3910,
                  'sha256': 'ced63edbf099271cc9ba5282c6d4f1ee918353c9319b0e4c6bc8d4e927d25316'}
    parent = _json(parent_ref)
    frozen = [json.loads(raw) for raw in _json_lines(AUDIT / 'plan/scenes.jsonl', parent['components']['scenes.jsonl'])]
    if scene not in frozen:
        raise ValueError('unapproved_scene_source')
    if manifest['source_scope'] == 'development_pilot':
        supplied = manifest['parent_plan_ref']
        if (_path(supplied['path']) != _path(parent_ref['path']) or supplied['sha256'] != parent_ref['sha256']
                or supplied['bytes'] != parent_ref['bytes'] or manifest['parent_plan_id'] != parent['plan_id']):
            raise ValueError('parent_plan_binding_mismatch')
        proof_path = _path(manifest['membership_ref']['path'])
        if proof_path.name != 'membership.json' or not any(proof_path.is_relative_to(root) for root in (
                PUBLIC, PROJECT / 'data/recommendation-runtime-audit/ticket14-development')):
            raise ValueError('development_membership_mismatch')
        proof = _json(manifest['membership_ref'])
        member_ref = proof['membership_source_ref']
        if (proof['split'] != 'dev' or proof['root_task_id'] != relation['root_task_id']
                or proof['cohort_sha256'] != sources['cohort']['sha256']
                or _path(member_ref['path']) != _path(sources['cohort']['path'])):
            raise ValueError('development_membership_mismatch')
        frozen_D1 = (manifest.get('pilot_id') == '6353afe1bf05e4eadd56216d64bb5d29181798e29c6edf9468f9d537e10c1af1'
            and manifest['components']['tasks.jsonl']['sha256'] ==
                '079b82c266193f56248fb493e2e3080f6502b92a50088d4b2c302a5c2c34257f'
            and proof['root_task_id'] == '015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e'
            and proof.get('formal_overlap') == 0
            and proof.get('target_or_states_projected') is False)
        member = ({'split': proof['split'], 'task_id': proof['root_task_id']} if frozen_D1 else _source_row(member_ref))
        users = [json.loads(raw)['root_task_id'] for raw in _json_lines(AUDIT / 'plan/sample-users.jsonl',
                                                                 parent['components']['sample-users.jsonl'])]
        if (member['split'] != 'dev' or member['task_id'] != relation['root_task_id']
                or relation['root_task_id'] in users):
            raise ValueError('development_membership_mismatch')
    elif manifest['source_scope'] != 'accepted_test_pool' or manifest['plan_id'] != parent['plan_id']:
        raise ValueError('unapproved_assembly_scope')
    if (task['task_key'] != digest(encoded([manifest['schema_version'], relation['root_task_id'], scene['view_id'], task['method'], 1]))
            or relation['binding_id'] != digest(encoded([manifest['schema_version'], relation['root_task_id'], scene['view_id']]))):
        raise ValueError('task_identity_mismatch')


def assemble_task(plan, task_key, *, execution_record=None):
    """Read one bound safe input. Stage A never grants real execution capability."""
    from joint_access import JointSession
    directory, manifest, rows = _task_plan(plan)
    def one(name, field, value):
        found = [row for row in rows[name] if row[field] == value]
        if len(found) != 1:
            raise ValueError('unknown_or_duplicate_' + field)
        return found[0]
    task = one('tasks.jsonl', 'task_key', task_key)
    relation = one('user-scenarios.jsonl', 'binding_id', task['binding_id'])
    scene = one('scenes.jsonl', 'view_id', relation['view_id'])
    refs = one('root-references.jsonl', 'root_task_id', relation['root_task_id'])
    if manifest['model_binding'] != UNBOUND or manifest['execution_authorized'] is not False:
        raise ValueError('stage_A_model_binding_must_be_null')
    public = manifest['source_scope'] == 'public_fixture'
    if public and (not directory.is_relative_to(PUBLIC) or not relation['root_task_id'].startswith('PUBLIC-')):
        raise ValueError('fixture_source_scope_mismatch')
    sources = manifest['sources']
    view_ref = relation.get('existing_binding_ref') or relation.get('request_template_ref')
    if view_ref is None:
        normal_scene = next(row for row in rows['scenes.jsonl'] if row['label'] == 'V00')
        normal = next(row for row in rows['user-scenarios.jsonl'] if row['root_task_id'] == relation['root_task_id']
                      and row['view_id'] == normal_scene['view_id'])
        view_ref = normal['existing_binding_ref']
    used_refs = [refs['root_ref'], refs['candidate_ref'], view_ref,
                 sources['catalog'], sources['candidate_map'], scene['snapshot']]
    if public and any(not _path(ref['path']).is_relative_to(PUBLIC) for ref in used_refs):
        raise ValueError('fixture_source_scope_mismatch')
    if not public:
        _accepted_assembly_sources(manifest, refs, view_ref, scene, relation, task)
    root, candidates = _source_row(refs['root_ref']), _source_row(refs['candidate_ref'])
    view = _source_row(view_ref)
    if 'existing_binding_ref' not in relation:
        view = view | {k: scene[k] for k in ('label', 'view_id', 'snapshot', 'snapshot_id', 'arm')}
    catalog = [json.loads(line) for line in _json_lines(_path(sources['catalog']['path']), sources['catalog'])]
    mapping = [json.loads(line) for line in _json_lines(_path(sources['candidate_map']['path']), sources['candidate_map'])]
    snapshot = _json(scene['snapshot'])
    if view['principal_id'] != 'SIM-VERIFIER' or view['arm'] != scene['arm']:
        raise ValueError('permission_binding_mismatch')
    c, scores, batches = candidates['C'], candidates['b'], candidates['batches']
    hashes = {'C_sha256': digest(encoded(c)), 'H_sha256': digest(encoded(root['history'])),
              'base_scores_sha256': digest(encoded(list(zip(c, scores))))}
    if (task['method'] not in ('R', 'S', 'M') or task['repeat'] != 1 or task['uses_model'] != (task['method'] != 'R')
            or len(c) != len(set(c)) or not len(c) == len(scores) == len(batches) == len(candidates['background_statistics'])
            or any(row['root_task_id'] != relation['root_task_id'] for row in (root, candidates, view))
            or view['view_id'] != scene['view_id'] or view['snapshot'] != scene['snapshot']
            or view['snapshot_id'] != snapshot['snapshot_id'] or snapshot['snapshot_id'] != scene['snapshot_id']
            or any(row[k] != v for row in (root, refs, view) for k, v in hashes.items())
            or set(c) - {p['parent_asin'] for p in catalog}
            or any(next((m.get('sim_batch_id') for m in mapping if m['parent_asin'] == p), None) != b for p, b in zip(c, batches))):
        raise ValueError('assembly_binding_mismatch')
    safe_fields = {'schema_version', 'root_task_id', 'history', 'seen_parent_asins', 'history_cutoff_exclusive_ms',
        'catalog_version', 'score_version', 'C_sha256', 'H_sha256', 'base_scores_sha256', 'candidate_count',
        'metadata_time_basis', 'text_policy_version'}
    if set(root) - safe_fields:
        raise ValueError('unsafe_root_fields')
    initial = JointSession(root, candidates, catalog, view, 'session:' + task_key).dispatch('model_request', {})['request']['messages']
    payload = json.loads(initial[0]['content'])
    payload['H'] = payload.pop('history')
    payload.pop('input_fingerprint')
    payload['verify_at_ms'] = view['verify_at_ms']
    payload['input_fingerprint'] = digest(encoded(payload))
    initial[0]['content'] = encoded(payload).decode()
    record = execution_record or {}
    binding = {'schema_version': 'rsm-run-0.3.0', 'execution_kind': 'on_demand_public' if public else 'unbound_stage_A',
        'fixture': 'public_runtime_adapter' if public else None, 'plan_source_scope': manifest['source_scope'],
        'execution_budget': None, 'execution_authorized': False, 'run_id': record.get('run_id'),
        'root_task_id': relation['root_task_id'], 'method': task['method'], 'repeat_id': task['repeat'],
        'task_key': task_key, 'view_id': scene['view_id'], 'material_version': view['material_version'],
        'request_profile_id': view['request_profile_id'],
        'arm': scene['arm'], 'C': c, 'base_scores': scores, 'batches': batches,
        'C_sha256': hashes['C_sha256'], 'H_sha256': hashes['H_sha256'], 'base_score_sha256': hashes['base_scores_sha256'],
        'K': view['K'], 'principal_id': view['principal_id'], 'snapshot_id': scene['snapshot_id'],
        'verify_at_ms': view['verify_at_ms'], 'necessary_clauses': [v['clause_id'] if isinstance(v, dict) else v
            for v in view['request']['necessary_clauses']], 'prefix_limit': record.get('prefix_limit'),
        'fusion': record.get('fusion'), 'safe_initial_messages': initial,
        'assembled_input_sha256': digest(encoded(initial)), 'source_snapshot_ref': scene['snapshot']}
    result = {'task_key': task_key, 'plan_id': manifest.get('plan_id', manifest.get('pilot_id')),
        'source_scope': manifest['source_scope'], 'task': task, 'scene': scene, 'view': view,
        'binding': binding, 'initial_messages': initial, 'root': root, 'candidates': candidates, 'catalog': catalog,
        'snapshot_ref': scene['snapshot'], 'model_binding': copy.deepcopy(manifest['model_binding']),
        'provider_requests_sent': 0, 'started': False}
    if not public or record.get('fixture') is not True:
        return result | {'status': 'configuration_required', 'terminal': 'configuration_required',
            'missing': [k for k, v in manifest['model_binding'].items() if v is None] + ['stage_B_not_implemented']}
    missing = [k for k in ('run_id', 'limits', 'final_reserve') if not record.get(k)]
    if missing:
        return result | {'status': 'configuration_required', 'terminal': 'configuration_required', 'missing': missing}
    return result | {'status': 'assembled'}


if __name__ == '__main__':
    import sys
    if sys.argv[1:] != ['build']:
        raise SystemExit('usage: experiment_runner.py build')
    result = build_plan(accepted_sources(), '20261019', AUDIT / 'plan')
    print(json.dumps({'status': 'frozen_references_only', 'plan_id': result['plan_id'],
                      'counts': result['counts'], 'provider_requests_sent': 0}))
