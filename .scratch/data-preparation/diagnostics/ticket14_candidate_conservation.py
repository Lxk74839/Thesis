"""Supplement the missing complete-C conservation using stored H/S/C, without scoring."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.scratch/data-preparation/verification/ticket14-20261016'
joint = ROOT / 'data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0'
source = joint / 'roots.jsonl'
expected = json.loads((ROOT / 'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json').read_text())['components']['roots.jsonl']
with source.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected['sha256']
catalog = {json.loads(line)['parent_asin'] for line in (joint / 'model/catalog.jsonl').read_text(encoding='utf-8').splitlines()}
roots = histories = seen = candidates = min_candidates = max_candidates = 0
min_candidates = len(catalog)
with source.open(encoding='utf-8') as stream:
    for line in stream:
        row = json.loads(line)
        s, c = row['seen_parent_asins'], row['C']
        assert len(s) == len(set(s)) and len(c) == len(set(c))
        assert set(s) <= catalog and set(c) == catalog - set(s)
        assert all(h['parent_asin'] in s and h['timestamp_ms'] < row['history_cutoff_exclusive_ms'] for h in row['history'])
        roots += 1
        histories += len(row['history'])
        seen += len(s)
        candidates += len(c)
        min_candidates, max_candidates = min(min_candidates, len(c)), max(max_candidates, len(c))
result = json.loads((OUT / 'conservation.json').read_text(encoding='utf-8'))
equation = next(e for e in result['equations'] if e['name'] == 'complete_candidate_partition')
equation.update(right=candidates + seen, passed=roots * len(catalog) == candidates + seen,
                evidence='accepted13_roots.jsonl_full_stored_C_equals_catalog_minus_all_seen')
result.update(all_passed=all(e['passed'] for e in result['equations']),
              candidate_supplement={'roots': roots, 'catalog': len(catalog), 'H_events': histories,
                'S_parent_references': seen, 'C_references': candidates,
                'candidate_min': min_candidates, 'candidate_max': max_candidates,
                'rootwise_set_complement_and_history_time_checked': True},
              diagnostic_correction='Initial audit incorrectly substituted 1845 positive H events for all-seen S references. '
                'Stored S totals 1874; original failed audit is retained. No upstream defect or change.',
              initial_failure_retained='conservation.json')
assert roots == 1603 and histories == 1845 and candidates == 2393008 and result['all_passed']
with (OUT / 'conservation-final.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'passed', **result['candidate_supplement'], 'conservation_checks': len(result['equations'])}))
