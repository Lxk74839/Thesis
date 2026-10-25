"""Validate the authorized frozen compact inputs; never read held-out labels."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from compact_experiment import load_config, OUTPUT, file_ref
from evidence_access import encoded, digest
from experiment_runner import _task_plan, _source_row, _json, accepted_sources

cfg = load_config()
assert cfg['configuration_id'] == '9d0c8eb73b8ad0788eed05d0654353aa5154db348c7f974b78cfd24190a81fdf'
assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
assert cfg['protocol'] == 'personalized-compact-0.1.0'
assert (cfg['max_calls'], cfg['max_hours'], cfg['max_new_bytes']) == (700, 24, 10 * 1024**3)
_, plan, rows = _task_plan(ROOT / cfg['plan_directory'])
assert plan['sources'] == accepted_sources()
assert cfg['users'] == [r['root_task_id'] for r in rows['sample-users.jsonl']]
assert len(cfg['users']) == len(set(cfg['users'])) == 100
assert (len(rows['tasks.jsonl']), len(rows['scenes.jsonl'])) == (5000, 18)
inputs = []
for ref in rows['root-references.jsonl']:
    root, candidates = _source_row(ref['root_ref']), _source_row(ref['candidate_ref'])
    assert root['root_task_id'] == candidates['root_task_id'] == ref['root_task_id']
    assert digest(encoded(root['history'])) == root['H_sha256'] == ref['H_sha256']
    assert digest(encoded(candidates['C'])) == root['C_sha256'] == ref['C_sha256']
    assert digest(encoded(list(zip(candidates['C'], candidates['b'])))) == root['base_scores_sha256'] == ref['base_scores_sha256']
    inputs.append({'root_task_id': ref['root_task_id'], 'candidate_count': len(candidates['C']),
        'C_sha256': root['C_sha256'], 'H_sha256': root['H_sha256'],
        'root_ref': ref['root_ref'], 'candidate_ref': ref['candidate_ref']})
for scene in rows['scenes.jsonl']:
    snapshot = _json(scene['snapshot'])
    assert snapshot['snapshot_id'] == scene['snapshot_id']
record = {'configuration_id': cfg['configuration_id'], 'protocol': cfg['protocol'],
    'checked_utc_epoch': time.time(), 'code_and_plan_files': 'PASS', 'input_rows': 'PASS',
    'users': 100, 'scenarios': 18, 'tasks': 5000, 'model_slots': 3400,
    'candidate_count_range': [min(r['candidate_count'] for r in inputs), max(r['candidate_count'] for r in inputs)],
    'inputs': inputs, 'prior_output_exists': OUTPUT.exists(), 'supplier_calls': 0,
    'tests_reused': 35, 'reviewed_candidate': '4e63a107215d9b238b59c049104c7d02198bdc4a',
    'human_authorization': 'Current user message explicitly authorizes the new protocol and all batches.'}
target = Path(__file__).with_name('preflight.json')
with target.open('xb') as stream:
    stream.write(encoded(record) + b'\n')
print(json.dumps({k: v for k, v in record.items() if k != 'inputs'}))
