"""Recheck source protection and the final receipts without rerunning accepted pipelines."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.scratch/data-preparation/verification/ticket14-20261016'
assert Path(sys.prefix).resolve() == (ROOT / '.conda/envs/Thesis').resolve()


def load(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def fingerprint(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


expected = {}
for row in load('binding-receipts.json') + load('protected-current-before.json') + load('upstream-source-reuse.json')['files']:
    binding = {k: row[k] for k in ('bytes', 'sha256') if k in row}
    expected.setdefault(row['path'], {}).update(binding)
if any(n.endswith('id-key.bin') for n in expected):
    manifest = json.loads((ROOT / 'data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0/package-manifest.json').read_text())
    key = manifest['sources']['identity_key']
    expected[key['path']]['sha256'] = key['sha256']
changed = []
for name, binding in sorted(expected.items()):
    actual = fingerprint(ROOT / name)
    if any(actual[k] != value for k, value in binding.items()):
        changed.append(name)
assert load('binding-summary.json')['status'] == 'passed'
assert load('upstream-source-reuse.json')['status'] == 'passed'
assert load('conservation-final.json')['all_passed']
reviews = load('review-summary.json')
assert reviews['standards']['blocking'] == reviews['spec']['blocking'] == 0
result = {'status': 'passed' if not changed else 'failed', 'protected_distinct_files': len(expected),
 'protected_baseline_tracked_files': len(load('protected-current-before.json')),
 'changed': changed, 'excluded_task_updates': ['.scratch/data-preparation/issues/14-full-data-acceptance.md',
 '.scratch/data-preparation/map.md'], 'old_acceptance_records_and_production_and_manuscript_unchanged': not changed,
 'original_materials': 26, 'data_payloads_recomputed': False,
 'formal_test_recommendation_outputs_read_or_computed': 0,
 'P0_SIM_base_scoring_joint_packaging_reproductions_rerun': 0}
with (OUT / 'protection-final.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps(result))
raise SystemExit(2 if changed else 0)
