"""Original complete S runtime, one separately preserved attempt per invocation."""
import time
START = time.monotonic()
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import p1_runtime as p1
from p1_engineering import LONG_AUTHORIZATIONS
from control import requests, claim_request

PACKAGE = Path(__file__).resolve().parent
SHARED = p1.OUTPUT / 'S-120-CONTROL-20261021'
spec = importlib.util.spec_from_file_location('inherited_S_entry', ROOT / '.scratch/ticket14-s-engineering-20261020/run_once.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
ensure_first_execution = old.ensure_first_execution


def main():
    candidate, attempt = sys.argv[1:]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate) or attempt not in ('A1', 'A2'):
        raise ValueError('fixed_candidate_attempt_required')
    control = PACKAGE / attempt
    grant = LONG_AUTHORIZATIONS[int(attempt[-1]) - 1]
    run_id = 'P1-D1-V00-S-' + grant
    receipt = ensure_first_execution(control, p1.OUTPUT / run_id / 'attempt.json')
    cfg = json.loads((control / 's.config.json').read_bytes())
    with (control / 'execution-claim.json').open('x', encoding='utf-8') as stream:
        json.dump({'authorization_id': grant, 'run_id': run_id, 'candidate': candidate}, stream)
    with p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2):
        SHARED.mkdir(exist_ok=True)
    guard = p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2)
    guard.claim_S_request = lambda body: claim_request(SHARED / 'requests.jsonl', body, run_id)
    result = {'run_id': run_id, 'task_key': p1.TASK_KEYS['S'], 'terminal': None,
        'candidate_count': None, 'verified_count': None, 'recommendation_count': None, 'responses': [],
        'cost': None, 'metering_status': 'unknown/incomplete'}
    timer = threading.Timer(max(0, cfg['limits']['S']['elapsed_ms'] / 1000 + 10 - (time.monotonic() - START)), lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        result.update(p1.execute_p1(control / 's.config.json', 'S', storage_guard=guard))
        if result.get('audit_path'):
            audit = json.loads(Path(result['audit_path']).read_bytes())
            acquired = audit.get('evidence', {}).get('acquired', {})
            result.update(candidate_count=len(audit['binding']['C']), C_sha256=audit['binding']['C_sha256'],
                verified_count=sum(a['advance_allowed'] for a in audit['assessments'].values()),
                G=audit['G'], reason=audit.get('reason'), acquired_candidate_count=len(acquired.get('candidates', {})),
                actual_tokens={k: audit['budget']['usage'].get(k) for k in ('input_tokens', 'output_tokens')},
                model_calls=audit['budget']['usage']['model_calls'],
                responses=[{'status': m['response']['status'], 'protocol_diagnostic': m['response'].get('protocol_diagnostic'),
                    'deadline_diagnostic': m['response'].get('deadline_diagnostic'), **(m['response'].get('raw_response') or {})}
                    for m in audit['messages']])
        if result.get('publication_path'):
            publication = json.loads(Path(result['publication_path']).read_bytes())
            result['recommendation_count'] = len(publication['draft']['items'])
            result['sample_recommendations'] = [i['parent_asin'] for i in publication['draft']['items'][:3]]
    except Exception:
        result.update(terminal='failed_or_unknown', reason='entry_error_no_retry')
    finally:
        timer.cancel()
    result.update(code_candidate=candidate, guard_allowed=guard.allowed, guard_denied=guard.attempts,
        cumulative_send_intents=len(requests(SHARED / 'requests.jsonl')), count_api=0, other_api=0,
        elapsed_seconds=time.monotonic() - START, token_cost_metering_complete=False)
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'terminal': result['terminal'], 'receipt': str(receipt)}))
    return 0 if result['terminal'] in ('released', 'valid_empty') else 2


if __name__ == '__main__':
    if sys.stdin.buffer.readline() != b'GO\n':
        raise SystemExit(2)
    raise SystemExit(main())
