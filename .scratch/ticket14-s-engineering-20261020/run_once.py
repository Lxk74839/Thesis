"""Consume the human's one S grant; launched only after fixed-candidate review."""
import sys
if sys.stdin.buffer.readline() != b'GO\n':
    raise SystemExit(2)
import time
START = time.monotonic()
import json
import os
from pathlib import Path
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import p1_runtime as p1
from p1_engineering import AUTHORIZATION

PACKAGE = Path(__file__).resolve().parent
RUN_ID = 'P1-D1-V00-S-' + AUTHORIZATION


def main():
    candidate = sys.argv[1]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise SystemExit('fixed_candidate_required')
    if (PACKAGE / 'result.json').exists():
        raise SystemExit('S_receipt_exists_no_retry')
    with (PACKAGE / 'execution-claim.json').open('x', encoding='utf-8') as stream:
        json.dump({'authorization_id': AUTHORIZATION, 'task_key': p1.TASK_KEYS['S'],
            'run_id': RUN_ID, 'candidate': candidate, 'execution_attempts': 1}, stream)
    guard = p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2)
    timer = threading.Timer(max(0, 350 - (time.monotonic() - START)), lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    result = {'task_key': p1.TASK_KEYS['S'], 'run_id': RUN_ID, 'terminal': None,
        'candidate_count': None, 'verified_count': None, 'recommendation_count': None,
        'responses': [], 'sample_recommendations': [], 'actual_tokens': None, 'cost': None,
        'metering_status': 'unknown/incomplete', 'metering_reason': 'count_waived_rates_unknown_native_usage_optional'}
    try:
        result.update(p1.execute_p1(PACKAGE / 's.config.json', 'S', storage_guard=guard))
        if result.get('audit_path'):
            audit = json.loads(Path(result['audit_path']).read_bytes())
            result.update(candidate_count=len(audit['binding']['C']), C_sha256=audit['binding']['C_sha256'],
                verified_count=sum(a['advance_allowed'] for a in audit['assessments'].values()),
                qualified_count=len(audit['G']), reason=audit.get('reason'),
                actual_tokens={k: audit['budget']['usage'].get(k) for k in ('input_tokens', 'output_tokens')},
                request_output_cap_sum=audit['budget']['usage'].get('request_output_tokens'),
                model_calls=audit['budget']['usage']['model_calls'],
                responses=[{'status': m['response']['status'], **(m['response'].get('raw_response') or {})}
                    for m in audit['messages']])
        if result.get('publication_path'):
            publication = json.loads(Path(result['publication_path']).read_bytes())
            items = publication['draft']['items']
            result.update(recommendation_count=len(items), release_scope=publication['release_scope'],
                sample_recommendations=[{'parent_asin': i['parent_asin'], 'sim_batch_id': i['sim_batch_id'],
                    'reasons': [r['text'] for r in i['reasons']]} for i in items[:3]])
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        result.update(terminal='failed_or_unknown', exception_type=type(exc).__name__,
            started=None if (p1.OUTPUT / RUN_ID / 'attempt.json').exists() else False)
    finally:
        timer.cancel()
    result.update(code_candidate=candidate, elapsed_seconds=time.monotonic() - START,
        guarded_shared_write_upper_bytes=guard.charged_bytes, guard_allowed=guard.allowed,
        guard_denied=guard.attempts, count_api=0, other_api=0, independent_evaluation_read=0,
        execution_attempts=1, engineering_passed=result['terminal'] in ('released', 'valid_empty'),
        token_cost_metering_complete=False)
    with (PACKAGE / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['engineering_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
