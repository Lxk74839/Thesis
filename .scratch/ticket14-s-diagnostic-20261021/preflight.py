"""Real frozen-input composition only; explicitly no Key, claim, network, or S run."""
import importlib.util
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from tests.test_fourrouter_protocol_diagnostics import setUpModule

setUpModule()
spec = importlib.util.spec_from_file_location('diagnostic_entry',
    root / '.scratch/ticket14-first-request-20261020/run_once.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
request, prepared, meta = entry.prepare_first_request()
assert len(request['messages'][-1]['content']['runtime']['candidate_batches']) == 1493
assert len(request['messages'][-1]['content']['runtime']['base_preferences']) == 1493
assert prepared['wire_body']['reasoning'] == {'effort': 'none'}
print(json.dumps({'status': 'offline_preflight_only', **meta, 'Key_reads': 0, 'HTTP': 0}))
