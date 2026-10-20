"""Use the existing Job/ledger guard under the user's revised local limits."""
import importlib.util
import json
from pathlib import Path

package = Path(__file__).resolve().parent
root = package.parents[1]
meta = json.loads((package / 'package.json').read_bytes())
spec = importlib.util.spec_from_file_location('existing_offline_guard', root / '.scratch/ticket12-budget-20261018/diagnostics/run_check.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.LIMIT = min(meta['offline_limit_seconds'], meta['inherited_offline_seconds']
    + meta['package_limit_seconds'] - meta['closeout_reserve_seconds'])
raise SystemExit(guard.main())
