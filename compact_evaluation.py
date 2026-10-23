"""Evaluation-only adapter. No sender or credential access; references stay private."""
import copy
import json

from evidence_access import PROJECT, encoded
from compact_experiment import DIRECTORY, OUTPUT, load_config, store_json, file_ref
from experiment_evaluation import score_task, summarize, BINDING
from experiment_io import load_evaluation_inputs
from experiment_runner import _task_plan, _scan, _path
from formal_runtime import PLAN
from formal_evaluation import source_references, read
from p1_storage import P1StorageGuard


def observed_execution(task, reference, row, observed):
    """Publication shape and original object binding are checked before independent scoring."""
    states = {p: observed[p]['state'] for p in task['C']}
    eligible = [p for p in task['C'] if observed[p]['eligible']]
    delivered = row['topK'] if row['status'] == 'ok' else []
    legal = (len(delivered) <= 10 and len(delivered) == len(set(delivered))
             and set(delivered) <= set(eligible))
    return {'task_key': task['task_key'], 'binding': {k: task[k] for k in BINDING},
        'started': True, 'terminal': ('released' if delivered else 'valid_empty') if row['status'] == 'ok' else 'failed_model',
        'delivered': delivered, 'G': eligible, 'gate_passed': legal, 'publication_verified': legal,
        'complete_C': True, 'assessments': states,
        'usage': {'basis': 'shared_preprocessing_cost_reported_separately', 'model_calls': None,
                  'input_tokens': None, 'output_tokens': None, 'cost_microusd': None}}


def evaluate():
    cfg = load_config()
    grant = OUTPUT / 'authorization.json'
    if not grant.exists() or json.loads(grant.read_bytes())['configuration_id'] != cfg['configuration_id']:
        raise ValueError('compact_execution_not_started')
    _, _, tables = _task_plan(PLAN)
    original = source_references()
    target = OUTPUT / 'evaluation' / cfg['configuration_id']
    guard = P1StorageGuard(target.parent, 1024**3, run_root=target, run_limit_bytes=128 * 1024**2,
        formal=True, evaluation_sources=[_path(r['path']) for r in original.values()])
    combined = {'source_scope': 'personalized_compact', 'plan_id': cfg['configuration_id'],
        'users': [], 'scenes': None, 'tasks': [], 'applicability': {}, 'cohorts': {'U8': [], 'UQ': []}}
    scores, component_scores = [], []
    with guard:
        target.mkdir(parents=True, exist_ok=True)
        sets = [r['selected_parents'] for r, _ in _scan(original['fixed_S_ref'])]
        if not sets or any(s != sets[0] for s in sets):
            raise ValueError('compact_fixed_set_binding')
        sources = {k: original[k] for k in ('preference', 'joint_states', 'scenario_states')} | {
            'scope': 'accepted_formal_evaluation', 'fixed_S': sets[0]}
        scene_cache = {}
        for user in tables['sample-users.jsonl']:
            plan, observations = load_evaluation_inputs(PLAN, execution_index={}, reference_sources=sources,
                read_artifact=read, resolve_artifact=_path, formal=True, root_task_ids=[user['root_task_id']])
            combined['users'].extend(plan['users'])
            combined['tasks'].extend(plan['tasks'])
            combined['applicability'].update(plan['applicability'])
            combined['scenes'] = plan['scenes']
            for name in ('U8', 'UQ'):
                combined['cohorts'][name].extend(plan['cohorts'][name])
            for observation in observations:
                task, reference = observation['task'], observation['reference']
                path = OUTPUT / 'tasks' / (task['task_key'] + '.json')
                row, execution = None, None
                if path.exists():
                    row = json.loads(path.read_bytes())
                    if (row['configuration_id'] != cfg['configuration_id'] or row['task_key'] != task['task_key']
                            or row['root_task_id'] != task['root_task_id'] or row['snapshot_id'] != task['snapshot_id']):
                        raise ValueError('compact_result_binding')
                    scene_ref = row['scene_ref']
                    scene_path = (OUTPUT / 'scenes' / (next(s['snapshot']['sha256'] for s in tables['scenes.jsonl']
                        if s['snapshot_id'] == task['snapshot_id']) + '.json'))
                    if scene_ref['path'] != scene_path.relative_to(PROJECT).as_posix():
                        raise ValueError('compact_scene_path')
                    if scene_ref['path'] not in scene_cache:
                        if file_ref(scene_path) != scene_ref:
                            raise ValueError('compact_scene_digest')
                        scene_cache[scene_ref['path']] = json.loads(scene_path.read_bytes())['candidates']
                    execution = observed_execution(task, reference, row, scene_cache[scene_ref['path']])
                main = score_task(task, execution, reference, component_protocol='personalized')
                if row is not None and row['method'] == 'M':
                    parts = {}
                    for mode, result in row['components'].items():
                        variant = copy.deepcopy(execution)
                        variant['delivered'] = result['topK']
                        variant['terminal'] = 'released' if result['topK'] else 'valid_empty'
                        part = score_task(task, variant, reference, component_protocol='personalized')
                        parts[mode] = {'SJ_C': part['metrics']['10']['SJ_NDCG'],
                                       'metric': cfg['quality_component_metric'], 'status': part['status']}
                        component_scores.append({'task_key': task['task_key'], 'mode': mode,
                            'metrics': part['metrics'], 'scope': 'scoring-or-profile-prefix-component'})
                    if task['scene'].startswith('Q'):
                        main['components'] = {mode: parts.get(mode, {'SJ_C': 0 if main['reference_applicable'] else None,
                            'status': 'anchor_failed'}) for mode in ('full', 'no_quality', 'mean_quality')}
                scores.append(main)
        summary = summarize(combined, scores)
        summary.update(protocol=cfg['protocol'], configuration_id=cfg['configuration_id'],
            component_metric=cfg['quality_component_metric'],
            analysis_scope='fixed users and materials; profile verification feedback; no real batch preference labels')
        store_json(target / 'summary.json', summary)
        with (target / 'component-scores.jsonl').open('wb') as stream:
            for row in component_scores:
                stream.write(encoded(row) + b'\n')
    return {'status': summary['status'], 'counts': summary['counts'], 'summary': str(target / 'summary.json')}


if __name__ == '__main__':
    print(json.dumps(evaluate(), ensure_ascii=False))
