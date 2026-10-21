"""Offline replay of A6's saved business projection, not a full HTTP/native replay."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_p1_s_engineering import setUpModule
setUpModule()  # No sockets, subprocesses, actual credentials or evaluation labels.
import provider_fourrouter as provider

receipt_path = ROOT / '.scratch/ticket14-s-120-20261021/A6/execution-result.json'
receipt = json.loads(receipt_path.read_bytes())
audit = json.loads(Path(receipt['audit_path']).read_bytes())
checkpoint = json.loads(Path(receipt['dispatch_checkpoint']['path']).read_bytes())
assert checkpoint['passed'] is True and checkpoint['business_output']['replayable'] is True
saved = checkpoint['business_output']['items']
for item in saved:
    text = ''.join(p['text'] for p in item['item']['content'])
    assert hashlib.sha256(text.encode()).hexdigest() == item['text_sha256']
dispatch = next(m for m in audit['messages'] if m['request']['output_kind'] == 'dispatch')
request = {k: dispatch['request'][k] for k in ('run_id', 'session_id', 'request_id', 'output_schema')}
request.update(messages=[], tools=[])
# The shell is explicitly derived. Only the captured business items are original;
# reasoning is absent and usage/HTTP-body reconstruction is not claimed.
shell = {'http_status': 200, 'body': {'model': provider.MODEL, 'status': 'completed',
    'output': [item['item'] for item in saved]}}
result = provider.normalize(shell, request, pricing=None, engineering=True, continuations={})
assert result['message']['content'] == dispatch['response']['message']['content']
last = receipt['responses'][-1]
assert last['http_status'] == 408 and last['protocol_diagnostic']['code'] == 'http_status_not_200'
assert last['business_output']['replayable'] is False
summary = {'scope': 'actual_A6_checkpoint_business_projection_only', 'hashes_valid': True,
    'strict_production_normalize': 'PASS', 'matches_recorded_dispatch': True,
    'original_output_indices': [item['output_index'] for item in saved],
    'actual_phases': [item['item'].get('phase') for item in saved],
    'later_failure': {'stage': 'acquire/response_status', 'http_status': 408,
        'code': 'http_status_not_200', 'business_body_replayable': False,
        'provider_or_gateway_cause': 'unknown', 'usage': None},
    'API_calls': 0, 'full_original_response_replay': False}
(Path(__file__).resolve().parent / 'replay-result.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
