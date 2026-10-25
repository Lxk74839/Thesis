"""One read-only replay of failed profile validation using recorded replies only."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compact_experiment import OUTPUT, load_config
from evidence_access import digest, encoded
from experiment_runner import _task_plan, _source_row, _json_lines, _path
from personalized_recommendation import analyze_profile

cfg = load_config()
_, plan, tables = _task_plan(ROOT / cfg['plan_directory'])
catalog = [json.loads(raw) for raw in _json_lines(_path(plan['sources']['catalog']['path']), plan['sources']['catalog'])]
references = {r['root_task_id']: r for r in tables['root-references.jsonl']}
results = {p.name.split('.')[0]: json.loads(p.read_bytes()) for p in (OUTPUT / 'calls').glob('*.result.json')}
rows, used = [], []


def recorded_only(request):
    identity = digest(encoded({'namespace': cfg['configuration_id'], 'request': request}))
    used.append(identity)
    if identity not in results:
        raise ValueError('offline_missing_receipt_no_send')
    record = results[identity]
    if record['status'] != 'ok':
        raise ValueError(record.get('error', 'recorded_profile_failure'))
    if digest(encoded(record['output'])) != record['output_sha256']:
        raise ValueError('offline_receipt_mismatch')
    return record['output']


for user in cfg['users']:
    for method in ('S', 'M'):
        profile = json.loads((OUTPUT / 'profiles' / f'{user}-{method}.json').read_bytes())
        if profile['status'] == 'ok':
            continue
        root = _source_row(references[user]['root_ref'])
        used = []
        try:
            analyze_profile(root['history'], catalog, method=method, invoke=recorded_only)
            error = 'replay_completed_unexpectedly'
        except ValueError as exc:
            error = str(exc)
        rows.append({'root_task_id': user, 'method': method, 'recorded_status': profile['status'],
                     'offline_validation_error': error, 'recorded_request_ids': used})
result = {'scope': 'read-only; recorded replies only; no supplier API; no result mutation', 'profiles': rows}
(HERE / 'failure-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'failed_profiles': len(rows), 'error_counts': {e: sum(r['offline_validation_error'] == e for r in rows)
    for e in sorted({r['offline_validation_error'] for r in rows})}}, ensure_ascii=False))
