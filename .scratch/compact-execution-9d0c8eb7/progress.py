"""Read-only execution progress; no private evaluation data."""
import json
import time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
output = ROOT / 'data/recommendation-runtime-audit/personalized-compact-0.1.0'
results, profiles, usage = Counter(), Counter(), Counter()
recent = []
for p in (output / 'calls').glob('*.result.json'):
    row = json.loads(p.read_bytes())
    results[row['status']] += 1
    recent.append((row.get('completed', p.stat().st_mtime), row['status'], row.get('error')))
    for key, value in (row.get('usage') or {}).items():
        if type(value) is int:
            usage[key] += value
for p in (output / 'profiles').glob('*.json'):
    row = json.loads(p.read_bytes())
    profiles[row['status']] += 1
started = json.loads((output / 'started.json').read_bytes()) if (output / 'started.json').exists() else None
print(json.dumps({'scenes_cached': len(list((output / 'scenes').glob('*.json'))),
    'generation_intents': len(list((output / 'calls').glob('*.intent.json'))),
    'generation_results': dict(results), 'profiles': dict(profiles),
    'task_rows': len(list((output / 'tasks').glob('*.json'))), 'native_usage': dict(usage),
    'remaining_seconds': started['deadline'] - time.time() if started else None,
    'retained_bytes': sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) if output.exists() else 0,
    'last_completed_statuses': [r[1:] for r in sorted(recent)[-5:]]}))
