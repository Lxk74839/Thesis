"""Independent F1/F2 evaluation. References are evaluation-only, never model inputs."""
import copy
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
from collections import Counter
import uuid

METRICS = ('HR', 'NDCG_P', 'EG_NDCG', 'SJ_NDCG')
BINDING = ('root_task_id', 'view_id', 'material_version', 'snapshot_id', 'request_profile_id',
           'principal_id', 'verify_at_ms', 'C', 'batches', 'H_sha256', 'base_scores_sha256')
STATES = ('Supported', 'Refuted', 'Pending', 'Conflict')
FAILED = ('failed_model', 'failed_protocol', 'failed_source', 'blocked_evidence',
          'incomplete_budget', 'incomplete_count', 'incomplete_deadline')
ORIGINAL = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12')
SCENES = tuple(f'V{i:02d}' for i in range(16)) + ('Q1', 'Q2')
PROJECT = Path(__file__).resolve().parent
PUBLIC = PROJECT / '.tmp/experiment-evaluation'


def _wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_wire(value)).hexdigest()


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def score_task(task, execution, reference):
    """Score one observed task against an independently supplied reference."""
    empty = {k: copy.deepcopy(task.get(k)) for k in ('task_key', 'root_task_id', 'view_id', 'scene', 'method', 'repeat')}
    empty.update(status='pipeline_error', error=None, execution_state='missing_record',
        reference_applicable=None, na_reason=None, terminal=None, usage=None, components=None,
        task_sha256=_digest(task), metrics={str(k): dict.fromkeys(METRICS) for k in (1, 5, 10)})
    try:
        c = task['C']
        _require(task['repeat'] == 1 and task['method'] in ('R', 'S', 'M')
                 and len(c) == len(set(c)) and all(isinstance(p, str) for p in c)
                 and len(c) == len(task['batches']), 'invalid_task')
        binding = {k: task[k] for k in BINDING}
        _require(reference['binding'] == binding and reference['target'] in c
                 and set(reference['states']) == set(c)
                 and all(s in STATES for s in reference['states'].values()), 'reference_binding_mismatch')
        source = reference['source_ref']
        _require(bool(source['path']) and len(source['sha256']) == 64
                 and int(source['sha256'], 16) >= 0, 'invalid_reference_source')
        if execution is not None:
            _require(execution['task_key'] == task['task_key'] and execution['binding'] == binding,
                     'execution_binding_mismatch')
            _require(type(execution['started']) is bool and execution['terminal'] in (
                'not_started', 'configuration_required', 'running', 'unresolved_attempt',
                'released', 'valid_empty', *FAILED), 'invalid_execution_state')
            _require(execution['started'] == (execution['terminal'] not in ('not_started', 'configuration_required')),
                     'invalid_execution_state')
        result = _score_task(task, execution, reference) | {'task_sha256': empty['task_sha256']}
        if task['scene'] in ('Q1', 'Q2') and result['status'] not in ('not_started', 'unresolved', 'pipeline_error'):
            _quality(result, task, execution, reference)
        return result
    except (KeyError, TypeError, ValueError) as exc:
        return empty | {'error': str(exc)}


def _score_task(task, execution, reference):
    applicable = reference['states'][reference['target']] == 'Supported'
    result = {k: copy.deepcopy(task[k]) for k in ('task_key', 'root_task_id', 'view_id', 'scene', 'method', 'repeat')}
    result.update(status='pipeline_error', error=None, execution_state='missing_record', terminal=None,
        reference_applicable=applicable, na_reason=None if applicable else reference['states'][reference['target']],
        metrics={str(k): dict.fromkeys(METRICS) for k in (1, 5, 10)}, usage=None, components=None,
        secondary=None, confusion=None, recall=None)
    if execution is None:
        return result | {'error': 'missing_execution_record'}
    result['terminal'] = execution['terminal']
    if not execution['started']:
        return result | {'status': 'not_started', 'execution_state': 'not_started'}
    result['usage'] = copy.deepcopy(execution['usage'])
    if execution['terminal'] in ('unresolved_attempt', 'running'):
        return result | {'status': 'unresolved', 'execution_state': 'unresolved'}
    success = execution['terminal'] in ('released', 'valid_empty')
    result.update(status='scored' if success else 'failed',
                  execution_state=execution['terminal'] if success else 'failed', usage=copy.deepcopy(execution['usage']))
    delivered = execution['delivered'] if success else []
    acquired_g = set(execution['G'])
    supported = {p for p in task['C'] if reference['states'][p] == 'Supported'}
    assessments = execution['assessments']
    _require(set(assessments) <= set(task['C']) and all(s in (*STATES, 'Unassessed') for s in assessments.values()),
             'invalid_assessments')
    empty_proof = (not delivered and not acquired_g and execution['complete_C'] is True
                   and set(assessments) == set(task['C']) and all(s in STATES and s != 'Supported' for s in assessments.values()))
    release_valid = (execution['terminal'] == 'released' and bool(delivered)
                     or execution['terminal'] == 'valid_empty' and empty_proof and not supported)
    legal_shape = len(delivered) <= 10 and len(set(delivered)) == len(delivered) and set(delivered) <= set(task['C'])
    gate = (release_valid and legal_shape and execution['gate_passed'] and execution['publication_verified']
            and set(delivered) <= set(execution['G'])
            and all(reference['states'][p] == 'Supported' for p in delivered))
    preference_valid = legal_shape and release_valid and execution['gate_passed'] and execution['publication_verified']
    if success and not preference_valid:
        result.update(execution_state='failed', status='failed', reason='invalid_publication')
    metrics = {}
    for k in (1, 5, 10):
        rank = delivered.index(reference['target']) + 1 if reference['target'] in delivered else 0
        gain = 1 / math.log2(rank + 1) if preference_valid and 0 < rank <= k else 0
        metrics[str(k)] = {'HR': int(gain > 0), 'NDCG_P': gain,
                           'EG_NDCG': gain if applicable else None,
                           'SJ_NDCG': (gain if gate else 0) if applicable else None}
    result['metrics'] = metrics
    violations = sum(p not in supported for p in delivered)
    result['secondary'] = {'violation_item_rate': violations / len(delivered) if delivered else None,
        'violation_items': violations, 'delivered_items': len(delivered), 'any_violation': int(violations > 0),
        'failure': int(not gate), 'necessary_satisfied': int(gate),
        'qualified_coverage': len(acquired_g & supported) / len(supported) if supported else None,
        'fill': len(delivered) / 10,
        'qualified_fill': len(set(delivered) & supported) / min(10, len(supported)) if supported else None}
    result['confusion'], result['recall'] = {}, {}
    for group in ('fixed_S', 'other'):
        matrix = {state: dict.fromkeys((*STATES, 'Unassessed'), 0) for state in STATES}
        for parent in task['C']:
            if (parent in task.get('fixed_S', [])) == (group == 'fixed_S'):
                matrix[reference['states'][parent]][assessments.get(parent, 'Unassessed')] += 1
        result['confusion'][group] = matrix
        result['recall'][group] = {s: matrix[s][s] / sum(matrix[s].values()) if sum(matrix[s].values()) else None for s in STATES}
    if not applicable:
        result['status'] = 'reference_na'
    return result


def _quality(result, task, execution, reference):
    modes = ('full', 'no_quality', 'mean_quality')
    if result['execution_state'] == 'failed':
        result['components'] = {mode: {'SJ_C': 0 if result['reference_applicable'] else None,
                                      'status': 'anchor_failed'} for mode in modes}
        return
    acquired, components = execution['acquired'], execution['components']
    anchor = components['full']['anchor']
    _require(task['method'] == 'M' and set(components) == set(modes), 'invalid_quality_task')
    expected = {'root_task_id': task['root_task_id'], 'snapshot_id': task['snapshot_id'],
        'A_sha256': _digest(acquired), 'G': execution['G'], 'C_sha256': _digest(task['C']),
        'base_score_sha256': task['base_scores_sha256'], 'H_sha256': task['H_sha256'],
        'repeat_id': task['repeat'], 'cursor': execution['cursor'], 'stop_reason': execution['stop_reason'],
        'terminal': execution['terminal'], 'fusion_sha256': _digest(task['fusion'])}
    _require(all(anchor[k] == v for k, v in expected.items()), 'quality_anchor_mismatch')
    _require(all(acquired['binding'][k] == task[k] for k in ('root_task_id', 'snapshot_id', 'principal_id', 'verify_at_ms'))
             and acquired['candidate_binding']['C'] == task['C']
             and acquired['candidate_binding']['base_scores'] == task['base_scores']
             and _digest(list(zip(task['C'], task['base_scores']))) == task['base_scores_sha256'], 'quality_scope_mismatch')
    admitted = {p for p, a in acquired['assessments'].items()
                if a['eligible'] and a['evidence_state'] == 'Supported' and a['advance_allowed']}
    _require(admitted == set(execution['G']) and len(execution['G']) == len(admitted), 'quality_G_expansion')
    fusion = task['fusion']
    _require(fusion['alpha'] == .5 and fusion['beta'] == [.25,.5,.25] and fusion['K'] == 10
             and fusion['mode'] == 'full' and fusion['preference'] == {'source': 'experiment_design',
                'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}, 'quality_fusion_mismatch')
    # Replay an accepted scoring component on actual M acquisitions, never on references/gold.
    from evidence_verification import rank_acquired_quality
    observed = rank_acquired_quality(fusion, acquired)
    rows = observed['candidates']
    _require([r['parent_asin'] for r in rows] == task['C'], 'quality_candidate_scope')
    supported = [r['q'] for r in rows if r['z']]
    mean = math.fsum(supported) / len(supported) if supported else 0
    result['quality'] = {'A_sha256': anchor['A_sha256'], 'G': execution['G'][:],
                         'mean_q': mean, 'mean_denominator': len(supported)}
    result['components'] = {}
    factor_keys = ('parent_asin', 'z', 'm', 'q', 'C', 'T', 'A', 'citations')
    factors = [{k: r[k] for k in factor_keys} for r in rows]
    _require([{k: r[k] for k in factor_keys} for r in components['full']['candidates']] == factors,
             'quality_unacquired_fact')
    for mode in modes:
        component = components[mode]
        _require(component['anchor'] == anchor and component['anchor_sha256'] == _digest(anchor)
                 and set(component['G']) == admitted and len(component['G']) == len(admitted), 'quality_anchor_mismatch')
        _require(component['status'] == 'computed'
                 and [{k: r[k] for k in factor_keys} for r in component['candidates']] == factors
                 and component['mean_quality']['denominator'] == len(supported)
                 and abs(component['mean_quality']['value']-mean) < 1e-12, 'quality_control_scope_mismatch')
        qeff = lambda r: r['q'] if mode == 'full' else r['z'] if mode == 'no_quality' else r['z']*mean
        scores = {r['parent_asin']: round(.5*b+.5*qeff(r)*r['m'], 12) for r, b in zip(rows, task['base_scores'])}
        order = sorted(execution['G'], key=lambda p: (-scores[p], p.encode()))
        _require(component['order'] == order and component['topK'] == order[:10], 'quality_order_mismatch')
        replay = _score_task(task, execution | {'delivered': component['topK']}, reference)
        result['components'][mode] = {'SJ_C': replay['metrics']['10']['SJ_NDCG'],
            'metrics': replay['metrics'], 'status': 'fixed_M_scope_component'}
    if components['full']['topK'] != execution['delivered'] or result['secondary']['failure']:
        result.update(execution_state='failed', status='failed' if result['reference_applicable'] else 'reference_na',
                      reason='quality_anchor_publication_failed')
        result['secondary'].update(failure=1, necessary_satisfied=0)
        for metrics in result['metrics'].values():
            metrics['SJ_NDCG'] = 0 if result['reference_applicable'] else None
        for component in result['components'].values():
            component.update(SJ_C=0 if result['reference_applicable'] else None, status='anchor_failed')
            for metrics in component['metrics'].values():
                metrics['SJ_NDCG'] = 0 if result['reference_applicable'] else None


def _average(values):
    return math.fsum(values) / len(values) if values and all(v is not None for v in values) else None


def _scene_report(scene, method, rows, applicability):
    applicable = [r for r in rows if applicability[r['root_task_id']][scene]]
    closed = all(r['status'] not in ('pipeline_error', 'not_started', 'unresolved') for r in rows)
    metrics = {str(k): {name: _average([r['metrics'][str(k)][name] for r in (
        applicable if name in ('EG_NDCG', 'SJ_NDCG') else rows)]) for name in METRICS} for k in (1, 5, 10)}
    report = {'scene': scene, 'method': method, 'group': 'quality' if scene.startswith('Q') else
        'original8' if scene in ORIGINAL else 'additional8', 'planned': len(rows), 'applicable': len(applicable),
        'NA': len(rows)-len(applicable), 'NA_reasons': dict(Counter(r['na_reason'] for r in rows if r['na_reason'])),
        'status': 'complete' if closed else 'incomplete', 'terminal_counts': dict(Counter(r['terminal'] or 'missing_record' for r in rows)),
        'execution_counts': dict(Counter(r['execution_state'] for r in rows)), 'metrics': metrics,
        'SJ_NDCG': metrics['10']['SJ_NDCG']}
    secondary = [r.get('secondary') for r in rows]
    report['secondary'] = {name: _average([s[name] for s in secondary if s and s[name] is not None]) if closed else None
        for name in ('necessary_satisfied', 'failure', 'any_violation', 'qualified_coverage', 'fill', 'qualified_fill')}
    items = sum((s or {}).get('delivered_items', 0) for s in secondary)
    report['violation_item_rate'] = sum((s or {}).get('violation_items', 0) for s in secondary)/items if closed and items else None
    report['confusion'], report['recall'] = {}, {}
    for group in ('fixed_S', 'other'):
        matrix = {s: {p: sum((r.get('confusion') or {}).get(group, {}).get(s, {}).get(p, 0) for r in rows)
                      for p in (*STATES, 'Unassessed')} for s in STATES}
        report['confusion'][group] = matrix
        report['recall'][group] = {s: matrix[s][s]/sum(matrix[s].values()) if closed and sum(matrix[s].values()) else None for s in STATES}
    if scene.startswith('Q'):
        report['components'] = {mode: _average([(r['components'] or {}).get(mode, {}).get('SJ_C') for r in applicable])
                                for mode in ('full', 'no_quality', 'mean_quality')}
    return report


def _usage_report(rows):
    groups = {}
    for row in rows:
        usage = row['usage'] or {}
        groups.setdefault(usage.get('basis', 'unknown'), []).append(usage)
    unattributed = len(groups.get('unknown', []))
    result = {}
    for basis, usages in groups.items():
        result[basis] = {}
        for field in ('model_calls', 'input_tokens', 'output_tokens', 'logical_tools', 'physical_tools', 'retries', 'cost_microusd'):
            values = [u.get(field) for u in usages]
            known = [v for v in values if v is not None]
            _require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in known), 'invalid_usage')
            unknown = len(values)-len(known)
            result[basis][field] = {'known_subtotal': math.fsum(known), 'unknown_tasks': unknown,
                'total': math.fsum(known) if not unknown and not unattributed and field != 'cost_microusd' else None}
    return result


def summarize(plan, task_scores):
    """Aggregate fixed users and scenes without replacing missing tasks by zeros."""
    users = sorted(plan['users'], key=lambda p: p.encode())
    _require(len(users) == len(set(users)) and set(plan['scenes']) == set(SCENES), 'invalid_plan')
    tasks = {t['task_key']: t for t in plan['tasks']}
    _require(len(tasks) == len(plan['tasks']) == len(users)*50, 'invalid_plan_tasks')
    planned = {(u, s, m, 1) for u in users for s in SCENES for m in (('M',) if s.startswith('Q') else ('R', 'S', 'M'))}
    _require({(t['root_task_id'], t['scene'], t['method'], t['repeat']) for t in tasks.values()} == planned,
             'invalid_plan_tasks')
    rows = {r['task_key']: r for r in task_scores}
    _require(len(rows) == len(task_scores) and set(rows) <= set(tasks), 'duplicate_or_unknown_task_score')
    for key, row in rows.items():
        _require(row['task_sha256'] == _digest(tasks[key]) and all(row[k] == tasks[key][k]
                 for k in ('root_task_id', 'view_id', 'scene', 'method', 'repeat')), 'task_score_binding_mismatch')
        if row['reference_applicable'] is not None:
            _require(row['reference_applicable'] is plan['applicability'][row['root_task_id']][row['scene']],
                     'reference_applicability_mismatch')
    missing = set(tasks) - set(rows)
    for key in missing:
        task = tasks[key]
        rows[key] = {k: task[k] for k in ('task_key', 'root_task_id', 'view_id', 'scene', 'method', 'repeat')}
        rows[key].update(task_sha256=_digest(task), status='pipeline_error', error='missing_task_record',
            execution_state='missing_record', terminal=None, reference_applicable=None, na_reason=None,
            metrics={str(k): dict.fromkeys(METRICS) for k in (1, 5, 10)}, usage=None, components=None, secondary=None)
    indexed = {(r['root_task_id'], r['scene'], r['method']): r for r in rows.values()}
    for cohort, scenes in (('U8', ORIGINAL), ('UQ', ('Q1', 'Q2'))):
        expected = [u for u in users if all(plan['applicability'][u][s] for s in scenes)]
        _require(sorted(plan['cohorts'][cohort], key=lambda p: p.encode()) == expected, 'cohort_mismatch')
    pairs = []
    for user in users:
        x8 = {method: _average([indexed[user, s, method]['metrics']['10']['SJ_NDCG'] for s in ORIGINAL])
              for method in ('R', 'S', 'M')}
        xq = {mode: _average([(indexed[user, s, 'M']['components'] or {}).get(mode, {}).get('SJ_C') for s in ('Q1', 'Q2')])
              for mode in ('full', 'no_quality', 'mean_quality')}
        deltas = {}
        for label, a, b, cohort in (('C1', x8['M'], x8['S'], 'U8'), ('C2', x8['M'], x8['R'], 'U8'),
                ('C3', xq['full'], xq['no_quality'], 'UQ'), ('C4', xq['full'], xq['mean_quality'], 'UQ')):
            deltas[label] = a-b if user in plan['cohorts'][cohort] and a is not None and b is not None else None
        applicable_scenes = [s for s in ORIGINAL if plan['applicability'][user][s]]
        conditional = {m: _average([indexed[user, s, m]['metrics']['10']['SJ_NDCG'] for s in applicable_scenes])
                       for m in ('R', 'S', 'M')}
        pairs.append({'root_task_id': user, 'X8': x8, 'XQ': xq, **deltas,
                      'conditional_original8': conditional, 'conditional_weight_mass': len(applicable_scenes)/8})
    comparisons = {}
    for label, cohort in (('C1', 'U8'), ('C2', 'U8'), ('C3', 'UQ'), ('C4', 'UQ')):
        values = [r[label] for r in pairs if r['root_task_id'] in plan['cohorts'][cohort]]
        comparisons[label] = {'n': len(values), 'estimate': _average(values), 'interval': None, 'cohort': cohort}
    resampling = {}
    for cohort, labels, seed in (('U8', ('C1', 'C2'), 20261016), ('UQ', ('C3', 'C4'), 20261017)):
        group = [r for r in pairs if r['root_task_id'] in plan['cohorts'][cohort]]
        n = len(group)
        active = [label for label in labels if comparisons[label]['estimate'] is not None]
        digest, samples, rng = hashlib.sha256(), {label: [] for label in active}, random.Random(seed)
        if n >= 2 and active:
            for _ in range(50000):
                indices = [rng.randrange(n) for _ in range(n)]
                digest.update(b''.join(i.to_bytes(4, 'big') for i in indices))
                for label in active:
                    samples[label].append(math.fsum(group[i][label] for i in indices) / n)
        index_sha = digest.hexdigest() if n >= 2 and active else None
        resampling[cohort] = {'seed': seed, 'B': 50000, 'quantile': 'type7', 'tails': [.00625, .99375],
            'index_sha256': index_sha, 'index_encoding': 'uint32be_row_major', 'users_sha256': _digest([r['root_task_id'] for r in group])}
        for label in labels:
            comparison = comparisons[label]
            comparison['index_sha256'] = index_sha
            comparison['status'] = 'incomplete' if label not in active else 'n_lt_2' if n < 2 else 'estimated'
            comparison['degenerate'] = None
            comparison['max_endpoint_distance'] = None
            if n >= 2 and label in active:
                values = sorted(samples[label])
                interval = []
                for p in (.00625, .99375):
                    h = (len(values)-1)*p
                    k = math.floor(h)
                    interval.append((1-(h-k))*values[k]+(h-k)*values[k+1])
                comparison['interval'] = interval
                comparison['degenerate'] = len({r[label] for r in group}) == 1 or interval[0] == interval[1]
                comparison['max_endpoint_distance'] = max(abs(comparison['estimate']-v) for v in interval)
    counts = {'planned_tasks': len(tasks), 'missing_records': len(missing),
        'pipeline_errors': sum(r['status'] == 'pipeline_error' for r in rows.values()),
        'not_started': sum(r['execution_state'] == 'not_started' for r in rows.values()),
        'unresolved': sum(r['execution_state'] == 'unresolved' for r in rows.values()),
        'executed_failed': sum(r['execution_state'] == 'failed' for r in rows.values()),
        'reference_NA': sum(r['reference_applicable'] is False for r in rows.values())}
    complete = not any(counts[k] for k in ('pipeline_errors', 'not_started', 'unresolved'))
    scenes = [_scene_report(scene, method, [indexed[u, scene, method] for u in users], plan['applicability'])
              for scene in SCENES for method in (('M',) if scene.startswith('Q') else ('R', 'S', 'M'))]
    return {'status': 'complete' if complete else 'incomplete', 'plan_id': plan['plan_id'], 'users': pairs,
            'comparisons': comparisons, 'counts': counts, 'task_scores': [rows[k] for k in tasks],
            'scenes': scenes, 'usage': _usage_report(list(rows.values())),
            'usage_unattributed_tasks': sum(not r['usage'] or r['usage'].get('basis', 'unknown') == 'unknown' for r in rows.values()),
            'cost': {'total_microusd': None, 'pricing_status': 'unbound'},
            'resampling': resampling,
            'family_status': 'estimated' if all(c['interval'] is not None for c in comparisons.values()) else 'not_fully_estimated',
            'interval_interpretation': '98.75% marginal; approximate simultaneous 95%; conditional on fixed sources',
            'sample_sufficiency': 'not_claimed', 'historical_planning_n': 975}


def _public_path(value):
    path = Path(value).absolute()
    _require('..' not in path.parts and path.is_relative_to(PUBLIC), 'public_fixture_path_required')
    _require(not any(p.exists() and (p.is_symlink() or p.is_junction()) for p in (path, *path.parents)), 'reparse_path')
    return path


def _fixture_ref(ref):
    path = _public_path(ref['path'])
    _require(path.stat().st_size == ref['bytes'] and ref['bytes'] <= 8*1024**2, 'fixture_binding_mismatch')
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'fixture_binding_mismatch')
    return json.loads(raw)


def _main():
    parser = argparse.ArgumentParser(description='Handwritten public fixtures only; no real experiment execution.')
    parser.add_argument('--fixture-manifest', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    try:
        manifest_path, output = _public_path(args.fixture_manifest), _public_path(args.output_root)
        _require(not output.exists(), 'output_conflict')
        _require(manifest_path.stat().st_size <= 8192, 'invalid_fixture_manifest')
        raw_manifest = manifest_path.read_bytes()
        manifest = json.loads(raw_manifest)
        _require(set(manifest) == {'schema_version', 'source_scope', 'plan', 'observations'}
                 and manifest['schema_version'] == 'public-evaluation-fixture-0.1.0'
                 and manifest['source_scope'] == 'public_fixture', 'public_fixture_required')
        plan, observations = _fixture_ref(manifest['plan']), _fixture_ref(manifest['observations'])
        _require(plan['source_scope'] == 'public_fixture' and 1 <= len(plan['users']) <= 4
                 and all(u.startswith('PUBLIC-') for u in plan['users'])
                 and plan['model_binding'] == dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget')),
                 'public_fixture_required')
        scores = [score_task(row['task'], row['execution'], row['reference']) for row in observations]
        result = summarize(plan, scores)
        stage = output.with_name(output.name + '.staging-' + uuid.uuid4().hex)
        stage.mkdir(parents=True)
        parts = {'task-scores.jsonl': result.pop('task_scores'), 'user-pairs.jsonl': result.pop('users'),
                 'scene-summary.jsonl': result.pop('scenes')}
        components = {}
        for name, rows in parts.items():
            raw = b''.join(_wire(row)+b'\n' for row in rows)
            with (stage/name).open('xb') as stream:
                stream.write(raw)
            components[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'records': len(rows)}
        raw_summary = _wire(result)+b'\n'
        with (stage/'summary.json').open('xb') as stream:
            stream.write(raw_summary)
        components['summary.json'] = {'bytes': len(raw_summary), 'sha256': hashlib.sha256(raw_summary).hexdigest()}
        delivery = {'status': 'public_fixture_complete' if result['status'] == 'complete' else 'public_fixture_incomplete',
            'fixture_only': True, 'real_evaluations': 0, 'real_recommendations': 0, 'real_statistics': 0,
            'provider_requests_sent': 0, 'sample_sufficiency': 'not_claimed', 'plan_id': plan['plan_id'],
            'inputs': {'manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(), 'plan': manifest['plan'],
                       'observations': manifest['observations']},
            'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'components': components}
        with (stage/'manifest.json').open('xb') as stream:
            stream.write(_wire(delivery)+b'\n')
        os.rename(stage, output)
        print(json.dumps({'status': delivery['status'], 'fixture_only': True, 'real_evaluations': 0,
                          'provider_requests_sent': 0, 'output_root': str(output)}))
        return 0 if result['status'] == 'complete' else 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'public_fixture_failed', 'fixture_only': True, 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(_main())
