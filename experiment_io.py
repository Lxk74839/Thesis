"""Read-only artifact/reference association. Stage A accepts PUBLIC evidence only."""
import copy
import json

from evidence_access import PROJECT, digest, encoded
from experiment_runner import _path, _task_plan, assemble_task
from experiment_evaluation import BINDING, ORIGINAL, SCENES


def _public_path(path):
    path = _path(path)
    if not any(path.is_relative_to(PROJECT / root) for root in (
            '.tmp/recommendation-runtime', '.tmp/experiment-evaluation')):
        raise ValueError('stage_A_real_evaluation_forbidden')
    return path


def _read(ref):
    path = _public_path(ref['path'])
    if 'offset' in ref:
        with path.open('rb') as stream:
            stream.seek(ref['offset'])
            raw = stream.read(ref['bytes'])
    else:
        raw = path.read_bytes()
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise ValueError('artifact_binding_mismatch')
    return raw


def _rows(ref):
    return [json.loads(raw) for raw in _read(ref).splitlines()]


def _execution(task, ref, plan_id, *, read_artifact=None, resolve_artifact=None, legacy_R=False):
    """Project actual artifacts without ever accepting an independent reference."""
    read, path = read_artifact or _read, resolve_artifact or _public_path
    result = json.loads(read(ref))
    if result['task_key'] != task['task_key'] or result['plan_id'] != plan_id:
        raise ValueError('execution_binding_mismatch')
    binding = {k: task[k] for k in BINDING}
    if path(ref['path']).name == 'task.intent.json' and set(result) == {'task_key', 'plan_id'}:
        return {'task_key': task['task_key'], 'binding': binding, 'started': True,
                'terminal': 'unresolved_attempt', 'usage': None}
    if result['terminal'] in ('not_started', 'configuration_required'):
        if result.get('started') is not False:
            raise ValueError('invalid_execution_state')
        return {'task_key': task['task_key'], 'binding': binding, 'started': False, 'terminal': result['terminal']}
    if result['terminal'] in ('running', 'unresolved_attempt'):
        return {'task_key': task['task_key'], 'binding': binding, 'started': True,
                'terminal': result['terminal'], 'usage': result.get('usage')}
    directory = path(ref['path']).parent
    audit_path = path(result['audit_path'])
    legacy = (legacy_R and task['method'] == 'R' and result.get('legacy_R_source') == result['audit_ref'])
    if legacy:
        directory = audit_path.parent
    if audit_path.parent != directory:
        raise ValueError('audit_scope_mismatch')
    if path(result['audit_ref']['path']) != audit_path:
        raise ValueError('audit_scope_mismatch')
    audit = json.loads(read(result['audit_ref']))
    actual = audit['binding']
    expected = binding | {'base_scores': task['base_scores']}
    if (audit['run_id'] != result['run_id'] or audit['terminal'] != result['terminal']
            or actual.get('task_key') != task['task_key']
            or any(actual.get('base_score_sha256' if k == 'base_scores_sha256' else k) != v for k, v in expected.items())):
        raise ValueError('audit_binding_mismatch')
    acquired = json.loads(read(result['acquired_ref']))
    if ((acquired != audit['evidence']['acquired'] if legacy else audit.get('acquired_ref') != result['acquired_ref'])
            or acquired['binding']['run_id'] != result['run_id']
            or any(acquired['binding'][k] != task[k] for k in ('root_task_id', 'snapshot_id', 'principal_id', 'verify_at_ms'))
            or acquired['candidate_binding'] != {'C': task['C'], 'base_scores': task['base_scores']}):
        raise ValueError('actual_A_binding_mismatch')
    success = result['terminal'] in ('released', 'valid_empty')
    proofs, assessments = acquired.get('assessments', {}), audit['assessments']
    queue = sorted(task['C'], key=lambda p: (-task['base_scores'][task['C'].index(p)], p.encode()))
    closed = {p for p, a in assessments.items() if a['assessment_status'] == 'assessed'
        and a['advance_allowed'] is True and a['completion']['enumeration_complete'] is True
        and a['completion']['attempts_settled'] is True}
    if (set(assessments) - set(task['C']) or any(proofs.get(p) != a for p, a in assessments.items())
            or audit['evidence']['acquired'].get('assessments', {}) != proofs
            or success and set(proofs) != set(assessments)
            or audit['queue'] != queue or type(audit['cursor']) is not int or not 0 <= audit['cursor'] <= len(queue)
            or not set(queue[:audit['cursor']]) <= closed
            or audit['G'] != [p for p in queue if p in closed and assessments[p]['eligible'] is True]):
        raise ValueError('actual_assessment_binding_mismatch')
    complete_C = audit['cursor'] == len(queue) and closed == set(task['C'])
    if result['terminal'] == 'valid_empty' and not complete_C:
        raise ValueError('actual_assessment_binding_mismatch')
    publication_verified = False
    if path(result['budget_ref']['path']) != directory / 'budget.jsonl':
        raise ValueError('budget_scope_mismatch')
    journal = [json.loads(raw) for raw in read(result['budget_ref']).splitlines()]
    settled = {r['reservation_id']: r for r in journal if r.get('status') in ('settled', 'unresolved')}
    closing = [r for r in journal if r.get('status') == 'reserved'
               and r.get('operation') in ('final', 'commit', 'seal_audit')]
    gate = (len(closing) == 3 and [r['operation'] for r in closing] == ['final', 'commit', 'seal_audit']
        and all(r['phase'] == 'final' and r['reservation_id'].startswith(result['run_id'] + ':')
            and settled.get(r['reservation_id'], {}).get('status') == 'settled'
            and settled[r['reservation_id']]['observation']['status'] == 'ok'
            and not settled[r['reservation_id']]['observation'].get('late') for r in closing))
    if success:
        from recommendation_runner import audit_reference_projection
        audit_receipts = audit_reference_projection(journal[1:-1]) if audit.get('acquired_ref') else journal[1:-1]
        if (not gate or journal[0].get('kind') != 'init' or journal[0]['binding'] != actual
                or audit['budget']['binding'] != actual
                or audit['budget']['receipts'] != audit_receipts
                or journal[-1] != settled[closing[-1]['reservation_id']]):
            raise ValueError('settlement_binding_mismatch')
        publication_path = path(result['publication_path'])
        if path(result['publication_ref']['path']) != publication_path:
            raise ValueError('publication_binding_mismatch')
        raw = read(result['publication_ref'])
        publication = json.loads(raw)
        publication_verified = (publication_path.parent == directory and digest(raw) == audit['publication_record_sha256']
            and publication['run_id'] == result['run_id'] and publication['terminal'] == result['terminal']
            and publication['G'] == audit['G'] and publication['A_sha256'] == digest(encoded(acquired))
            and publication['draft'] == audit['drafts'][-1] and publication['draft_sha256'] == digest(encoded(publication['draft']))
            and publication['cursor'] == audit['cursor']
            and publication['budget']['binding']['run_id'] == result['run_id']
            and publication['budget']['receipts'] == journal[1:1 + len(publication['budget']['receipts'])]
            and [r['parent_asin'] for r in publication['draft']['items']] == result['delivered'] == audit['delivered'])
        if not publication_verified:
            raise ValueError('publication_binding_mismatch')
    attempts = [m['root_reservation_id'] for m in audit['messages']]
    if legacy and (attempts or audit['budget']['usage']['model_calls'] != 0):
        raise ValueError('legacy_R_model_usage')
    model_reservations = {r['reservation_id']: r for r in journal if r.get('status') == 'reserved'
                          and isinstance(r.get('operation'), dict) and r['operation'].get('kind') == 'model'}
    if (len(attempts) != len(set(attempts)) or set(attempts) != set(model_reservations)
            or any(i not in settled for i in attempts)):
        raise ValueError('budget_attempt_binding_mismatch')
    native_usages = []
    for message in audit['messages']:
        reservation = model_reservations[message['root_reservation_id']]
        observation = settled[message['root_reservation_id']]['observation']
        for key in ('request_ref', 'response_ref'):
            if (message[key] != observation[key]
                    or path(message[key]['path']).parent != directory / 'trace'):
                raise ValueError('trace_binding_mismatch')
        request = json.loads(read(message['request_ref']))
        response = json.loads(read(message['response_ref']))
        if message['response_summary'].get('usage') != response.get('usage'):
            raise ValueError('trace_usage_mismatch')
        native_usages.append(response.get('usage') or {})
        if (request['run_id'] != result['run_id'] or request['reservation_id'] != message['root_reservation_id']
                or request['request_id'] != message['role_message_id']
                or message['response_summary'].get('request_id', message['role_message_id']) != message['role_message_id']
                or observation['status'] != message['response_summary']['status']
                or any(request[k] != reservation['operation'][k] for k in (
                    'request_id', 'role', 'output_kind', 'prepared_id', 'count_receipt_id'))):
            raise ValueError('trace_binding_mismatch')
    native = actual.get('execution_kind') == 'fourrouter_responses' and not legacy
    usages = native_usages if native else [settled[i]['usage'] for i in attempts]
    usage = {'basis': ('provider_native_fixture' if actual.get('fixture') is not None else 'provider_native')
        if native else 'no_model' if legacy else 'synthetic_fixture_units',
        'known_subtotal': {}, 'unknown_counts': {}}
    for key in ('input_tokens', 'output_tokens', 'cost_microusd'):
        values = [u.get(key) for u in usages]
        usage['known_subtotal'][key] = sum(v for v in values if v is not None)
        usage[key] = sum(values) if all(v is not None for v in values) else None
        usage['unknown_counts'][key] = sum(v is None for v in values)
    states = {p: a['evidence_state'] or 'Unassessed' for p, a in assessments.items()}
    execution = {'task_key': task['task_key'], 'binding': binding, 'started': True,
        'terminal': result['terminal'], 'delivered': result['delivered'], 'G': audit['G'],
        'cursor': audit['cursor'], 'stop_reason': audit['stop_reason'], 'assessments': states,
        'complete_C': complete_C,
        'gate_passed': gate, 'publication_verified': publication_verified, 'acquired': acquired,
        'components': audit['components'], 'usage': usage}
    if task['scene'].startswith('Q'):
        task['fusion'] = copy.deepcopy(actual['fusion'])
    return execution


def load_evaluation_inputs(plan, *, execution_index, reference_sources, read_artifact=None, resolve_artifact=None,
                           development=False):
    """Return fixed evaluation slots and observations; perform no scoring or execution."""
    read, path = read_artifact or _read, resolve_artifact or _public_path
    path(plan)
    _, manifest, rows = _task_plan(plan)
    if development:
        from p1_runtime import PILOT, PILOT_ID, PLAN_ID, D1
        if (path(plan) != PILOT or manifest.get('pilot_id') != PILOT_ID
                or manifest.get('parent_plan_id') != PLAN_ID or len(rows['tasks.jsonl']) != 8
                or [u['root_task_id'] for u in rows['sample-users.jsonl']] != [D1]
                or reference_sources['scope'] != 'accepted_development_evaluation'
                or read_artifact is None or resolve_artifact is None):
            raise ValueError('development_evaluation_binding')
    elif manifest['source_scope'] != 'public_fixture' or reference_sources['scope'] != 'public_fixture':
        raise ValueError('stage_A_real_evaluation_forbidden')
    if set(r['label'] for r in rows['scenes.jsonl']) != set(SCENES):
        raise ValueError('evaluation_requires_18_scene_slots')
    plan_id = manifest.get('plan_id', manifest.get('pilot_id'))
    tasks, observations, applicability = [], [], {}
    roots = [u['root_task_id'] for u in rows['sample-users.jsonl']]
    if len(roots) != len(set(roots)):
        raise ValueError('duplicate_evaluation_user')
    scheduled = {}
    for row in rows['tasks.jsonl']:
        relation = next(b for b in rows['user-scenarios.jsonl'] if b['binding_id'] == row['binding_id'])
        key = (relation['root_task_id'], relation['view_id'], row['method'])
        if key in scheduled:
            raise ValueError('duplicate_scheduled_task')
        scheduled[key] = row
    if set(execution_index) - {t['task_key'] for t in scheduled.values()}:
        raise ValueError('unknown_execution_key')
    preferences = [json.loads(row) for row in read(reference_sources['preference']).splitlines()]
    states = [json.loads(row) for row in read(reference_sources['joint_states']).splitlines()]
    additional = [json.loads(row) for row in read(reference_sources['scenario_states']).splitlines()]
    for root in roots:
        first = next(t for (u, _, _), t in scheduled.items() if u == root)
        assembly = assemble_task(plan, first['task_key'])
        binding = assembly['binding']
        pref = [p for p in preferences if p['root'] == root]
        if len(pref) != 1 or pref[0]['target_parent'] not in binding['C']:
            raise ValueError('preference_reference_mismatch')
        applicability[root] = {}
        for scene in rows['scenes.jsonl']:
            relation = next(b for b in rows['user-scenarios.jsonl'] if b['root_task_id'] == root and b['view_id'] == scene['view_id'])
            view_ref = relation.get('existing_binding_ref') or relation.get('request_template_ref')
            if view_ref is None:
                normal_scene = next(s for s in rows['scenes.jsonl'] if s['label'] == 'V00')
                normal = next(b for b in rows['user-scenarios.jsonl'] if b['root_task_id'] == root
                              and b['view_id'] == normal_scene['view_id'])
                view_ref = normal['existing_binding_ref']
            view = json.loads(read(view_ref))
            if 'existing_binding_ref' not in relation:
                view = view | {k: scene[k] for k in ('label', 'view_id', 'snapshot', 'snapshot_id', 'arm')}
            if (view['root_task_id'] != root or view['snapshot_id'] != scene['snapshot_id']
                    or view['snapshot'] != scene['snapshot'] or any(view[k] != assembly['root'][k]
                        for k in ('C_sha256', 'H_sha256', 'base_scores_sha256'))):
                raise ValueError('evaluation_view_binding_mismatch')
            use_joint = scene['label'] in (*ORIGINAL, 'Q1', 'Q2')
            matching = [r for r in (states if use_joint else additional) if
                r.get('view' if use_joint else 'view_id') == scene['view_id'] and
                r.get('profile' if use_joint else 'request_profile_id') == view['request_profile_id']]
            independent = {}
            for row in matching:
                parent = row['parent' if use_joint else 'parent_asin']
                if parent not in binding['C']:
                    continue
                if (parent in independent or row['snapshot' if use_joint else 'snapshot_id'] != scene['snapshot_id']
                        or row['batch' if use_joint else 'sim_batch_id'] != binding['batches'][binding['C'].index(parent)]
                        or use_joint and row['material_version'] != view['material_version']
                        or row['candidate_state'] not in ('Supported', 'Refuted', 'Pending', 'Conflict')
                        or row['eligible'] != (row['candidate_state'] == 'Supported')):
                    raise ValueError('independent_reference_binding_mismatch')
                independent[parent] = row['candidate_state']
            if set(independent) != set(binding['C']):
                raise ValueError('missing_independent_reference')
            applicability[root][scene['label']] = independent[pref[0]['target_parent']] == 'Supported'
            for method in (('M',) if scene['label'].startswith('Q') else ('R', 'S', 'M')):
                scheduled_task = scheduled.get((root, scene['view_id'], method))
                key = scheduled_task['task_key'] if scheduled_task else digest(encoded([
                    manifest['schema_version'], root, scene['view_id'], method, 1]))
                task = {'task_key': key, 'root_task_id': root, 'view_id': scene['view_id'], 'scene': scene['label'],
                    'method': method, 'repeat': 1, 'material_version': view['material_version'],
                    'snapshot_id': scene['snapshot_id'], 'request_profile_id': view['request_profile_id'],
                    'principal_id': view['principal_id'], 'verify_at_ms': view['verify_at_ms'],
                    'C': binding['C'], 'batches': binding['batches'], 'H_sha256': binding['H_sha256'],
                    'base_scores_sha256': binding['base_score_sha256'], 'base_scores': binding['base_scores'],
                    'fixed_S': reference_sources['fixed_S']}
                reference = {'binding': {k: task[k] for k in BINDING}, 'target': pref[0]['target_parent'],
                    'states': independent, 'source_ref': reference_sources['preference'] | {
                        'components': [reference_sources['preference'], reference_sources['joint_states' if use_joint else 'scenario_states']]}}
                execution = (_execution(task, execution_index[key], plan_id, read_artifact=read,
                    resolve_artifact=path, legacy_R=development) if key in execution_index else None) if scheduled_task else {
                    'task_key': key, 'binding': reference['binding'], 'started': False, 'terminal': 'not_started'}
                tasks.append(task)
                observations.append({'task': task, 'execution': execution, 'reference': reference})
    evaluation_plan = {'source_scope': 'frozen_development' if development else 'public_fixture', 'plan_id': plan_id, 'users': roots,
        'scenes': list(SCENES), 'tasks': tasks, 'applicability': applicability,
        'cohorts': {'U8': [u for u in roots if all(applicability[u][s] for s in ORIGINAL)],
                    'UQ': [u for u in roots if all(applicability[u][s] for s in ('Q1', 'Q2'))]}}
    return evaluation_plan, observations
