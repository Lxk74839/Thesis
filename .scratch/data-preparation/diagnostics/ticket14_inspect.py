"""Print only aggregate evidence and schema, never per-account records."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
files = [
 'data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0/package-manifest.json',
 'data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/check.json',
 'data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/coverage.json',
 '.scratch/data-preparation/verification/ticket12-p0-20261016-aggregate.json',
 '.scratch/data-preparation/verification/review-cleaning-1.0.0-independent-check.json',
 'records/splits/grain-A-1.1.15-user-split-1.0.0.json',
 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1-acceptance.json',
 'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json',
 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json',
 'records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0-acceptance.json',
 'data/joint-audit/joint-task-package-0.1.0/upstream-before.json']
for name in files:
    obj = json.loads((root / name).read_text(encoding='utf-8'))
    print('\nFILE', name, '\nKEYS', list(obj) if isinstance(obj, dict) else type(obj).__name__)
    if name.endswith(('coverage.json', 'check.json', 'independent-check.json')):
        print(json.dumps(obj, ensure_ascii=False))
    elif name.endswith('package-manifest.json'):
        for key, value in obj.items():
            if key in {'components', 'sources', 'input_records', 'inputs', 'source_graph'}:
                print(key, 'TYPE', type(value).__name__, 'LENGTH', len(value))
                print(json.dumps(list(value.items())[:3] if isinstance(value, dict) else value[:3], ensure_ascii=False))
            elif key not in {'private'}:
                print(key, json.dumps(value, ensure_ascii=False)[:1200])
    elif name.endswith('upstream-before.json'):
        print(json.dumps({k: (list(v.items())[:2] if isinstance(v, dict) else v[:2] if isinstance(v, list) else v)
                          for k, v in obj.items()}, ensure_ascii=False))
    else:
        allowed = {'status', 'counts', 'window', 'funnel', 'diagnostics', 'reference', 'independent_check',
                   'validation', 'sources', 'source_bindings', 'inputs', 'source_records',
                   'planning_counts', 'n8', 'nQ', 'P0', 'groups', 'exclusions', 'independent_validation',
                   'components', 'checks', 'reference_summary', 'source_fingerprints'}
        for key, value in obj.items():
            if key in allowed:
                print(key, json.dumps(value, ensure_ascii=False)[:8500])
