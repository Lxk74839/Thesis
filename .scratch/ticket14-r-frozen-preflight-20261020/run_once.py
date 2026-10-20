"""Human-authorized D1/V00/R once. No model, network, Key or evaluation reads."""
import time

START = time.monotonic()

import json
import os
from pathlib import Path
import sys
import threading

ATTEMPTS = {'network': 0, 'credentials': 0, 'evaluation': 0}


def offline(event, args):
    if event.startswith(('socket.', 'http.client.', 'subprocess.')):
        ATTEMPTS['network'] += 1
        raise OSError('R_network_forbidden')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).absolute()
        parts = {p.lower() for p in path.parts}
        kind = ('credentials' if '.secrets' in parts or path.name == 'id-key.bin' else
                'evaluation' if parts & {'private', 'evaluation', 'gold'} else None)
        if kind:
            ATTEMPTS[kind] += 1
            raise OSError('R_forbidden_read')


sys.addaudithook(offline)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import p1_runtime as p1

PACKAGE = Path(__file__).resolve().parent
CONFIG = PACKAGE / 'r.config.json'
RECEIPT = PACKAGE / 'result.json'
RUN_ID = 'P1-D1-V00-R-R-FROZEN-RETRY-20261020'


def main():
    if RECEIPT.exists():
        raise SystemExit('R_receipt_exists_no_retry')
    candidate = sys.argv[1]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise SystemExit('fixed_candidate_required')
    timer = threading.Timer(max(0, 120 - (time.monotonic() - START)), lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    guard = p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2)
    result = {'task_key': p1.TASK_KEYS['R'], 'run_id': RUN_ID, 'terminal': None, 'started': False,
        'candidate_count': None, 'verified_count': None, 'qualified_count': None, 'recommendation_count': None,
        'audit_path': None, 'publication_path': None, 'model_usage': None, 'sample_recommendations': []}
    try:
        result.update(p1.execute_p1(CONFIG, 'R', storage_guard=guard))
        if result.get('audit_path'):
            audit = json.loads(Path(result['audit_path']).read_bytes())
            result.update(candidate_count=len(audit['binding']['C']), C_sha256=audit['binding']['C_sha256'],
                verified_count=sum(a['advance_allowed'] for a in audit['assessments'].values()),
                qualified_count=len(audit['G']), stop_reason=audit.get('stop_reason'), reason=audit.get('reason'),
                model_usage={k: audit['budget']['usage'][k] for k in (
                    'model_calls', 'input_tokens', 'output_tokens', 'cost_microusd')},
                model_messages=len(audit['messages']))
        if result.get('publication_path'):
            publication = json.loads(Path(result['publication_path']).read_bytes())
            items = publication['draft']['items']
            result.update(recommendation_count=len(items), release_scope=publication['release_scope'],
                sample_recommendations=[{'parent_asin': i['parent_asin'], 'sim_batch_id': i['sim_batch_id'],
                    'reasons': [r['text'] for r in i['reasons']]} for i in items[:3]])
        elif result.get('started'):
            result['recommendation_count'] = 0
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        result.update(terminal='failed_or_unknown', exception_type=type(exc).__name__,
            started=None if (p1.OUTPUT / RUN_ID / 'attempt.json').exists() else False)
    finally:
        timer.cancel()
    result.update(code_candidate=candidate, method='R', elapsed_seconds=time.monotonic() - START,
        guarded_write_upper_bytes=guard.charged_bytes, storage_limit_bytes=guard.limit_bytes,
        boundary_attempts=ATTEMPTS, guard_attempts=guard.attempts,
        generate_api=0, count_api=0, other_api=0, actual_credentials_read=0, network_requests=0,
        independent_evaluation_read=0, engineering_only=True, execution_attempts=1)
    if result['model_usage'] is not None and (any(result['model_usage'].values()) or result['model_messages']):
        result['terminal'] = 'failed_zero_model_invariant'
    with RECEIPT.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['terminal'] in ('released', 'valid_empty') else 2


if __name__ == '__main__':
    raise SystemExit(main())
