"""Read-only pilot metering and development-only zero-hit audit. No provider API."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evidence_access import encoded, digest
from formal_runtime import PACKAGE, PLAN
from development_evaluation import read

outcomes_path = ROOT / '.scratch/ticket14-q-contract-20261022/task-outcomes.json'
outcomes = json.loads(outcomes_path.read_bytes())
report = json.loads(read(outcomes['evaluation_artifacts']['evaluation.json']))
preference = [json.loads(raw) for raw in read(report['projection_sources']['preference']).splitlines()]
assert len(preference) == 1 and preference[0]['group'] == 'dev'
target, user = preference[0]['target_parent'], preference[0]['root']
scores = {r['task_key']: r for r in (json.loads(raw) for raw in
    read(outcomes['evaluation_artifacts']['task-scores.jsonl']).splitlines())}
measurements, checks = [], []
for row in outcomes['rows']:
    audit = json.loads(read(row['audit_ref']))
    assert audit['binding']['root_task_id'] == user
    delivered = audit['delivered']
    rank = delivered.index(target) + 1 if target in delivered else None
    expected = {'HR': int(rank is not None and rank <= 10),
        'NDCG_P': 1 / math.log2(rank + 1) if rank is not None and rank <= 10 else 0}
    recorded = scores[row['task_key']]['metrics']['10']
    checks.append({'task_key': row['task_key'], 'scene': row['scene'], 'method': row['method'],
        'target_in_C': target in audit['binding']['C'], 'target_in_actual_G': target in audit['G'],
        'target_delivered_rank': rank, 'delivered_count': len(delivered),
        'HR_at_10': recorded['HR'], 'NDCG_P_at_10': recorded['NDCG_P'],
        'independent_calculation_agrees': all(recorded[k] == v for k, v in expected.items())})
    directory = (ROOT / row['audit_ref']['path']).parent
    parts = dict.fromkeys(('audit', 'publication', 'budget', 'requests', 'responses', 'acquired', 'other'), 0)
    for p in directory.rglob('*'):
        if not p.is_file():
            continue
        name = p.name
        category = ('audit' if name.startswith('audit') else 'publication' if name.startswith('publication')
            else 'budget' if name == 'budget.jsonl' else 'requests' if name.startswith('request-')
            else 'responses' if name.startswith('response-') else 'acquired' if name.startswith('acquired-') else 'other')
        parts[category] += p.stat().st_size
    result_ref = row.get('result_ref')
    result = json.loads(read(result_ref)) if result_ref else {}
    usage = row.get('usage') or {}
    seconds = (result.get('budget_usage') or audit['budget']['usage']).get('elapsed_ms', 0) / 1000
    measurements.append({'scene': row['scene'], 'method': row['method'], 'calls': row['selected_model_calls'],
        'input_tokens': usage.get('input_tokens', 0), 'output_tokens': usage.get('output_tokens', 0),
        'seconds': seconds, 'bytes': sum(parts.values()), 'disk_components': parts})
assert len(checks) == 8 and all(c['target_in_C'] and c['independent_calculation_agrees'] for c in checks)
zero_audit = {'scope': 'one_development_user_only', 'formal_users_read': 0,
    'evaluation_ref': outcomes['evaluation_artifacts']['evaluation.json'], 'checks': checks,
    'conclusion': 'eight_real_misses_no_association_or_HR_NDCG_calculation_error_detected',
    'target_identifier_disclosed': False, 'supplier_calls': 0}
(PACKAGE / 'development-zero-hit-audit.json').write_bytes(encoded(zero_audit) + b'\n')
ordinary = [r for r in measurements if r['method'] != 'R' and not r['scene'].startswith('Q')]
quality = [r for r in measurements if r['scene'].startswith('Q')]
rules = [r for r in measurements if r['method'] == 'R']
means = {name: {field: sum(r[field] or 0 for r in group) / len(group)
    for field in ('input_tokens', 'output_tokens', 'seconds', 'bytes')}
    for name, group in (('ordinary', ordinary), ('quality', quality), ('rule', rules))}
normal = {field: 3200 * means['ordinary'][field] + 200 * means['quality'][field] + 1600 * means['rule'][field]
    for field in ('input_tokens', 'output_tokens', 'seconds', 'bytes')}
normal['generations'] = 3200 * 9 + 200 * 16
disk_projection = {part: sum(count * sum(r['disk_components'][part] for r in group) / len(group)
    for count, group in ((3200, ordinary), (200, quality), (1600, rules))) for part in measurements[0]['disk_components']}
budget = {'scope': 'frozen_100_users_18_scenes_one_repeat', 'tasks': 5000, 'model_tasks': 3400,
    'ordinary_model_tasks': 3200, 'quality_model_tasks': 200, 'rule_tasks': 1600,
    'pilot_measurements': measurements, 'pilot_means': means, 'normal_projection': normal,
    'normal_disk_components_bytes': disk_projection,
    'normal_concurrency_seconds_ideal': {str(n): normal['seconds'] / n for n in (1, 2, 4)},
    'conservative': {'generations': 61200, 'input_tokens_scenario': 61200 * 2 * 1024**2,
        'input_assumption': 'one_token_per_UTF8_request_byte_at_2MiB; not_verified_count_or_token_hard_bound',
        'requested_output_tokens_ceiling': 3400 * (17 * 8192 + 1500),
        'serial_task_watchdogs_seconds': 5000 * 1800,
        'task_storage_bytes': 5000 * 128 * 1024**2, 'shared_storage_bytes': 640 * 1024**3,
        'minimum_free_bytes': 20 * 1024**3},
    'pricing': None, 'cost': None, 'supplier_calls': 0,
    'limitations': ['one_development_user; other_scenes_and_users_unmeasured',
        'normal_path_assumes_one_ordinary_acquisition_batch_no_revision',
        'elapsed_projection_excludes_future_coordination_evaluation_and_throttling',
        'normal_R_projection_uses_legacy_R_artifact_shape; conservative_limit_controls_new_traces']}
(PACKAGE / 'budget.json').write_bytes(encoded(budget) + b'\n')
print(json.dumps({'normal': normal, 'means': means, 'HR_check': zero_audit['conclusion'], 'supplier_calls': 0}))
