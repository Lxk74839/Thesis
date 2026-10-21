"""Evaluation-only association for the eight frozen D1 pilot slots. No sender imports."""
import json
from pathlib import Path

from evidence_access import PROJECT, digest, encoded
from experiment_runner import _path, _json, _scan, _task_plan, accepted_sources

R_RUN = 'P1-D1-V00-R-R-FROZEN-RETRY-20261020'


def evaluation_directory(output, run_id):
    return output / 'evaluation' / run_id


def reference(ref):
    path = _path(ref)
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}


def read(ref):
    path = _path(ref['path'])
    if '.secrets' in path.parts:
        raise ValueError('evaluation_credentials_forbidden')
    with path.open('rb') as stream:
        stream.seek(ref.get('offset', 0))
        raw = stream.read(ref['bytes'])
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise ValueError('evaluation_source_binding')
    return raw


def store(path, value):
    with path.open('xb') as stream:
        stream.write(encoded(value) + b'\n')
    return reference(path)


def project_rows(source, target, fields, predicate):
    """Stream and verify the whole accepted source; retain only evaluation-required fields."""
    rows = 0
    with target.open('xb') as stream:
        for row, location in _scan(source):
            if predicate(row):
                stream.write(encoded({k: row[k] for k in fields} | {'source_row': location}) + b'\n')
                rows += 1
    return reference(target) | {'source': source, 'rows': rows}


def legacy_R_sidecar(target, *, run_root, task_key, plan_id, expected_files):
    """Seal actual legacy A once, without modifying its audit, publication or budget."""
    refs = {Path(r['path'].replace('\\\\', '\\')).name: r for r in expected_files}
    for name in ('audit.json', 'publication.json', 'budget.jsonl', 'attempt.json'):
        # Old records can contain doubled Windows separators; preserve the record itself.
        pinned = refs[name]
        actual = reference(run_root / name)
        if any(actual[k] != pinned[k] for k in ('bytes', 'sha256')):
            raise ValueError('legacy_R_evidence_changed')
    audit_ref = reference(run_root / 'audit.json')
    audit = json.loads(read(audit_ref))
    if (audit.get('acquired_ref') is not None or audit['binding']['method'] != 'R' or audit['binding']['task_key'] != task_key
            or audit['terminal'] != 'released' or audit['messages'] or audit['budget']['usage']['model_calls'] != 0):
        raise ValueError('legacy_R_invalid')
    acquired_ref = store(target / 'R-acquired.json', audit['evidence']['acquired'])
    result = {k: audit[k] for k in ('run_id', 'terminal', 'delivered')}
    result.update(task_key=task_key, plan_id=plan_id, started=True,
        audit_path=str(run_root / 'audit.json'), audit_ref=audit_ref, legacy_R_source=audit_ref,
        acquired_ref=acquired_ref, publication_path=str(run_root / 'publication.json'),
        publication_ref=reference(run_root / 'publication.json'), budget_ref=reference(run_root / 'budget.jsonl'))
    return store(target / 'R-result-sidecar.json', result)


def evaluate(run_id):
    from p1_runtime import PILOT, PILOT_ID, D1
    from p1_storage import P1StorageGuard
    from development_pilot import OUTPUT, CONTROL, storage_headroom, METADATA_RESERVE
    from experiment_io import load_evaluation_inputs
    from experiment_evaluation import score_task, summarize

    _, manifest, rows = _task_plan(PILOT)
    authority = accepted_sources()
    joint = _json(next(r for r in authority['authority'] if '/joint-tasks/' in '/' + r['path']
        and r['path'].endswith('-acceptance.json')))
    scenes = _json(authority['scenarios'])
    components = joint['independent_reference']['components']
    original = {'preference': components['preference-reference.jsonl'],
        'joint_states': components['sim-reference-index.jsonl'],
        'scenario_states': scenes['independent_reference']['reference'],
        'fixed_S': scenes['audit_private']['mutation-plan.jsonl']}
    target = evaluation_directory(OUTPUT, run_id)
    pinned_paths = [_path(r['path']) for r in original.values()]
    guard = P1StorageGuard(OUTPUT, storage_headroom(OUTPUT), run_root=target,
        run_limit_bytes=128 * 1024**2 - METADATA_RESERVE, development=True, evaluation_sources=pinned_paths)
    with guard:
        target.mkdir(parents=True, exist_ok=False)
        preference = project_rows(original['preference'], target / 'preference.jsonl',
            ('root', 'target_parent', 'group'), lambda r: r['root'] == D1)
        views = {s['view_id'] for s in rows['scenes.jsonl']}
        joint_ref = project_rows(original['joint_states'], target / 'joint-states.jsonl',
            ('view', 'profile', 'snapshot', 'material_version', 'parent', 'batch', 'candidate_state', 'eligible'),
            lambda r: r['view'] in views)
        scenario_ref = project_rows(original['scenario_states'], target / 'scenario-states.jsonl',
            ('view_id', 'request_profile_id', 'snapshot_id', 'parent_asin', 'sim_batch_id', 'candidate_state', 'eligible'),
            lambda r: r['view_id'] in views)
        sets = [r['selected_parents'] for r, _ in _scan(original['fixed_S'])]
        if not sets or any(s != sets[0] for s in sets):
            raise ValueError('fixed_S_binding')
        sources = {'scope': 'accepted_development_evaluation', 'preference': preference,
            'joint_states': joint_ref, 'scenario_states': scenario_ref, 'fixed_S': sets[0]}
        index, selected, attempts = {}, [], []
        R_task = next(t for t in rows['tasks.jsonl'] if t['method'] == 'R')
        old = json.loads((PROJECT / '.scratch/ticket14-r-frozen-preflight-20261020/resource-closeout.json').read_bytes())
        index[R_task['task_key']] = legacy_R_sidecar(target, run_root=OUTPUT / R_RUN,
            task_key=R_task['task_key'], plan_id=PILOT_ID, expected_files=old['files'])
        for task in (t for t in rows['tasks.jsonl'] if t['method'] != 'R'):
            candidates = []
            for path in OUTPUT.glob('T14-D1-*/result.json'):
                result = json.loads(path.read_bytes())
                if result.get('task_key') == task['task_key'] and result.get('plan_id') == PILOT_ID:
                    attempts.append({'run_id': result['run_id'], 'task_key': task['task_key'],
                        'terminal': result['terminal'], 'reason': result.get('reason'),
                        'model_calls': result.get('model_calls'), 'result_ref': reference(path)})
                    candidates.append((path, result))
            passed = [(p, r) for p, r in candidates if r['terminal'] in ('released', 'valid_empty')]
            # Keep the first complete run. Later failures cannot replace valid evidence.
            available = sorted(passed or candidates, key=lambda item: item[0].stat().st_mtime)
            if available:
                path, result = available[0] if passed else available[-1]
                index[task['task_key']] = reference(path)
                selected.append({'task_key': task['task_key'], 'run_id': result['run_id'], 'result_ref': index[task['task_key']]})
        plan, observations = load_evaluation_inputs(PILOT, execution_index=index, reference_sources=sources,
            read_artifact=read, resolve_artifact=_path, development=True)
        scores = [score_task(**observation) for observation in observations]
        summary = summarize(plan, scores)
        pilot_keys = {t['task_key'] for t in rows['tasks.jsonl']}
        pilot_scores = [s for s in scores if s['task_key'] in pilot_keys]
        anomaly_coverage = {}
        for scene, expected in (('V01', 'Pending'), ('V05', 'Refuted'), ('V06', 'Conflict')):
            observation = next(o for o in observations if o['task']['scene'] == scene and o['task']['method'] == 'M')
            states = (observation['execution'] or {}).get('assessments', {}).values()
            anomaly_coverage[scene] = {'expected_state': expected, 'actually_assessed': list(states).count(expected),
                'covered': expected in states}
        report = {'scope': 'frozen_D1_development_only', 'pilot_id': PILOT_ID,
            'parent_plan_id': manifest['parent_plan_id'], 'independent_users': 1, 'pilot_slots': 8,
            'scored_slots': len(pilot_scores), 'pilot_acceptance': 'PASS' if len(pilot_scores) == 8
                and all(s['status'] in ('scored', 'reference_na') and s['secondary']['failure'] == 0 for s in pilot_scores)
                and all(c['covered'] for c in anomaly_coverage.values()) else 'incomplete',
            'formal_experiment_complete': False, 'full_50_slot_summary_status': summary['status'],
            'unscheduled_slots': len(scores) - 8, 'sources': original, 'projection_sources': sources,
            'selected': selected, 'historical_attempts_retained': attempts,
            'anomaly_coverage': anomaly_coverage,
            'network_requests': 0, 'credentials': 0, 'count_api': 0, 'other_api': 0,
            'guard_denied': guard.attempts}
        store(target / 'evaluation.json', report)
        with (target / 'task-scores.jsonl').open('xb') as stream:
            for score in scores:
                stream.write(encoded(score) + b'\n')
        store(target / 'summary.json', summary)
        print(json.dumps({'evaluation_path': str(target / 'evaluation.json'),
            'pilot_acceptance': report['pilot_acceptance'], 'summary': summary['status']}))
    return 0 if report['pilot_acceptance'] == 'PASS' else 2
