"""Verify inherited artifacts against existing Task14 receipts, without editing them."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evidence_access import encoded
from formal_runtime import PACKAGE, OUTPUT, load_config, reference

cfg = load_config()
previous = json.loads((ROOT / '.scratch/ticket14-q-contract-20261022/preservation.json').read_bytes())
outcomes = json.loads((ROOT / '.scratch/ticket14-q-contract-20261022/task-outcomes.json').read_bytes())
refs = previous['old_eight_selected_artifacts'] + previous['formal_six'] + [previous['historical_ledger']]
refs += list(outcomes['evaluation_artifacts'].values())
checks = []
for ref in refs:
    actual = reference(ROOT / ref['path'])
    checks.append(actual | {'unchanged': all(actual[k] == ref[k] for k in ('bytes', 'sha256'))})
assert all(row['unchanged'] for row in checks)
result = {'configuration_id': cfg['configuration_id'], 'checks': checks,
    'formal_six_unchanged': True, 'inherited_artifacts_unchanged': True,
    'production_output_created': OUTPUT.exists(), 'effective_authorization_exists': (PACKAGE / 'authorization.json').exists(),
    'supplier_generate': 0, 'supplier_count': 0, 'supplier_other': 0}
assert not result['production_output_created'] and not result['effective_authorization_exists']
(PACKAGE / 'preservation.json').write_bytes(encoded(result) + b'\n')
print(json.dumps({'checked': len(checks), 'unchanged': True, 'supplier_calls': 0}))
