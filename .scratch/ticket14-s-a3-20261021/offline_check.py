"""Reuse the accepted Windows Job guard, bounded by this package's work window."""
import importlib.util
import json
from pathlib import Path

package = Path(__file__).resolve().parent
root = package.parents[1]
meta = json.loads((package / 'package.json').read_bytes())
spec = importlib.util.spec_from_file_location('existing_offline_guard',
    root / '.scratch/ticket12-budget-20261018/diagnostics/run_check.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.LIMIT = min(meta['offline_limit_seconds'] - meta['reserve_seconds'],
    meta['inherited_offline_seconds'] + meta['package_seconds'] - meta['reserve_seconds'])
raise SystemExit(guard.main())
