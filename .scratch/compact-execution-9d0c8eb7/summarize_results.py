"""Read the completed independent evaluation; never sends or changes experiment inputs."""
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compact_experiment import OUTPUT, load_config
from experiment_runner import _source_row


def read(path):
    return json.loads(path.read_bytes())


def lines(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def mean(values):
    return math.fsum(values) / len(values) if values and all(v is not None for v in values) else None


def percentile(values, p):
    h = (len(values) - 1) * p
    k = math.floor(h)
    return values[k] + (values[min(k + 1, len(values) - 1)] - values[k]) * (h - k)


def intervals(rows, seed):
    """Exploratory user-paired bootstrap, never a replacement for frozen C1-C4."""
    if not rows:
        return {}
    n, labels = len(rows), list(rows[0])
    result = {label: {'n': n, 'estimate': mean([r[label] for r in rows]), 'interval': None} for label in labels}
    if n < 2:
        return result
    samples, rng, digest = {k: [] for k in labels}, random.Random(seed), hashlib.sha256()
    for _ in range(50000):
        indices = [rng.randrange(n) for _ in range(n)]
        digest.update(b''.join(i.to_bytes(4, 'big') for i in indices))
        for label in labels:
            samples[label].append(math.fsum(rows[i][label] for i in indices) / n)
    for label in labels:
        values = sorted(samples[label])
        result[label].update(interval=[percentile(values, .025), percentile(values, .975)],
            level=.95, B=50000, seed=seed, quantile='type7', index_sha256=digest.hexdigest(),
            scope='exploratory; unadjusted; fixed sources; independent unit=user',
            degenerate=len({r[label] for r in rows}) == 1)
    return result


def metric_summary(users, get):
    result = {}
    for k in ('1', '5', '10'):
        result[k] = {}
        for metric in ('HR', 'NDCG_P'):
            values = [mean([get(u, scene, k, metric) for scene in V]) for u in users]
            known = [v for v in values if v is not None]
            result[k][metric] = {'n': len(known), 'planned_n': len(users),
                'estimate': mean(values), 'observed_complete_user_mean': mean(known)}
    return result


def fmt(v):
    return '未完成/不适用' if v is None else f'{v:.6f}'


def ci(v):
    return '未估计' if v is None else '[' + ', '.join(fmt(x) for x in v) + ']'


V = [f'V{i:02d}' for i in range(16)]
cfg = load_config()
evaluation = OUTPUT / 'evaluation' / cfg['configuration_id']
summary_path = evaluation / 'summary.json'
summary = read(summary_path)
assert summary['configuration_id'] == cfg['configuration_id']
users = cfg['users']
scores = {(r['root_task_id'], r['scene'], r['method']): r for r in summary['task_scores']}
tasks = [read(p) for p in (OUTPUT / 'tasks').glob('*.json')]
profiles = {p.stem: read(p) for p in (OUTPUT / 'profiles').glob('*.json')}
components = {}
for r in lines(evaluation / 'component-scores.jsonl'):
    # task_key is content-bound to the independent score row.
    components[r['task_key'], r['mode']] = r['metrics']
task_index = {r['task_key']: r for r in summary['task_scores']}
parts = {(task_index[key]['root_task_id'], task_index[key]['scene'], mode): metrics
         for (key, mode), metrics in components.items()}

method_metrics = {method: metric_summary(users, lambda u, s, k, m: scores[u, s, method]['metrics'][k][m])
                  for method in ('R', 'S', 'M')}
component_metrics = {mode: metric_summary(users, lambda u, s, k, m: parts.get((u, s, mode), {}).get(k, {}).get(m))
                     for mode in ('full', 'base', 'uniform_weights', 'no_quality', 'mean_quality', 'no_feedback')}
feedback_rows, real_rows = [], []
for u in users:
    row = {f'{method}_{metric}': mean([scores[u, s, method]['metrics']['10'][metric] for s in V])
           for method in ('R', 'S', 'M') for metric in ('HR', 'NDCG_P')}
    if all(v is not None for v in row.values()):
        real_rows.append(row | {'M_minus_S_NDCG_P': row['M_NDCG_P'] - row['S_NDCG_P'],
                               'M_minus_R_NDCG_P': row['M_NDCG_P'] - row['R_NDCG_P']})
    row = {f'{mode}_{metric}': mean([parts.get((u, s, mode), {}).get('10', {}).get(metric) for s in V])
           for mode in ('full', 'no_feedback') for metric in ('HR', 'NDCG_P')}
    if all(v is not None for v in row.values()):
        feedback_rows.append(row | {f'delta_{metric}': row[f'full_{metric}'] - row[f'no_feedback_{metric}']
                                   for metric in ('HR', 'NDCG_P')})

ranking_changes = {}
for scope, selected_scenes in (('V16', set(V)), ('Q1', {'Q1'}), ('Q2', {'Q2'})):
    anchors = [r for r in tasks if r['method'] == 'M' and r['scene'] in selected_scenes and r['status'] == 'ok']
    ranking_changes[scope] = {}
    for mode in ('base', 'uniform_weights', 'no_quality', 'mean_quality', 'no_feedback'):
        observed = [r for r in anchors if mode in r['components']]
        ranking_changes[scope][mode] = {'successful_anchor_tasks': len(observed),
            'top10_sequence_changed': sum(r['topK'] != r['components'][mode]['topK'] for r in observed),
            'top10_set_changed': sum(set(r['topK']) != set(r['components'][mode]['topK']) for r in observed)}

intents = [read(p) for p in (OUTPUT / 'calls').glob('*.intent.json')]
results = [read(p) for p in (OUTPUT / 'calls').glob('*.result.json')]
assert len({r['request_id'] for r in intents}) == len(intents) <= 700
assert len({r['request_id'] for r in results}) == len(results)
assert {r['request_id'] for r in results} <= {r['request_id'] for r in intents}
usage = {}
for field in ('input_tokens', 'output_tokens', 'total_tokens'):
    known = [r.get('usage', {}).get(field) for r in results]
    known = [v for v in known if type(v) is int]
    usage[field] = {'known_subtotal': sum(known), 'unknown_attempts': len(intents) - len(known),
                    'total': sum(known) if len(known) == len(intents) else None}
scenes = [read(p)['shared_preprocessing_usage'] for p in (OUTPUT / 'scenes').glob('*.json')]
shared = {field: sum(r[field] for r in scenes) for field in ('candidates', 'elapsed_ms', 'logical_tools', 'physical_tools')}
start = read(OUTPUT / 'started.json')
run_terminal = read(HERE / 'run-terminal.json')
eval_terminal = read(HERE / 'evaluation-terminal.json')
task_by_user = Counter(r['root_task_id'] for r in tasks)
task_status = Counter(r['status'] for r in tasks)
ok_users = [u for u in users if task_by_user[u] == 50 and all(r['status'] == 'ok' for r in tasks if r['root_task_id'] == u)]
failed_users = {r['root_task_id'] for r in tasks if r['status'] != 'ok'}
u8 = {r['root_task_id'] for r in summary['users'] if r['C1'] is not None}
cohort_check = {'U8_n': len(u8), 'U8_users_with_retained_model_failure': len(u8 & failed_users),
    'U8_original8_failed_task_rows': sum(r['execution_state'] == 'failed' and r['root_task_id'] in u8
        and r['scene'] in ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12') for r in summary['task_scores']),
    'basis': 'independent reference applicability; not a successful-execution filter'}
changed, weighted_changed, successful_M = 0, 0, 0
for u in users:
    profile = profiles.get(u + '-M', {})
    if profile.get('status') == 'ok':
        successful_M += 1
        before, after = profile['before_feedback']['selections'], profile['profile']['selections']
        changed += before != after
        weighted_changed += {r['option_id']: r['weight'] for r in before} != {r['option_id']: r['weight'] for r in after}
history_counts, unique_history, targets = [], [], Counter()
for reference in lines(ROOT / cfg['plan_directory'] / 'root-references.jsonl'):
    root = _source_row(reference['root_ref'])
    history_counts.append(len(root['history']))
    unique_history.append(len({r['parent_asin'] for r in root['history']}))
# Target distribution is read only from evaluation-owned references, after independent evaluation.
from formal_evaluation import source_references
pref = source_references()['preference']
for r in lines(ROOT / pref['path']):
    if r.get('root') in set(users):
        target = r.get('target_parent')
        if target is not None:
            targets[target] += 1
assert len(history_counts) == 100 and sum(targets.values()) == 100

resources = {'generation_intents': len(intents), 'generation_results': dict(Counter(r['status'] for r in results)),
    'unresolved_generations': len(intents) - len(results), 'native_usage': usage,
    'shared_preprocessing': shared, 'started_epoch': start['deadline'] - 24 * 3600,
    'deadline_epoch': start['deadline'], 'run_terminal': run_terminal, 'evaluation_terminal': eval_terminal,
    'run_seconds': run_terminal['ended_epoch'] - (start['deadline'] - 24 * 3600),
    'evaluation_seconds': eval_terminal['ended_epoch'] - eval_terminal['started_epoch'],
    'run_plus_evaluation_seconds': run_terminal['ended_epoch'] - (start['deadline'] - 24 * 3600)
        + eval_terminal['ended_epoch'] - eval_terminal['started_epoch'],
    'shared_budget_elapsed_seconds': eval_terminal['ended_epoch'] - (start['deadline'] - 24 * 3600),
    'between_stages_wait_seconds': eval_terminal['started_epoch'] - run_terminal['ended_epoch'],
    'experiment_output_bytes': sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()),
    'execution_scratch_bytes_at_report': sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()),
    'pricing': None, 'cost': None, 'caps': {'generations': 700, 'hours': 24, 'new_bytes': 10 * 1024**3}}
report = {'protocol': cfg['protocol'], 'configuration_id': cfg['configuration_id'],
    'parent_plan_id': cfg['parent_plan_id'], 'evaluation_summary_ref': {
        'path': str(summary_path), 'sha256': hashlib.sha256(summary_path.read_bytes()).hexdigest()},
    'terminal': summary['status'], 'planned_users': 100, 'planned_tasks': 5000, 'planned_model_tasks': 3400,
    'users_with_50_terminal_rows': sum(task_by_user[u] == 50 for u in users),
    'users_all_methods_ok': len(ok_users), 'tasks_recorded': len(tasks), 'task_status': dict(task_status),
    'uncompleted_task_rows': 5000 - len(tasks), 'evaluation_counts': summary['counts'],
    'SIM_secondary': {
        'tasks_with_observed_secondary': sum(r.get('secondary') is not None for r in summary['task_scores']),
        'necessary_condition_or_execution_failure_tasks': sum((r.get('secondary') or {}).get('failure', 0) for r in summary['task_scores']),
        'tasks_with_any_violation': sum((r.get('secondary') or {}).get('any_violation', 0) for r in summary['task_scores']),
        'violating_delivered_items': sum((r.get('secondary') or {}).get('violation_items', 0) for r in summary['task_scores']),
        'delivered_items': sum((r.get('secondary') or {}).get('delivered_items', 0) for r in summary['task_scores'])},
    'profile_status': {m: dict(Counter(profiles[u + '-' + m]['status'] for u in users if u + '-' + m in profiles))
                       for m in ('R', 'S', 'M')},
    'failed_profile_diagnosis': dict(Counter(r['offline_validation_error']
        for r in read(HERE / 'failure-audit.json')['profiles'])),
    'resources': resources, 'real_preference_all16V': method_metrics,
    'exploratory_real_preference_at10': intervals(real_rows, 20261023),
    'primary_comparisons': summary['comparisons'], 'primary_interval_interpretation': summary['interval_interpretation'],
    'primary_cohort_checks': cohort_check,
    'quality_scenes': [r for r in summary['scenes'] if r['scene'].startswith('Q')],
    'ranking_changes_on_same_actual_anchor': ranking_changes,
    'component_preference_all16V': component_metrics,
    'feedback': {'successful_M_profiles': successful_M, 'content_changed': changed,
                 'selection_or_weight_changed': weighted_changed, 'conditional_users': len(feedback_rows),
                 'exploratory_at10': intervals(feedback_rows, 20261023)},
    'sample': {'history_records': dict(Counter(history_counts)), 'unique_history_parents': dict(Counter(unique_history)),
               'median_history_records': statistics.median(history_counts), 'target_parents': dict(targets)},
    'limits': ['Fixed 100 users; scenes are repeated measures, not independent users.',
               'SIM qualification is distinct from real preference and real product safety.',
               'Scoring/profile components are not rerun end-to-end role ablations.',
               'M uses more inference than S; role and compute effects are confounded.',
               'Unknown usage and total cost remain null; failed calls are retained.']}
(HERE / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
with (HERE / 'scene-results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    cols = ['scene', 'method', 'planned_n', 'reference_applicable_n', 'status', 'HR@10', 'NDCG_P@10', 'SJ_NDCG@10',
            'failure', 'any_violation', 'necessary_satisfied', 'qualified_coverage', 'fill']
    writer = csv.DictWriter(stream, fieldnames=cols)
    writer.writeheader()
    for r in summary['scenes']:
        writer.writerow({'scene': r['scene'], 'method': r['method'], 'planned_n': r['planned'],
            'reference_applicable_n': r['applicable'], 'status': r['status'],
            **{name + '@10': r['metrics']['10'][name] for name in ('HR', 'NDCG_P', 'SJ_NDCG')},
            **{name: r['secondary'][name] for name in cols[8:]}})

out = ['# 100 用户全场景实验实际结果', '', f"协议：{cfg['protocol']}；配置：{cfg['configuration_id']}", '',
       f"终态：{summary['status']}。{report['users_with_50_terminal_rows']}/100 用户已具备全部 50 条终态记录；"
       f"{report['users_all_methods_ok']} 位用户的所有方法均成功。任务记录 {len(tasks)}/5000，状态 {dict(task_status)}，"
       f"未完成 {report['uncompleted_task_rows']} 条。评价计数：{summary['counts']}。", '',
       f"生成意图 {len(intents)}，返回 {resources['generation_results']}，未决 {resources['unresolved_generations']}；"
       f"实际 usage：{usage}。单价与总费用均为 null。运行 {resources['run_seconds']:.1f} 秒，"
       f"运行加评价 {resources['run_plus_evaluation_seconds']:.1f} 秒；实验产物 {resources['experiment_output_bytes']} 字节。", '',
       '真实偏好：全部16个V场景先按用户等权平均。未命中的真实目标为0；终结失败按既定口径计入。', '',
       '| 方法 | 有效/计划用户 | HR@10 | NDCG@10 |', '|---|---:|---:|---:|']
for method, values in method_metrics.items():
    out.append(f"| {method} | {values['10']['NDCG_P']['n']}/100 | {fmt(values['10']['HR']['estimate'])} | {fmt(values['10']['NDCG_P']['estimate'])} |")
out += ['', '预定主比较（SJ-NDCG@10，98.75%边际区间；近似家族同时覆盖95%，条件于固定资料）：', '',
        '| 比较 | 有效人数 | 差值 | 区间 |', '|---|---:|---:|---|']
for label, r in summary['comparisons'].items():
    out.append(f"| {label} ({r['cohort']}) | {r['n']} | {fmt(r['estimate'])} | {ci(r['interval'])} |")
out += ['', 'C1=M−S，C2=M−R（原8共同适用场景）；C3=full−no_quality，C4=full−mean_quality（Q1/Q2共同适用人群）。', '',
        f"U8按独立参考适用性确定，共 {len(u8)} 人，其中 {len(u8 & failed_users)} 人存在保留的模型失败。"
        '它不是排除模型失败后的成功用户子集；主比较保留该人群内的失败。', '',
        f"核验前后：{successful_M} 个成功M画像，其中列表（含顺序）改变 {changed}，选项或权重改变 {weighted_changed}；"
        f"对应组件完整的条件人数 {len(feedback_rows)}。探索性95%用户成对区间见 results.json；不替代主比较。", '',
        'SIM资格、逐场景适用人数、失败和违规见 scene-results.csv 与独立 summary.json；Q场景仅有M和其评分组件。', '',
        '质量组件和核验前后均共享实际材料。模型失败不重跑，未完成不补值；18场景不增加独立样本量。'
        'M/S调用量不同，不能把差异单独归因于角色分工。Fabric未部署，未填入账本性能。', '',
        '完整审计：`data/recommendation-runtime-audit/personalized-compact-0.1.0/`。']
out += ['', '真实偏好@10的探索性95%用户重采样区间（未经多重比较调整，不能替代预定主比较）：', '',
        '| 方法 | 有效人数 | HR@10区间 | NDCG@10区间 |', '|---|---:|---|---|']
for method in ('R', 'S', 'M'):
    a = report['exploratory_real_preference_at10'].get(method + '_HR', {})
    b = report['exploratory_real_preference_at10'].get(method + '_NDCG_P', {})
    out.append(f"| {method} | {b.get('n', 0)} | {ci(a.get('interval'))} | {ci(b.get('interval'))} |")
out += ['', 'Q1/Q2质量评分组件（留出目标SJ-NDCG@10；包括预设锚点失败计0规则）：', '',
        '| 场景 | 参考适用人数 | full | no_quality | mean_quality |', '|---|---:|---:|---:|---:|']
for r in report['quality_scenes']:
    out.append(f"| {r['scene']} | {r['applicable']}/100 | " + ' | '.join(fmt(r['components'][m])
               for m in ('full', 'no_quality', 'mean_quality')) + ' |')
out += ['', '全部16个V场景的M评分组件（仅具备完整实际组件的用户，主比较仍保留失败）：', '',
        '| 组件 | 条件人数 | HR@10 | NDCG@10 |', '|---|---:|---:|---:|']
for mode, values in component_metrics.items():
    a, b = values['10']['HR'], values['10']['NDCG_P']
    out.append(f"| {mode} | {b['n']} | {fmt(a['observed_complete_user_mean'])} | {fmt(b['observed_complete_user_mean'])} |")
out += ['', '核验后−核验前的探索性成对差（上述成功M条件人群；95%区间，未经多重比较调整）：', '',
        '| 指标 | 有效人数 | 差值 | 区间 |', '|---|---:|---:|---|']
for metric in ('HR', 'NDCG_P'):
    r = report['feedback']['exploratory_at10'].get('delta_' + metric, {})
    out.append(f"| {metric}@10 | {r.get('n', 0)} | {fmt(r.get('estimate'))} | {ci(r.get('interval'))} |")
out += ['', f"SIM独立参考核对计数：{report['SIM_secondary']}。这些计数不等于真实偏好或现实商品安全。", '',
        f"失败画像只读归因：{report['failed_profile_diagnosis']}；没有重发请求或修改失败结果。", '',
        f"样本历史记录长度分布：{report['sample']['history_records']}；不同历史父商品数分布："
        f"{report['sample']['unique_history_parents']}；留出目标涉及 {len(targets)} 个父商品。", '',
        f"阶段耗时：运行 {resources['run_seconds']:.1f} 秒，评价 {resources['evaluation_seconds']:.1f} 秒，"
        f"两者合计 {resources['run_plus_evaluation_seconds']:.1f} 秒；阶段间等待 {resources['between_stages_wait_seconds']:.1f} 秒。"
        f"24小时共享预算起算至评价结束累计 {resources['shared_budget_elapsed_seconds']:.1f} 秒（含等待）。", '',
        '区间条件于固定样本与来源。若重采样区间退化为[0,0]，仅表示本样本的差值没有变化，不能据此断言总体误差为零或方法等效。']
(HERE / 'results.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ('terminal', 'users_with_50_terminal_rows', 'tasks_recorded', 'task_status')}, ensure_ascii=False))
