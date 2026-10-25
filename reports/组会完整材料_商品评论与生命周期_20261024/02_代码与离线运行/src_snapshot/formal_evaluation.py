"""Evaluation-only formal association. Stream actual audits; no supplier sender."""
import json
import time

from evidence_access import PROJECT, digest, encoded
from experiment_runner import accepted_sources, _json, _scan, _path, _task_plan
from formal_runtime import PLAN, PLAN_ID, OUTPUT, load_config, reference


def source_references():
    """Metadata only; independent targets and states are read inside the evaluator."""
    authority = accepted_sources()
    joint = _json(next(r for r in authority['authority'] if '/joint-tasks/' in '/' + r['path']
        and r['path'].endswith('-acceptance.json')))
    scenes = _json(authority['scenarios'])
    components = joint['independent_reference']['components']
    return {'preference': components['preference-reference.jsonl'],
        'joint_states': components['sim-reference-index.jsonl'],
        'scenario_states': scenes['independent_reference']['reference'],
        'fixed_S_ref': scenes['audit_private']['mutation-plan.jsonl']}


def read(ref):
    path = _path(ref['path'])
    with path.open('rb') as stream:
        stream.seek(ref.get('offset', 0))
        raw = stream.read(ref['bytes'])
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise ValueError('formal_artifact_digest')
    return raw


def evaluate():
    from formal_experiment import require_authorization, ledger_for, store
    from p1_storage import P1StorageGuard
    from experiment_io import load_evaluation_inputs, _execution
    from experiment_evaluation import score_task, summarize
    cfg = load_config()
    require_authorization(cfg)
    ledger = ledger_for(cfg)
    original = source_references()
    _, _, rows = _task_plan(PLAN)
    target = OUTPUT / 'evaluation' / ('T15-EVAL-' + str(int(time.time() * 1000)))
    guard = P1StorageGuard(OUTPUT / 'evaluation', 1024**3, run_root=target,
        run_limit_bytes=128 * 1024**2, formal=True,
        evaluation_sources=[_path(r['path']) for r in original.values()])
    combined = {'source_scope': 'formal_test100', 'plan_id': PLAN_ID, 'users': [],
        'scenes': None, 'tasks': [], 'applicability': {}, 'cohorts': {'U8': [], 'UQ': []}}
    scores, errors = [], []
    with guard:
        target.mkdir(parents=True, exist_ok=False)
        sets = [r['selected_parents'] for r, _ in _scan(original['fixed_S_ref'])]
        if not sets or any(s != sets[0] for s in sets):
            raise ValueError('formal_fixed_S_binding')
        sources = {k: original[k] for k in ('preference', 'joint_states', 'scenario_states')} | {
            'scope': 'accepted_formal_evaluation', 'fixed_S': sets[0]}
        for user in rows['sample-users.jsonl']:
            # Build only safe task/reference associations, then load one observed audit at a time.
            plan, observations = load_evaluation_inputs(PLAN, execution_index={}, reference_sources=sources,
                read_artifact=read, resolve_artifact=_path, formal=True, root_task_ids=[user['root_task_id']])
            combined['users'].extend(plan['users'])
            combined['tasks'].extend(plan['tasks'])
            combined['applicability'].update(plan['applicability'])
            combined['scenes'] = plan['scenes']
            for name in ('U8', 'UQ'):
                combined['cohorts'][name].extend(plan['cohorts'][name])
            for observation in observations:
                task = observation['task']
                path = ledger.directory(task['task_key']) / 'result.json'
                if path.exists():
                    try:
                        observation['execution'] = _execution(task, reference(path), PLAN_ID,
                            read_artifact=read, resolve_artifact=_path)
                    except (ValueError, OSError, TypeError, KeyError):
                        errors.append({'task_key': task['task_key'], 'code': 'formal_observation_binding_failed'})
                        observation['execution'] = None
                scores.append(score_task(**observation))
                observation['execution'] = None
        summary = summarize(combined, scores)
        store(target / 'summary.json', summary)
        with (target / 'task-scores.jsonl').open('xb') as stream:
            for score in scores:
                stream.write(encoded(score) + b'\n')
        store(target / 'evaluation.json', {'plan_id': PLAN_ID, 'configuration_id': cfg['configuration_id'],
            'users': 100, 'tasks': 5000, 'independent_reference_sources': original,
            'association_errors': errors, 'guard_denied': guard.attempts,
            'count_api': 0, 'other_api': 0, 'supplier_calls': 0, 'status': summary['status']})
    return {'evaluation_path': str(target), 'status': summary['status'], 'counts': summary['counts']}
