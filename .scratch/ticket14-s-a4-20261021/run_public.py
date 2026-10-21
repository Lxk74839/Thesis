"""One PUBLIC analysis request through the production composer/schema/normalizer."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import p1_runtime as p1
import provider_fourrouter as provider
from model_adapter import ModelAdapter
from recommendation_runner import compose_role_request
from p1_storage import P1StorageGuard
from evidence_access import encoded, digest
from fourrouter_probe import _request_bytes

PACKAGE = Path(__file__).resolve().parent / 'PUBLIC'
RUN_ID = 'PUBLIC-CLAUSE-CONTRACT-20261021'


def ensure_first_execution(package, attempt_path):
    if any((Path(package) / name).exists() for name in ('execution-claim.json', 'execution-result.json',
            'execution-resources.jsonl')) or Path(attempt_path).exists():
        raise FileExistsError('PUBLIC_authorization_consumed')
    return Path(package) / 'execution-result.json'


def public_request():
    binding = {'method': 'S', 'execution_kind': 'fourrouter_responses', 'orchestration': 'batch32-0.1.0',
        'necessary_clauses': ['c1', 'c2'], 'C': ['PUBLIC-A'], 'batches': ['SIM-PUBLIC-A'],
        'base_scores': [0.5], 'base_score_sha256': 'PUBLIC-base', 'K': 10, 'run_id': RUN_ID, 'arm': 'quality'}
    state = {'queue': [], 'cursor': 0, 'stop_reason': None, 'assessments': {}, 'G': [], 'drafts': [],
        'visible_issues': [], 'messages': [], 'input_projection_sha256': 'PUBLIC-input', 'batches': []}
    return compose_role_request(binding=binding, state=state, acquired={'candidates': {}},
        initial_messages=[{'role': 'user', 'content': json.dumps({'H': [], 'PUBLIC': True})}],
        quality={}, ordered=[], role='需求解析', kind='analysis', stage='需求解析', output_cap=512,
        request_id=RUN_ID + ':1', protocol='rsm-host-protocol-0.1.0')


def run_protocol(sender, *, clock=time.monotonic):
    result = {'status': 'failed', 'send_attempts': 0, 'provider_requests_sent': 0, 'response': None,
        'count_api': 0, 'other_api': 0, 'cost': None, 'metering_status': 'unknown/incomplete',
        'exact_clause_ids': False, 'protocol_diagnostic': None}
    started = clock()
    try:
        request = public_request()
        adapter = ModelAdapter(None, capability_binding={'execution_kind': 'fourrouter_responses',
            'model_id': provider.MODEL, 'channel': provider.CHANNEL, 'base_url': 'https://4router.net/v1',
            'project_id': 'Thesis-PUBLIC-clause-contract', 'provenance': '4router', 'max_request_bytes': 16384})
        prepared = adapter.prepare(request)
        if prepared.get('status') != 'prepared' or prepared.get('missing') or not provider.verify_prepared(prepared):
            raise provider.ProtocolError('prepare', 'PUBLIC_prepared_invalid')
        result.update(request_body_bytes=len(_request_bytes(prepared['wire_body'], 16384)),
            prepared_id=prepared['prepared_id'], wire_sha256=prepared['wire_sha256'])
        deadline = min(started + 150, clock() + 120)
        if clock() >= deadline:
            raise TimeoutError()
        result['send_attempts'] = 1
        reply = sender(prepared['wire_utf8'], deadline_ms=deadline * 1000)
        result['response'] = provider.response_diagnostic(reply)
        result['provider_requests_sent'] = 1 if isinstance(result['response']['http_status'], int) else None
        normalized = provider.normalize(reply, request, pricing=None, engineering=True,
            continuations=adapter.protocol_context)
        if clock() > deadline:
            raise TimeoutError()
        output = normalized['usage']['output_tokens']
        if output is not None and output > 512:
            raise provider.ProtocolError('native_usage', 'output_token_cap_exceeded')
        message = normalized['message']
        if message['tool_requests'] or message['content']['data']['necessary_clauses'] != ['c1', 'c2']:
            raise provider.ProtocolError('runner_analysis', 'changed_request', field='necessary_clauses')
        result.update(status='passed', exact_clause_ids=True, returned_clause_ids=['c1', 'c2'])
    except provider.ProtocolError as exc:
        result['protocol_diagnostic'] = exc.diagnostic
    except (OSError, TimeoutError):
        result['protocol_diagnostic'] = {'stage': 'transport', 'code': 'PUBLIC_send_failed_or_unknown'}
        if result['send_attempts'] and result['response'] is None:
            result['provider_requests_sent'] = None
    except (ValueError, TypeError, KeyError, AttributeError):
        result['protocol_diagnostic'] = {'stage': 'unknown', 'code': 'PUBLIC_processing_failed'}
    result['elapsed_seconds'] = clock() - started
    return result


class PublicStorage(P1StorageGuard):
    def authorize_public(self):
        if not self.active:
            raise OSError('PUBLIC_guard_inactive')
        self.S_authorized = True


def main():
    candidate = sys.argv[1]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise ValueError('fixed_candidate_required')
    receipt = ensure_first_execution(PACKAGE, p1.OUTPUT / RUN_ID / 'attempt.json')
    (PACKAGE / 'execution-claim.json').write_bytes(encoded({'candidate': candidate, 'maximum_generate': 1}))
    guard = PublicStorage(p1.OUTPUT, 64 * 1024**2)
    with guard:
        output = p1.OUTPUT / RUN_ID
        output.mkdir()
        (output / 'attempt.json').write_bytes(encoded({'candidate': candidate, 'scope': 'independent_PUBLIC'}))
        guard.authorize_public()
        result = run_protocol(provider.make_sender(clock=lambda: time.monotonic() * 1000,
            max_request_bytes=16384, http_timeout_seconds=120, storage_guard=guard))
        result.update(candidate=candidate, run_id=RUN_ID, guard_allowed=guard.allowed, guard_denied=guard.attempts)
        raw = encoded(result)
        (output / 'result.json').write_bytes(raw)
    receipt.write_bytes(encoded(result | {'result_path': str(output / 'result.json'), 'sha256': digest(raw)}))
    print(json.dumps({'status': result['status'], 'send_attempts': result['send_attempts']}))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    if sys.stdin.buffer.readline() != b'GO\n':
        raise SystemExit(2)
    try:
        code = main()
    except Exception:
        print('{"status":"PUBLIC_entry_failed_no_retry"}')
        code = 2
    raise SystemExit(code)
