"""No API, no user/target rows: measure shared materials and synthetic-history ranking."""
import json
import time
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from evidence_access import encoded
from compact_experiment import collect_scene, DIRECTORY
from experiment_runner import _task_plan, _json_lines, _path
from formal_runtime import PLAN
from personalized_recommendation import profile_options, run_task

started = time.monotonic()
def checkpoint():
    if time.monotonic() - started > 120:
        raise ValueError('resource_diagnostic_timeout')

_, plan, tables = _task_plan(PLAN)
catalog = [json.loads(raw) for raw in _json_lines(_path(plan['sources']['catalog']['path']), plan['sources']['catalog'])]
mapping = [json.loads(raw) for raw in _json_lines(_path(plan['sources']['candidate_map']['path']), plan['sources']['candidate_map'])]
report = {'scope': 'production-materials-and-synthetic-history; no user targets or API',
          'products': len(catalog), 'supplier_calls': 0, 'measurements': []}
for label in ('V00', 'Q1'):
    scene = next(s for s in tables['scenes.jsonl'] if s['label'] == label)
    before = time.monotonic()
    observed = collect_scene(scene['snapshot'], mapping, quality=scene['arm'] == 'quality', checkpoint=checkpoint)
    seconds = time.monotonic() - before
    sample_history = [{'parent_asin': catalog[0]['parent_asin'], 'text': 'Synthetic resource probe', 'rating': 5}]
    choices = profile_options(sample_history, catalog)[:24]
    profile = {'selections': [{'option_id': p['option_id'], 'weight': 1} for p in choices]}
    request = {'C': [p['parent_asin'] for p in catalog], 'base_scores': [.5] * len(catalog),
               'K': 10, 'prefer_stock': label == 'Q1'}
    before = time.monotonic()
    ranked = run_task(request, catalog=catalog, history=sample_history, profile=profile, scene=observed['candidates'])
    ranking_seconds = time.monotonic() - before
    top = set(ranked['topK'])
    row = {'topK': ranked['topK'], 'reasons': [r for r in ranked['candidates'] if r['parent_asin'] in top]}
    result = {'scene': label, 'seconds': seconds, 'cache_bytes': len(encoded(observed)),
              'shared_usage': observed['shared_preprocessing_usage'], 'synthetic_profile_entries': len(choices),
              'full_catalog_rank_seconds': ranking_seconds, 'sample_result_bytes': len(encoded(row))}
    report['measurements'].append(result)
    print(json.dumps(result), flush=True)
report['elapsed_seconds'] = time.monotonic() - started
report['linear_projection'] = {
    'scene_cache_bytes_18_at_larger_sample': max(r['cache_bytes'] for r in report['measurements']) * 18,
    'task_bytes_5000_at_larger_sample_plus_2KiB_per_row': max(r['sample_result_bytes'] + 2048 for r in report['measurements']) * 5000,
    'profile_request_and_response_reserved_bytes_700': 700 * (48 + 128) * 1024,
    'caveat': 'rough size projection for the measured synthetic profile, not a worst-case bound or an API throughput measurement'}
(DIRECTORY / 'resource-measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'elapsed_seconds': report['elapsed_seconds'], 'linear_projection': report['linear_projection']}))
