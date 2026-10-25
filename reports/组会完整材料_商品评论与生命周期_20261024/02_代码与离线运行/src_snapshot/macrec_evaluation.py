"""S5 independent evaluation and development selection. No model transport capability."""
import copy
import math
import random
import json
import argparse
import sys
import hashlib
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def source_rows(ref, predicate=None):
    path = (PROJECT / ref['path']).absolute()
    if path.resolve() != path or not path.is_relative_to(PROJECT):
        raise ValueError('evaluation_source_scope')
    checksum, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for raw in stream:
            checksum.update(raw)
            count += len(raw)
            if predicate is None or predicate(raw):
                yield json.loads(raw)
    if checksum.hexdigest() != ref['sha256'] or count != ref.get('bytes', count):
        raise ValueError('evaluation_source_digest')
from collections import Counter

METRICS = ('HR', 'NDCG_P', 'EG_NDCG', 'SJ_NDCG')
FAILED = ('failed_model', 'failed_protocol', 'failed_source', 'blocked_evidence', 'incomplete_budget')


def score_task(task, observed, reference):
    """Score actual publication against a separately supplied accepted reference."""
    result = {k: task[k] for k in ('root_task_id', 'method', 'scene')}
    result.update(status='pipeline_error', reason=None, recall=None, reference_applicable=None,
        execution_status=observed.get('status') if observed else 'not_started',
        metrics={str(k): dict.fromkeys(METRICS) for k in (1, 5, 10)}, delivered_items=None, violations=None)
    try:
        c, d = task['C'], task['D']
        if (len(c) != len(set(c)) or len(d) != len(set(d)) or not set(d) <= set(c)
                or reference['target'] not in c or set(reference['states']) != set(c)
                or reference['binding_id'] != task['binding_id']
                or any(state not in ('Supported', 'Pending', 'Refuted', 'Conflict') for state in reference['states'].values())):
            raise ValueError('evaluation_reference_binding')
        applicable = reference['states'][reference['target']] == 'Supported'
        result.update(recall=int(reference['target'] in d), reference_applicable=applicable,
            na_reason=None if applicable else reference['states'][reference['target']])
        if observed is None or observed.get('status') == 'not_started':
            return result | {'status': 'not_started'}
        if observed['binding_id'] != task['binding_id']:
            raise ValueError('evaluation_observation_binding')
        if observed['status'] in ('unresolved', 'running'):
            return result | {'status': 'unresolved'}
        success = observed['status'] == 'ok'
        if not success and observed['status'] not in FAILED:
            raise ValueError('evaluation_unknown_terminal')
        delivered = observed.get('topK', []) if success else []
        pool = c if task['method'] in ('R', 'S', 'M', 'CB') else d
        shape = len(delivered) <= 10 and len(delivered) == len(set(delivered)) and set(delivered) <= set(pool)
        observations = observed.get('observations', {})
        publication = (shape and all(observations.get(p, {}).get('eligible') is True for p in delivered))
        if success and not publication:
            success, delivered = False, []
            result['reason'] = 'invalid_publication'
        violations = sum(reference['states'][p] != 'Supported' for p in delivered)
        joint_valid = success and publication and violations == 0
        rank = delivered.index(reference['target']) + 1 if reference['target'] in delivered else 0
        for k in (1, 5, 10):
            gain = 1 / math.log2(rank + 1) if success and 0 < rank <= k else 0.
            result['metrics'][str(k)] = {'HR': int(gain > 0), 'NDCG_P': gain,
                'EG_NDCG': gain if applicable else None,
                'SJ_NDCG': (gain if joint_valid else 0.) if applicable else None}
        result.update(status='scored' if success else 'failed', delivered_items=len(delivered),
            violations=violations, fill=len(delivered) / 10,
            retrieval_empty=bool(success and not delivered and any(s == 'Supported' for s in reference['states'].values())
                and not any(observations.get(p, {}).get('eligible') for p in d)))
        return result
    except (ValueError, TypeError, KeyError) as exc:
        return result | {'status': 'pipeline_error', 'reason': str(exc)}


def summarize(plan, scores):
    """Fixed plan denominators; missing attempts stay unknown rather than observations."""
    key = lambda row: (row['root_task_id'], row['method'], row['scene'])
    observed = {key(row): row for row in scores}
    expected = {key(row): row for row in plan['tasks']}
    if len(observed) != len(scores) or len(expected) != len(plan['tasks']) or not set(observed) <= set(expected):
        raise ValueError('evaluation_summary_scope')
    grouped = {}
    for identity, task in expected.items():
        row = observed.get(identity, {'status': 'not_started', 'reference_applicable': None, 'recall': None,
            'metrics': {str(k): dict.fromkeys(METRICS) for k in (1, 5, 10)}})
        grouped.setdefault(task['method'] + '/' + task['scene'], []).append(row)
    report = {}
    for name, rows in grouped.items():
        metrics, bounds = {}, {}
        for k in ('1', '5', '10'):
            metrics[k], bounds[k] = {}, {}
            for metric in METRICS:
                applicable = rows if metric in ('HR', 'NDCG_P') else [r for r in rows if r['reference_applicable'] is True]
                unknown_reference = metric not in ('HR', 'NDCG_P') and any(r['reference_applicable'] is None for r in rows)
                values = [r['metrics'][k][metric] for r in applicable]
                denominator = len(applicable)
                complete = denominator > 0 and not unknown_reference and all(v is not None for v in values)
                metrics[k][metric] = sum(values) / denominator if complete else None
                bounds[k][metric] = (sum(v for v in values if v is not None) / denominator
                    if denominator and not unknown_reference else None)
        recalls = [r['recall'] for r in rows]
        report[name] = {'users': len(rows), 'states': dict(Counter(r['status'] for r in rows)),
            'execution_states': dict(Counter(r.get('execution_status', r['status']) for r in rows)),
            'metrics': metrics, 'conservative_lower_bound': bounds,
            'recall': sum(recalls) / len(rows) if all(v is not None for v in recalls) else None,
            'reference_na': sum(r['reference_applicable'] is False for r in rows),
            'eligible_target_recall': (sum(r['recall'] for r in rows if r['reference_applicable'] is True)
                / sum(r['reference_applicable'] is True for r in rows) if any(r['reference_applicable'] is True for r in rows)
                and all(r['recall'] is not None for r in rows if r['reference_applicable'] is True) else None),
            'violations': sum(r.get('violations') or 0 for r in rows),
            'fill': sum(r.get('fill') or 0 for r in rows) / len(rows),
            'lower_bound_interpretation': 'fixed planned denominator; unknown attempts are not observed failures'}
    comparisons = {}
    for other, scenes, confidence in (('B0', ['V00'], .95), ('A-semantic', ['V00'], .9875),
            ('A-confidence', ['V00'], .9875), ('A-quality', ['Q1', 'Q2'], .9875), ('A-feedback', ['V00'], .9875)):
        users = [u for u in plan['users'] if all((u, method, scene) in expected
            for method in ('I1', other) for scene in scenes)]
        deltas, complete_pairs = [], True
        for user in users:
            values = []
            for scene in scenes:
                pair = [observed.get((user, m, scene), {}).get('metrics', {}).get('10', {}).get('NDCG_P')
                    for m in ('I1', other)]
                if any(v is None for v in pair):
                    complete_pairs = False
                else:
                    values.append(pair[0] - pair[1])
            if len(values) == len(scenes):
                deltas.append(sum(values) / len(values))
        comparison = {'users': len(users), 'scenes': scenes, 'confidence': confidence,
            'point': None, 'interval': None, 'metric': 'NDCG_P@10', 'resampling_unit': 'user',
            'samples': 1000, 'seed': 1000, 'interpretation': 'exploratory; selected development panel and tuned parameters'}
        if users and complete_pairs:
            generator = random.Random(1000)
            draws = sorted(sum(generator.choice(deltas) for _ in deltas) / len(deltas) for _ in range(1000))
            tail = (1 - confidence) / 2
            def quantile(q):
                position = q * (len(draws) - 1)
                left = int(position)
                return draws[left] + (draws[min(left + 1, len(draws) - 1)] - draws[left]) * (position - left)
            comparison.update(point=sum(deltas) / len(deltas), interval=[quantile(tail), quantile(1 - tail)])
        comparisons['I1-' + other] = comparison
    complete = all(row['status'] not in ('not_started', 'unresolved', 'pipeline_error') for row in observed.values())
    strata = {}
    depths = {t['root_task_id']: t['history_depth'] for t in plan['tasks'] if 'history_depth' in t}
    for label, short in (('one_parent', True), ('multiple_parents', False)):
        selected = {u for u, n in depths.items() if (n <= 1) == short}
        selected_rows = [r for r in scores if r['root_task_id'] in selected]
        by_group = {}
        for row in selected_rows:
            by_group.setdefault(row['method'] + '/' + row['scene'], []).append(row)
        strata[label] = {'users': len(selected), 'interpretation': 'descriptive; no extra sampling',
            'groups': {name: {'rows': len(rows), 'HR@10': (sum(r['metrics']['10']['HR'] for r in rows) / len(rows)
                    if all(r['metrics']['10']['HR'] is not None for r in rows) else None),
                'NDCG_P@10': (sum(r['metrics']['10']['NDCG_P'] for r in rows) / len(rows)
                    if all(r['metrics']['10']['NDCG_P'] is not None for r in rows) else None)} for name, rows in by_group.items()}}
    return {'status': 'complete' if complete and len(observed) == len(expected) else 'partial',
        'groups': report, 'comparisons': comparisons, 'planned_rows': len(expected), 'observed_rows': len(observed),
        'users': len(plan['users']), 'scope': 'development_exploration',
        'history_strata': strata,
        'test_exposure': 'old test100 scores informed design; one additional out-of-panel test label was accidentally viewed during schema inspection; no blind-test claim'}


def select_development(sources, references):
    # This is an evaluation-side development selection, never a model-time truth generator.
    from macrec_experiment import prepare, read_ref
    trials, component_scores, candidates = [], {}, []
    observations = sources.get('observations')
    if observations is None:
        observations = {label: read_ref(ref)['candidates'] for label, ref in sources['evidence'].items()}
    for weights in ([1, 1, 1], [2, 1, 1], [1, 1, 2]):
        prepared = prepare(sources, sources['scope'], {'weights': weights, 'M': 200})
        scores = []
        for root, task in prepared['tasks'].items():
            if root not in references['targets']:
                raise ValueError('selection_reference_missing')
            target = references['targets'][root]
            order = sorted(task['C'], key=lambda p: (-task['prior'][p], p.encode()))
            qualified = [p for p in order if observations['V00'][p]['eligible']][:10]
            rank = qualified.index(target) + 1 if target in qualified else 0
            scores.append({'HR': int(rank > 0), 'NDCG_P': 1 / math.log2(rank + 1) if rank else 0.})
            if weights == [1, 1, 1]:
                for view, values in task['content_components'].items():
                    ranked = sorted(task['C'], key=lambda p: (-round(values[p], 12), p.encode()))
                    top = [p for p in ranked if observations['V00'][p]['eligible']][:10]
                    position = top.index(target) + 1 if target in top else 0
                    component_scores.setdefault(view, []).append(1 / math.log2(position + 1) if position else 0.)
        trials.append({'weights': weights, 'NDCG_P@10': sum(r['NDCG_P'] for r in scores) / len(scores),
            'HR@10': sum(r['HR'] for r in scores) / len(scores), 'users': len(scores)})
        candidates.append(prepared)
    chosen = min(range(3), key=lambda i: (-trials[i]['NDCG_P@10'], -trials[i]['HR@10'], i))
    tasks = candidates[chosen]['tasks']
    coverage = []
    for m in (50, 100, 200):
        hits = sum(references['targets'][u] in sorted(t['C'], key=lambda p: (-t['prior'][p], p.encode()))[:m]
            for u, t in tasks.items())
        coverage.append({'M': m, 'hits': hits, 'users': len(tasks), 'recall': hits / len(tasks)})
    m = next((row['M'] for row in coverage if row['recall'] >= .9), 200)
    from personalized_recommendation import analyze_profile, run_task as compact_rank
    offline_tasks, offline_scores = [], []
    for user, original in tasks.items():
        task = copy.deepcopy(original)
        task['D'] = sorted(task['C'], key=lambda p: (-task['prior'][p], p.encode()))[:m]
        catalog = list(task['catalog'].values())
        profile = analyze_profile(task['history'], catalog, method='R')['profile']
        for scene, rows in observations.items():
            actual = {p: rows[p] for p in task['C']}
            state = {p: references['states'][scene][p] for p in task['C']}
            for method, pool in (('CB', task['C']), ('CB-D', task['D']), ('R', task['C'])):
                binding = 'offline-' + user + '-' + scene
                descriptor = {k: task[k] for k in ('root_task_id', 'C', 'D')}
                descriptor.update(method=method, scene=scene, binding_id=binding,
                    history_depth=len({h['parent_asin'] for h in task['history']}))
                if method == 'R':
                    delivered = compact_rank({'C': task['C'], 'base_scores': [task['char3'][p] for p in task['C']],
                        'K': 10, 'method': 'R', 'prefer_stock': scene in ('Q1', 'Q2')},
                        catalog=catalog, history=task['history'], profile=profile, scene=actual)['topK']
                else:
                    ranked = sorted(pool, key=lambda p: (-round(task['prior'][p], 12), p.encode()))
                    delivered = [p for p in ranked if actual[p]['eligible']][:10]
                observed = {'status': 'ok', 'topK': delivered, 'binding_id': binding, 'observations': actual}
                ref = {'target': references['targets'][user], 'states': state, 'binding_id': binding}
                offline_tasks.append(descriptor)
                offline_scores.append(score_task(descriptor, observed, ref))
    offline_plan = {'users': list(tasks), 'tasks': offline_tasks}
    return {'weights': trials[chosen]['weights'], 'M': m, 'trials': trials, 'coverage': coverage,
        'users': len(tasks), 'component_NDCG_P@10': {k: sum(v) / len(v) for k, v in component_scores.items()},
        'offline': {'scores': offline_scores, 'summary': summarize(offline_plan, offline_scores)},
        'selection_scope': 'dev320_full_C; all tried values retained; not a confirmatory estimate'}


def evaluation_guard(event, args):
    if event.startswith('socket.') or event == 'subprocess.Popen':
        raise PermissionError('evaluation_network_and_children_denied')
    if event == 'open' and isinstance(args[0], (str, bytes)) and '.secrets' in str(args[0]):
        raise PermissionError('evaluation_credentials_denied')
    if event == 'import' and args[0] in ('provider_fourrouter', 'fourrouter_probe', 'macrec_recommendation'):
        raise PermissionError('evaluation_producer_import_denied')


def select_grid(inputs, references):
    trials = []
    for trial in inputs['trials']:
        scores = []
        tasks = []
        for row in trial['rows']:
            task = row['task']
            ref = {'target': references['targets'][task['root_task_id']], 'binding_id': task['binding_id'],
                'states': {p: references['states'][task['scene']][p] for p in task['C']}}
            tasks.append(task)
            scores.append(score_task(task, row['observed'], ref))
        summary = summarize({'users': inputs['users'], 'tasks': tasks}, scores)
        if summary['status'] != 'complete':
            raise ValueError('evaluation_grid_incomplete')
        trials.append({'policy': trial['policy'], 'scores': scores, 'summary': summary,
            'NDCG_P@10': summary['groups']['I1/V00']['metrics']['10']['NDCG_P']})
    selected = min(trials, key=lambda r: (-r['NDCG_P@10'], r['policy']['lambda'], -r['policy']['tau']))
    return {'policy': selected['policy'], 'trials': trials,
        'selection_scope': 'development scoring components, six settings; not six full systems'}


def evaluate_run(plan, references, *, stage='final'):
    from macrec_experiment import read_ref, file_ref, task_for, binding_for, read_unit_result, digest, PUBLIC
    from task16_control import session_path, observed_unit, request_rows, read, call_counts
    directory = session_path(PROJECT / plan['session_dir'])
    plan_sha = digest(plan)
    tasks, scores, unit_states = [], [], []
    for phase in plan['stages']:
        for unit in phase['units']:
            if unit['operation'] not in ('recommend', 'auxiliary'):
                continue
            if stage == 'v00' and (unit['operation'] == 'auxiliary' or unit.get('scene') != 'V00'
                    or unit['method'] not in ('B0', 'I1')):
                continue
            receipt = observed_unit(directory, unit, plan_sha)
            raw = None
            if receipt and receipt.get('output') and receipt['output'].get('result'):
                raw = read_ref(receipt['output']['result'])
            elif directory.is_relative_to(PUBLIC):
                raw = read_unit_result(directory, unit)
            state = raw['status'] if raw else receipt['status'] if receipt else 'not_started'
            if receipt is None and raw is None:
                intents = [r for r in request_rows(directory) if r['unit'] == unit['id']]
                if intents:
                    state = 'unresolved'
            unit_states.append({'id': unit['id'], 'status': state})
            scenes = ('V00', 'Q1', 'Q2') if unit['operation'] == 'auxiliary' else (unit['scene'],)
            for scene in scenes:
                current = unit
                if unit['operation'] == 'auxiliary':
                    current = unit | {'scene': scene, 'materials': unit['evidence'][scene]}
                task = task_for(current)
                binding = binding_for(current, task)
                descriptor = {k: task[k] for k in ('root_task_id', 'C', 'D')}
                descriptor.update(method=unit['method'], scene=scene, binding_id=binding,
                    history_depth=len({h['parent_asin'] for h in task['history']}))
                observed = raw.get('scene_results', {}).get(scene) if raw and unit['operation'] == 'auxiliary' else raw
                if observed is None and state != 'not_started':
                    observed = {'status': state, 'binding_id': binding, 'topK': []}
                reference = {'target': references['targets'][unit['root_id']], 'binding_id': binding,
                    'states': {p: references['states'][scene][p] for p in task['C']}}
                tasks.append(descriptor)
                scores.append(score_task(descriptor, observed, reference))
    if plan.get('offline_selection'):
        offline = read_ref(plan['offline_selection'])['offline']['scores']
        for row in offline:
            if row['root_task_id'] in plan['panel'] and row['scene'] in (('V00',) if stage == 'v00' else ('V00', 'Q1', 'Q2')):
                tasks.append({k: row[k] for k in ('root_task_id', 'method', 'scene')})
                scores.append(row)
    summary = summarize({'users': plan['panel'], 'tasks': tasks}, scores)
    counts, usage, latency = call_counts(directory)
    return {'stage': stage, 'summary': summary, 'scores': scores, 'unit_states': unit_states,
        'calls': counts, 'usage': usage, 'api_latency_sum_seconds': latency,
        'base_CNY_known_tokens': usage['input_tokens'] / 1e6 * .045 + usage['output_tokens'] / 1e6 * .225,
        'unknown_usage_requests': usage['unknown_requests'], 'cached_input_CNY_per_M': None,
        'extra_multiplier': None, 'fixed_fees': None, 'invoice': False}


def prepare_development_references(output):
    from experiment_runner import accepted_sources, ORIGINAL
    from formal_evaluation import source_references
    from formal_runtime import PLAN, load_config
    from macrec_experiment import read_ref, store, digest
    authority, independent = accepted_sources(), source_references()
    cfg = load_config(validate_code=False)
    split_ref = next(ref for ref in authority['authority'] if '/splits/' in ref['path'] and not ref['path'].endswith('-acceptance.json'))
    split = read_ref(split_ref)
    accounts = {row['user_id']: row for row in source_rows({'path': split['accounts_path'], 'sha256': split['accounts_sha256']})
        if row['split'] == 'dev'}
    cohort = []
    for row in source_rows(authority['cohort'], lambda raw: b'"split":"dev"' in raw):
        if row['source_user_id'] not in accounts:
            raise ValueError('evaluation_development_identity')
        cohort.append({'root_task_id': row['task_id'], 'split': 'dev',
            'split_hash': accounts[row['source_user_id']]['split_hash']})
    if len(cohort) != 320 or len({r['split_hash'] for r in cohort}) != 320:
        raise ValueError('evaluation_development_count')
    cohort.sort(key=lambda row: bytes.fromhex(row['split_hash']))
    users = {row['root_task_id'] for row in cohort}
    chosen = lambda raw: (match := re.search(rb'"root":"([0-9a-f]{64})"', raw)) and match[1].decode() in users
    targets = {row['root']: row['target_parent'] for row in source_rows(independent['preference'], chosen)}
    if set(targets) != users:
        raise ValueError('evaluation_development_targets')
    templates = {}
    for row in source_rows(authority['view_bindings']):
        if row['root_task_id'] in users:
            template = {k: row[k] for k in ('request_profile_id', 'material_version')}
            previous = templates.setdefault(row['label'], template)
            if previous != template:
                raise ValueError('evaluation_nonshared_request_profile')
    scenes = list(source_rows(cfg['plan_files']['scenes.jsonl']))
    if {s['label'] for s in scenes} != {f'V{i:02d}' for i in range(16)} | {'Q1', 'Q2'}:
        raise ValueError('evaluation_scene_scope')
    scenes = [s | templates.get(s['label'], templates['V00']) for s in scenes]
    by_view = {s['view_id']: s for s in scenes}
    mapping = {r['parent_asin']: r['sim_batch_id'] for r in source_rows(authority['candidate_map'])}
    states = {s['label']: {} for s in scenes}
    for role, original in (('joint_states', True), ('scenario_states', False)):
        for row in source_rows(independent[role]):
            scene = by_view.get(row['view' if original else 'view_id'])
            if scene is None or (scene['label'] in ORIGINAL) != original:
                continue
            if row['profile' if original else 'request_profile_id'] != scene['request_profile_id']:
                continue
            parent = row['parent' if original else 'parent_asin']
            state = row['candidate_state']
            if (row['snapshot' if original else 'snapshot_id'] != scene['snapshot_id']
                    or row['batch' if original else 'sim_batch_id'] != mapping[parent]
                    or original and row['material_version'] != scene['material_version']
                    or state not in ('Supported', 'Refuted', 'Pending', 'Conflict')
                    or row['eligible'] != (state == 'Supported') or parent in states[scene['label']]):
                raise ValueError('evaluation_state_association')
            states[scene['label']][parent] = state
    if any(set(values) != set(mapping) for values in states.values()):
        raise ValueError('evaluation_missing_reference_state')
    cohort_path = (Path(output).parent.parent / 'prepared/dev-cohort.json'
        if Path(output).parent.name == 'private' else Path(output).parent / 'dev-cohort.json')
    cohort_ref = store(cohort_path, cohort)
    reference_ref = store(output, {'targets': targets, 'states': states, 'scenes': scenes,
        'sources': independent, 'cohort_sha256': digest(cohort), 'scope': 'accepted_development_only'})
    return {'status': 'ok', 'users': 320, 'test_users_exported': 0, 'cohort': cohort_ref, 'references': reference_ref}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['select', 'references', 'grid', 'report'])
    parser.add_argument('--inputs')
    parser.add_argument('--references')
    parser.add_argument('--reference-sha')
    parser.add_argument('--output', required=True)
    parser.add_argument('--safe-output')
    parser.add_argument('--stage', choices=['v00', 'final'], default='final')
    args = parser.parse_args()
    sys.addaudithook(evaluation_guard)
    if args.command == 'references':
        print(json.dumps(prepare_development_references(args.output)))
        return
    from macrec_experiment import store
    sources = json.loads(Path(args.inputs).read_bytes())
    private_bytes = Path(args.references).read_bytes()
    if args.reference_sha and hashlib.sha256(private_bytes).hexdigest() != args.reference_sha:
        raise ValueError('evaluation_frozen_reference_changed')
    references = json.loads(private_bytes)
    if args.command == 'report':
        result = evaluate_run(sources, references, stage=args.stage)
        ref = store(args.output, result)
        print(json.dumps({'status': result['summary']['status'], 'report': ref}))
        return
    result = select_grid(sources, references) if args.command == 'grid' else select_development(sources, references)
    ref = store(args.output, result)
    safe = result['policy'] if args.command == 'grid' else {k: result[k] for k in ('weights', 'M')}
    safe_ref = store(args.safe_output, safe) if args.safe_output else None
    print(json.dumps({'status': 'ok', 'users': len(sources['users']) if args.command == 'grid' else result['users'], 'selection_ref': ref,
        'configuration': safe, 'configuration_ref': safe_ref}))


if __name__ == '__main__':
    main()
