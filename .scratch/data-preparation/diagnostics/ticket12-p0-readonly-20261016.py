"""One authorized P0 diagnostic, not a preparation CLI or model runner.

Standard library only. Existing components are read-only; targets stay in the
local private audit. No test-user scoring, recommendation metrics or network IO.
Public DEMO examples execute before reading any accepted data component.
"""

from collections import Counter, defaultdict
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import median, NormalDist
import sys
import time
import unicodedata


ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / '.scratch/data-preparation/verification'
PRIVATE = ROOT / 'data/evaluation-audit/ticket12-p0-20261016'
AGGREGATE = PUBLIC / 'ticket12-p0-20261016-aggregate.json'
MICRO = PUBLIC / 'ticket12-p0-20261016-micro.json'
MAIN_VIEWS = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12')
PROFILE = 'R1_AND_R5_SIM_Q1_ON_SALE'
VIEWS = tuple(f'V{i:02}' for i in range(16))
P8 = 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1.json'
A8 = 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1-acceptance.json'
P11 = 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json'
A11 = 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json'
PN = 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
AN = 'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json'
INPUTS = {}
START = time.perf_counter()


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
        (name, ctypes.c_size_t) for name in (
            'peak_working_set', 'working_set', 'peak_paged_pool', 'paged_pool',
            'peak_nonpaged_pool', 'nonpaged_pool', 'pagefile', 'peak_pagefile',
            'private_usage')]


def resource_check():
    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = (ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong)
    if not query(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise RuntimeError('resource_measurement_failed')
    elapsed = time.perf_counter() - START
    if elapsed > 1800 or max(counters.peak_working_set, counters.peak_pagefile) > 4 * 1024**3:
        raise RuntimeError('p0_resource_limit_exceeded')
    return {'elapsed_seconds': elapsed,
            'peak_working_set_bytes': counters.peak_working_set,
            'peak_private_commit_bytes': counters.peak_pagefile,
            'current_private_bytes': counters.private_usage,
            'limit_seconds': 1800, 'limit_bytes': 4 * 1024**3,
            'guard': 'checkpoint_time_and_windows_peak_memory'}


def insist(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(canonical(value) + '\n')


def resolve(path):
    p = (ROOT / path).resolve()
    insist(p.is_relative_to(ROOT), 'input_outside_project')
    return p


def record_digest(path, digest, size, expected=None):
    insist(expected is None or digest == expected, 'accepted_input_digest_mismatch')
    INPUTS[str(Path(path).as_posix())] = {'sha256': digest, 'bytes': size}


def load(path, expected=None):
    p = resolve(path)
    raw = p.read_bytes()
    record_digest(path, hashlib.sha256(raw).hexdigest(), len(raw), expected)
    return json.loads(raw)


def rows(path, expected=None):
    digest = hashlib.sha256()
    size = 0
    with resolve(path).open('rb') as stream:
        for i, line in enumerate(stream):
            digest.update(line)
            size += len(line)
            if i % 100 == 0:
                resource_check()
            yield json.loads(line)
    record_digest(path, digest.hexdigest(), size, expected)


def protect(path):
    digest = hashlib.sha256()
    size = 0
    with resolve(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            resource_check()
    record_digest(path, digest.hexdigest(), size)


def summary(values):
    values = sorted(values)
    if not values:
        return {'n': 0, 'min': None, 'median': None, 'p90': None, 'p95': None,
                'max': None, 'mean': None}
    n = len(values)
    return {'n': n, 'min': values[0], 'median': median(values),
            'p90': values[math.ceil(n*.9)-1], 'p95': values[math.ceil(n*.95)-1],
            'max': values[-1], 'mean': math.fsum(values)/n}


def concentration(counts):
    ranked = sorted(counts.values(), reverse=True)
    n = sum(ranked)
    hhi = math.fsum((v/n)**2 for v in ranked) if n else None
    return {'accounts_or_references': n, 'distinct_parents': len(ranked),
            'top_counts': {str(k): sum(ranked[:k]) for k in (1, 5, 10, 20)},
            'top_shares': {str(k): sum(ranked[:k])/n if n else None for k in (1, 5, 10, 20)},
            'hhi': hhi, 'inverse_hhi_diversity_only': 1/hhi if hhi else None,
            'singleton_parents': sum(v == 1 for v in ranked),
            'cluster_size_histogram': dict(sorted(Counter(ranked).items()))}


def reference_join(tasks, evaluations, states, main_views):
    insist(set(tasks) == set(evaluations), 'task_evaluation_keyset_mismatch')
    result = {}
    for key, task in tasks.items():
        ev = evaluations[key]
        target = ev['target_parent_asin']
        insist(target in task['candidate_parent_asins'], 'target_not_in_fixed_candidates')
        by_view = {}
        for view in states:
            insist(target in states[view], 'reference_target_missing')
            state = states[view][target]
            by_view[view] = {'applicable': state == 'Supported', 'target_state': state,
                             'reason': None if state == 'Supported' else 'reference_target_' + state}
        result[key] = {'all_main_applicable': all(by_view[v]['applicable'] for v in main_views),
                       'by_view': by_view}
    return result


def micro_examples():
    tasks = {'DEMO-U1': {'candidate_parent_asins': ['DEMO-A', 'DEMO-B']},
             'DEMO-U2': {'candidate_parent_asins': ['DEMO-A', 'DEMO-B']},
             'DEMO-U3': {'candidate_parent_asins': ['DEMO-A', 'DEMO-B']}}
    labels = {'DEMO-U1': {'target_parent_asin': 'DEMO-A'},
              'DEMO-U2': {'target_parent_asin': 'DEMO-B'},
              'DEMO-U3': {'target_parent_asin': 'DEMO-A'}}
    states = {'V00': {'DEMO-A': 'Supported', 'DEMO-B': 'Supported'},
              'V01': {'DEMO-A': 'Supported', 'DEMO-B': 'Pending'},
              'V05': {'DEMO-A': 'Supported', 'DEMO-B': 'Refuted'},
              'V06': {'DEMO-A': 'Supported', 'DEMO-B': 'Conflict'}}
    joined = reference_join(tasks, labels, states, tuple(states))
    insist(sum(r['all_main_applicable'] for r in joined.values()) == 2, 'micro_nj')
    insist(sum(r['by_view']['V01']['applicable'] for r in joined.values()) == 2, 'micro_app')
    insist(Counter(r['by_view']['V06']['reason'] for r in joined.values()) ==
            Counter({None: 2, 'reference_target_Conflict': 1}), 'micro_reason')
    reversed_join = reference_join(dict(reversed(list(tasks.items()))),
                                  dict(reversed(list(labels.items()))), states, tuple(states))
    insist(joined == reversed_join, 'micro_order')
    caught = 0
    for invalid_tasks, invalid_labels, invalid_states in (
        (tasks, {k: v for k, v in labels.items() if k != 'DEMO-U3'}, states),
        ({**tasks, 'DEMO-U1': {'candidate_parent_asins': ['DEMO-B']}}, labels, states),
        (tasks, labels, {**states, 'V01': {'DEMO-B': 'Pending'}})):
        try:
            reference_join(invalid_tasks, invalid_labels, invalid_states, tuple(states))
        except ValueError:
            caught += 1
    insist(caught == 3, 'micro_negative_associations')
    # Shared parents count twice as accounts, not once as a distinct product.
    insist(math.isclose(concentration(Counter({'DEMO-A': 2, 'DEMO-B': 1}))['hhi'], 5/9), 'micro_hhi')
    insist(summary([1, 1, 2])['median'] == 1, 'micro_summary')
    ranked = [('DEMO-A', .9), ('DEMO-B', .7), ('DEMO-C', .7)]
    top2 = sorted(ranked, key=lambda x: (-x[1], x[0].encode()))[:2]
    insist(len({'DEMO-B'} & {p for p, _ in top2}) == 1, 'micro_challenge_exposure')
    insist(normalize(' Ａ \n B ') == 'a b' and grams('x') == Counter({'x': 1}), 'micro_text_normalization')
    insist(tfidf(Counter({'aaa': 2}), {'aaa': 2}) == {'aaa': 1.0}, 'micro_tfidf_unit_norm')
    insist(tfidf(Counter({'zzz': 2}), {'aaa': 2}) == {}, 'micro_oov_zero')
    return {'status': 'passed', 'all_identifiers_are_public_demo': True,
            'expected_n_pool': 3, 'expected_n_J': 2,
            'expected_per_view_applicable': {'V00': 3, 'V01': 2, 'V05': 2, 'V06': 2},
            'expected_na_reasons': ['reference_target_Pending', 'reference_target_Refuted',
                                    'reference_target_Conflict'],
            'negative_cases_rejected': caught, 'line_order_invariance': True,
            'duplicate_target_accounts_preserved': True, 'topk_tie_order_checked': True}


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def grams(text):
    text = normalize(text)
    if not text:
        return Counter()
    return Counter(text[i:i+3] for i in range(len(text)-2)) if len(text) >= 3 else Counter({text: 1})


def tfidf(counts, idf):
    weights = {g: (1+math.log(counts[g]))*idf[g] for g in sorted(counts) if g in idf}
    norm = math.sqrt(math.fsum(v*v for v in weights.values()))
    return {g: v/norm for g, v in weights.items()} if norm else {}


def development_score(task, catalog, idf, vectors):
    """Only allowed model fields; no target, evaluation, S or reference input."""
    combined = defaultdict(float)
    text_oov = []; doc_oov = []; text_types = set(); text_oov_types = set()
    raw_text_zero = 0
    for event in task['history']:
        product = catalog[event['parent_asin']]
        raw = grams(event['text'])
        doc = grams(' '.join((event['text'], product['title'], product['crop'])))
        text_oov.append((sum(v for g, v in raw.items() if g not in idf), sum(raw.values())))
        doc_oov.append((sum(v for g, v in doc.items() if g not in idf), sum(doc.values())))
        text_types.update(raw)
        text_oov_types.update(set(raw)-idf.keys())
        raw_text_zero += not tfidf(raw, idf)
        vector = tfidf(doc, idf)
        for g, v in vector.items():
            combined[g] += event['rating']/5 * v
    norm = math.sqrt(math.fsum(combined[g]**2 for g in sorted(combined)))
    profile = {g: combined[g]/norm for g in sorted(combined)} if norm else {}
    raw_scores = []
    for parent in task['candidate_parent_asins']:
        dot = math.fsum(value*profile.get(g, 0) for g, value in vectors[parent].items())
        raw_scores.append((parent, round(dot, 12)))
    low = min(v for _, v in raw_scores); high = max(v for _, v in raw_scores)
    scores = [(p, round((v-low)/(high-low), 12) if high != low else .5) for p, v in raw_scores]
    ranked = sorted(scores, key=lambda x: (-x[1], x[0].encode('utf-8')))
    return {'scores': scores, 'top64': ranked[:64], 'profile_zero': not profile,
            'raw_text_zero': raw_text_zero, 'text_oov': text_oov, 'doc_oov': doc_oov,
            'text_types': text_types, 'text_oov_types': text_oov_types,
            'score_constant': high == low}


def subset_summary(ids, tasks, evaluations, catalog):
    target_counts = Counter(evaluations[k]['target_parent_asin'] for k in ids)
    depths = [len({h['parent_asin'] for h in tasks[k]['history']}) for k in ids]
    events = [len(tasks[k]['history']) for k in ids]
    times = [evaluations[k]['target_timestamp_ms'] for k in ids]
    crops = Counter(catalog[evaluations[k]['target_parent_asin']]['crop'] for k in ids)
    years = Counter(str(datetime.fromtimestamp(t/1000, timezone.utc).year) for t in times)
    history_parents = {h['parent_asin'] for k in ids for h in tasks[k]['history']}
    return {'accounts': len(ids), 'history_distinct_products': summary(depths),
            'history_depth_histogram': dict(sorted(Counter(depths).items())),
            'history_events': summary(events), 'history_parent_coverage': len(history_parents),
            'target_concentration': concentration(target_counts),
            'target_crop_counts': {c: crops[c] for c in sorted({r['crop'] for r in catalog.values()})},
            'target_year_counts_utc': dict(sorted(years.items())),
            'target_time_min_utc': datetime.fromtimestamp(min(times)/1000, timezone.utc).isoformat() if times else None,
            'target_time_max_utc': datetime.fromtimestamp(max(times)/1000, timezone.utc).isoformat() if times else None}


def main():
    insist(Path(sys.prefix).resolve() == ROOT/'.conda/envs/Thesis', 'wrong_conda_environment')
    insist(not PRIVATE.exists() and not AGGREGATE.exists() and not MICRO.exists(), 'diagnostic_output_already_exists')
    PUBLIC.mkdir(parents=True, exist_ok=True)
    private_parent = PRIVATE.parent.resolve()
    insist(private_parent.is_relative_to(ROOT), 'private_output_outside_project')
    micro = micro_examples()
    write_new(MICRO, micro)
    print('P0 public DEMO examples passed; accepted-data diagnostic starts.', flush=True)
    PRIVATE.mkdir(parents=True)

    for path in ('AGENTS.md', '.scratch/data-preparation/spec.md',
                 '.scratch/data-preparation/ticket12-stage1-joint-evaluation-review-draft-20261016.md',
                 '.scratch/data-preparation/diagnostics/ticket12-primary-source-notes-20261016.md',
                 '.scratch/data-preparation/issues/12-evaluation-sample-design.md',
                 '.scratch/data-preparation/issues/13-joint-task-package.md',
                 'research/数据修复方案与验收草案_20261010.md',
                 'manuscript/论文初稿_表达与实验结构修订版_20261010.docx',
                 '.scratch/data-preparation/diagnostics/ticket12-p0-readonly-20261016.py'):
        protect(path)
    a8 = load(A8); p8 = load(P8, a8['record_sha256'])
    a11 = load(A11); p11 = load(P11, a11['generation_record']['sha256'])
    an = load(AN); pn = load(PN, a11['normal_binding']['record']['sha256'])
    cfg = load('config/sim-normal-1.0.0.json', pn['inputs']['config']['sha256'])
    for key, ref in p8['components'].items():
        insist(ref['sha256'] == a8['component_sha256'][key], 'p8_acceptance_binding')

    catalog_rows = list(rows(p8['components']['catalog']['path'], p8['components']['catalog']['sha256']))
    catalog = {r['parent_asin']: r for r in catalog_rows}
    insist(len(catalog) == len(catalog_rows) == 1494, 'catalog_duplicate_or_count')
    plans = list(rows(p11['audit_private']['mutation-plan.jsonl']['path'],
                      p11['audit_private']['mutation-plan.jsonl']['sha256']))
    labels_by_view = {p['view_id']: p['view_name'] for p in plans}
    selected = set(plans[0]['selected_parents'])
    insist(len(plans) == 16 and len(selected) == 150 and
            set(labels_by_view.values()) == set(VIEWS) and
            all(set(p['selected_parents']) == selected for p in plans), 'accepted_selection_binding')
    index = list(rows(p11['components']['view-index.jsonl']['path'],
                      p11['components']['view-index.jsonl']['sha256']))
    snapshot_ids = {}
    for view in index:
        binding = p11['components'][view['snapshot_path']]
        insist(binding['sha256'] == view['snapshot_sha256'], 'snapshot_index_binding')
        snap = load(binding['path'], binding['sha256'])
        snapshot_ids[view['view_id']] = snap['snapshot_id']

    states = {v: {} for v in VIEWS}; r1_states = {v: {} for v in VIEWS}
    state_counts = Counter(); reference_count = 0; tuples = set()
    reference_binding = a11['independent_reference']['reference']
    for row in rows(reference_binding['path'], reference_binding['sha256']):
        key = (row['view_id'], row['request_profile_id'], row['parent_asin'])
        insist(key not in tuples and row['view_id'] in labels_by_view, 'reference_duplicate_or_view')
        tuples.add(key)
        insist(row['snapshot_id'] == snapshot_ids[row['view_id']], 'reference_snapshot_mismatch')
        insist(row['eligible'] == (row['candidate_state'] == 'Supported'), 'reference_state_eligibility')
        view = labels_by_view[row['view_id']]
        dest = states if row['request_profile_id'] == PROFILE else r1_states
        insist(row['request_profile_id'] in (PROFILE, 'R1_SIM_Q1'), 'unknown_reference_profile')
        dest[view][row['parent_asin']] = row['candidate_state']
        state_counts[row['candidate_state']] += 1
        reference_count += 1
    insist(reference_count == 47808 and all(set(s) == set(catalog) for s in states.values()) and
            all(set(s) == set(catalog) for s in r1_states.values()), 'reference_coverage')
    insist(dict(state_counts) == a11['independent_reference']['state_counts'], 'reference_count_binding')
    print('P0 accepted reference read once and bound; no state recomputation.', flush=True)

    evaluations = {}
    for row in rows(p8['components']['evaluation']['path'], p8['components']['evaluation']['sha256']):
        insist(row['task_id'] not in evaluations, 'evaluation_duplicate_account')
        # Deliberately discard target rating/review/source account; none is scored.
        evaluations[row['task_id']] = {k: row[k] for k in ('task_id', 'split', 'target_parent_asin', 'target_timestamp_ms')}
    tasks = {}
    for task in rows(p8['components']['tasks']['path'], p8['components']['tasks']['sha256']):
        key = task['task_id']
        insist(key not in tasks and key in evaluations, 'task_duplicate_or_orphan')
        insist(task['history_cutoff_exclusive_ms'] == evaluations[key]['target_timestamp_ms'], 'task_time_join')
        task['candidate_parent_asins'] = [catalog[p]['parent_asin'] for p in task['candidate_parent_asins']]
        if evaluations[key]['split'] != 'dev':
            task.pop('background_statistics')
        tasks[key] = task
    insist(len(tasks) == 1603, 'root_count')
    joined = reference_join(tasks, evaluations, states, MAIN_VIEWS)
    groups = {group: sorted(k for k, r in evaluations.items() if r['split'] == group) for group in ('dev', 'test')}
    insist(len(groups['dev']) == 320 and len(groups['test']) == 1283, 'frozen_split_count')
    group_results = {}
    for group, ids in groups.items():
        applicable = [k for k in ids if joined[k]['all_main_applicable']]
        excluded = [k for k in ids if not joined[k]['all_main_applicable']]
        per_view = {}
        for view in VIEWS:
            reasons = Counter(joined[k]['by_view'][view]['reason'] for k in ids
                              if not joined[k]['by_view'][view]['applicable'])
            per_view[view] = {'n_pool': len(ids), 'applicable': len(ids)-sum(reasons.values()),
                              'NA': sum(reasons.values()), 'NA_reasons': dict(sorted(reasons.items()))}
        group_results[group] = {'n_pool': len(ids), 'n_J_all_main_views': len(applicable),
                               'n_not_all_main_applicable': len(excluded),
                               'n_any_main_applicable': sum(any(joined[k]['by_view'][v]['applicable'] for v in MAIN_VIEWS) for k in ids),
                               'per_view': per_view,
                               'pool': subset_summary(ids, tasks, evaluations, catalog),
                               'U_J': subset_summary(applicable, tasks, evaluations, catalog),
                               'outside_U_J': subset_summary(excluded, tasks, evaluations, catalog),
                               'fixed_candidate_S_coverage': summary([len(set(tasks[k]['candidate_parent_asins']) & selected) for k in ids])}
    with (PRIVATE/'account-applicability.jsonl').open('x', encoding='utf-8', newline='\n') as f:
        for key in sorted(tasks):
            f.write(canonical({'task_id': key, **evaluations[key],
                              'history_distinct_parent_count': len({h['parent_asin'] for h in tasks[key]['history']}),
                              'applicability': joined[key]})+'\n')

    docs = {p: grams(catalog[p]['title']+' '+catalog[p]['crop']) for p in sorted(catalog)}
    df = Counter(g for counts in docs.values() for g in counts)
    idf = {g: math.log((len(catalog)+1)/(df[g]+1))+1 for g in sorted(df)}
    vectors = {p: tfidf(docs[p], idf) for p in sorted(docs)}
    vocab_hash = hashlib.sha256(canonical([(g, df[g], idf[g]) for g in sorted(idf)]).encode()).hexdigest()
    score_zero = 0; constant = 0; raw_text_zero = 0; hist_events = 0
    oov_text = [0, 0]; oov_doc = [0, 0]; oov_text_macro = []; oov_doc_macro = []
    text_types = set(); text_oov_types = set(); exposures = []; exposed_parents = Counter()
    full_top_parents = set(); payloads = defaultdict(list)
    states_at_top = {v: Counter() for v in VIEWS}; top_non_supported_accounts = Counter()
    unique_top_by_state = {v: defaultdict(set) for v in VIEWS}
    with (PRIVATE/'development-score-audit.jsonl').open('x', encoding='utf-8', newline='\n') as f:
        for key in groups['dev']:
            resource_check()
            task = tasks[key]
            scored = development_score(task, catalog, idf, vectors)
            score_zero += scored['profile_zero']; constant += scored['score_constant']
            raw_text_zero += scored['raw_text_zero']; hist_events += len(task['history'])
            for field, total, macros in (('text_oov', oov_text, oov_text_macro), ('doc_oov', oov_doc, oov_doc_macro)):
                numerator = sum(x[0] for x in scored[field]); denominator = sum(x[1] for x in scored[field])
                total[0] += numerator; total[1] += denominator
                macros.append(numerator/denominator if denominator else 0)
            text_types.update(scored['text_types']); text_oov_types.update(scored['text_oov_types'])
            top = [p for p, _ in scored['top64']]
            exposure = set(top) & selected
            exposures.append(len(exposure)); exposed_parents.update(exposure); full_top_parents.update(top)
            for view in VIEWS:
                counts = Counter(states[view][p] for p in top)
                states_at_top[view].update(counts)
                top_non_supported_accounts[view] += any(states[view][p] != 'Supported' for p in top)
                for p in top:
                    unique_top_by_state[view][states[view][p]].add(p)
            # Reconstruct the accepted 08 request format locally, without making a request.
            hparents = {h['parent_asin'] for h in task['history']}
            expanded = {**task, 'products': [catalog[p] for p in sorted(set(task['candidate_parent_asins']) | hparents, key=lambda p:p.encode())]}
            content = canonical(expanded)
            request = {'messages': [{'role': 'user', 'content': content}], 'tools': []}
            payloads['accepted08_content_utf8_bytes'].append(len(content.encode('utf-8')))
            payloads['accepted08_content_codepoints'].append(len(content))
            payloads['accepted08_outer_request_utf8_bytes'].append(len(canonical(request).encode('utf-8')))
            payloads['history_json_utf8_bytes'].append(len(canonical(task['history']).encode('utf-8')))
            scored_rows = [{**catalog[p], 'base_score': score} for p, score in scored['scores']]
            payloads['diagnostic_full_scored_catalog_utf8_bytes'].append(len(canonical(scored_rows).encode('utf-8')))
            rank_scores = dict(scored['scores'])
            first_page = [{**catalog[p], 'base_score': rank_scores[p]} for p in top[:32]]
            payloads['diagnostic_top32_page_utf8_bytes'].append(len(canonical(first_page).encode('utf-8')))
            payloads['diagnostic_top64_rows_utf8_bytes'].append(len(canonical([{**catalog[p], 'base_score':rank_scores[p]} for p in top]).encode('utf-8')))
            f.write(canonical({'task_id': key, 'score_version': 'char3-tfidf-history-1.0.0-diagnostic-only',
                               'complete_C_count': len(scored['scores']),
                               'scores_sha256': hashlib.sha256(canonical(scored['scores']).encode()).hexdigest(),
                               'top64': scored['top64'], 'S_in_C': len(set(task['candidate_parent_asins']) & selected),
                               'S_in_top64': len(exposure), 'profile_zero': scored['profile_zero']})+'\n')
    print('P0 scored exactly 320 development accounts; test scoring count is zero.', flush=True)

    # Only read admitted physical fields; do not generate variants or new references.
    material_probe = {}
    material_components = [('NORMAL', pn['components']['materials.jsonl'])]
    for label in VIEWS:
        opaque = next(k for k,v in labels_by_view.items() if v == label)
        material_components.append((label, p11['components'][f'views/{opaque}/materials.jsonl']))
    for label, component in material_components:
        kinds = Counter(); lengths = defaultdict(list); stocks = Counter(); origins = Counter(); remaining = Counter()
        for r in rows(component['path'], component['sha256']):
            kinds[r['kind']] += 1
            lengths[r['kind']].append(len((canonical(r)+'\n').encode()))
            if r['kind'] == 'harvest_record':
                origins[r['facts']['origin_area_id']] += 1
            if r['kind'] == 'retail_status':
                stocks[r['facts']['stock_units']] += 1
                if label == 'NORMAL' or states[label][r['parent_asin']] == 'Supported':
                    span = r['valid_to_ms']-r['valid_from_ms']
                    insist(span > 0, 'retail_interval_invalid')
                    remaining[round(max(0, min(1, (r['valid_to_ms']-cfg['clock']['verify_at_ms'])/span)),12)] += 1
        material_probe[label] = {'kind_counts': dict(kinds),
                                 'canonical_material_line_bytes_by_kind': {k: summary(v) for k,v in lengths.items()},
                                 'retail_stock_counts': dict(stocks), 'harvest_origin_counts': dict(origins),
                                 'R5_remaining_fraction_for_reference_eligible_candidates': {str(k):v for k,v in sorted(remaining.items())}}

    expected = dict(INPUTS)
    changed = []
    for path, evidence in expected.items():
        digest = hashlib.sha256()
        with resolve(path).open('rb') as stream:
            while block := stream.read(1024*1024):
                digest.update(block); resource_check()
        if digest.hexdigest() != evidence['sha256']:
            changed.append(path)
    insist(not changed, 'upstream_changed_during_diagnostic')
    audit_components = {}
    for p in sorted(PRIVATE.iterdir()):
        audit_components[p.name] = {'relative_path':p.relative_to(ROOT).as_posix(), 'bytes':p.stat().st_size,
                                   'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    result = {'status':'completed_p0_readonly_diagnostic_not_formal_acceptance',
              'authorization_scope':'one_P0_no_P1_no_models_no_paid_API_no_ticket13',
              'runtime':{'python':sys.version, 'prefix':sys.prefix, 'unicode':unicodedata.unidata_version},
              'resources':resource_check(), 'public_micro':micro,
              'n_all_root_accounts':len(tasks), 'groups':group_results,
              'reference_binding':{'rows':reference_count, 'state_counts':dict(state_counts),
                                   'path':reference_binding['path'], 'sha256':reference_binding['sha256']},
              'development_scoring':{'accounts':320, 'test_accounts_scored':0,
                    'vocabulary_size':len(idf), 'vocabulary_sha256':vocab_hash,
                    'zero_catalog_vectors':sum(not v for v in vectors.values()),
                    'zero_user_profiles':score_zero, 'zero_profile_rate':score_zero/320,
                    'constant_score_accounts':constant, 'history_events':hist_events,
                    'raw_history_text_zero_vectors':raw_text_zero,
                    'raw_history_text_OOV_occurrences':{'outside':oov_text[0], 'total':oov_text[1], 'rate':oov_text[0]/oov_text[1]},
                    'history_plus_metadata_OOV_occurrences':{'outside':oov_doc[0], 'total':oov_doc[1], 'rate':oov_doc[0]/oov_doc[1]},
                    'raw_history_text_OOV_types':{'outside':len(text_oov_types),'total':len(text_types),'rate':len(text_oov_types)/len(text_types)},
                    'account_macro_OOV_text':summary(oov_text_macro), 'account_macro_OOV_history_plus_metadata':summary(oov_doc_macro),
                    'top64_S_exposure':summary(exposures), 'top64_S_exposure_histogram':dict(sorted(Counter(exposures).items())),
                    'accounts_with_top64_S':sum(v>0 for v in exposures),
                    'unique_top64_parents':len(full_top_parents), 'unique_S_in_top64':len(exposed_parents),
                    'S_never_in_development_top64':len(selected)-len(exposed_parents),
                    'S_exposure_account_frequency':concentration(exposed_parents),
                    'reference_states_in_top64':{v:{'candidate_references':dict(states_at_top[v]),
                        'accounts_with_non_supported_candidate':top_non_supported_accounts[v],
                        'unique_parents_by_state':{s:len(ps) for s,ps in unique_top_by_state[v].items()}} for v in VIEWS},
                    'payload_sizes':{k:summary(v) for k,v in payloads.items()},
                    'payload_token_counts':'not_measured_no_tokenizer_or_model_calls'},
              'material_field_probe':material_probe,
              'private_audit_components':audit_components,
              'read_only_protection':{'checked_inputs':len(expected), 'changed_inputs':[], 'inputs':expected},
              'limits':{'model_calls':0,'paid_API_calls':0,'formal_test_recommendation_metrics':0,
                        'production_CLI_added':False,'formal_config_added':False,'joint_package_built':False,
                        'old_draft_overwritten':False,'sufficiency_accepted':False}}
    write_new(AGGREGATE, result)
    write_new(PRIVATE/'diagnostic-receipt.json', {'aggregate_sha256':hashlib.sha256(AGGREGATE.read_bytes()).hexdigest(),
                                              'private_components':audit_components,'resources':result['resources']})
    print(canonical({'status':result['status'], 'elapsed_seconds':result['resources']['elapsed_seconds'],
                     'peak_memory_bytes':max(result['resources']['peak_working_set_bytes'],result['resources']['peak_private_commit_bytes']),
                     'test_n_pool':group_results['test']['n_pool'], 'test_n_J':group_results['test']['n_J_all_main_views'],
                     'dev_zero_profiles':score_zero, 'aggregate_path':AGGREGATE.relative_to(ROOT).as_posix()}), flush=True)


if __name__ == '__main__':
    main()
