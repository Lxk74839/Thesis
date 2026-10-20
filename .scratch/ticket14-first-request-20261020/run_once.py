"""One independently authorized first request; never a recommendation run."""
import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import p1_runtime as p1
import provider_fourrouter as provider
from evidence_access import digest, encoded
from fourrouter_probe import _public_binding, PUBLIC_CONFIG, _request_bytes
from p1_storage import P1StorageGuard

PACKAGE = Path(__file__).resolve().parent
AUTHORIZATION = 'S-FIRST-DIAGNOSTIC-20261020'
RUN_ID = 'P1-D1-V00-S-' + AUTHORIZATION


def artifact_bytes(package, output):
    controls = ('execution-claim.json', 'execution-result.json', 'execution-resources.jsonl', 'execution.stdout')
    return sum(p.stat().st_size for p in [*(Path(package) / n for n in controls),
        *Path(output).rglob('*')] if p.is_file())


def write_artifact(path, raw, *, package, output):
    # Leave space for the bounded parent's stdout and resource receipt even on failure.
    if artifact_bytes(package, output) + len(raw) + 8192 > 1024**2:
        raise OSError('diagnostic_artifact_limit')
    if Path(output).is_relative_to(p1.OUTPUT):
        shared = sum(p.stat().st_size for p in p1.OUTPUT.rglob('*') if p.is_file())
        outside = artifact_bytes(package, Path(package) / '__no_output__')
        if shared + outside + len(raw) + 8192 > 64 * 1024**2:
            raise OSError('shared_storage_limit')
    with Path(path).open('xb') as stream:
        stream.write(raw)


def ensure_first_execution(package, attempt_path):
    if any((Path(package) / name).exists() for name in
           ('execution-claim.json', 'execution-result.json', 'execution-resources.jsonl')) or Path(attempt_path).exists():
        raise FileExistsError('diagnostic_already_consumed')
    return Path(package) / 'execution-result.json'


def claim_first_execution(package, attempt_path, candidate):
    receipt = ensure_first_execution(package, attempt_path)
    write_artifact(Path(package) / 'execution-claim.json', encoded({'authorization_id': AUTHORIZATION,
        'run_id': RUN_ID, 'responses_limit': 1, 'candidate': candidate}),
        package=package, output=Path(attempt_path).parent)
    return receipt


class DiagnosticStorage(P1StorageGuard):
    def authorize_diagnostic(self, authorization_id):
        if not self.active or authorization_id != AUTHORIZATION:
            raise OSError('diagnostic_sender_not_authorized')
        # Local capability only; no addition to the production S authorization registry.
        self.S_authorized = True


def diagnose(request, prepared, *, sender, clock):
    start = clock()
    result = {'send_attempts': 1, 'responses_requests': None, 'count_api': 0, 'other_api': 0,
        'retries': 0, 'cost': None, 'strict_role_schema_valid': None, 'tool_call_valid': None,
        'json_valid': None, 'protocol_diagnostic': None, 'terminal': 'diagnostic_failed',
        'usage': provider.engineering_usage({}), 'usage_diagnostic': {'state': 'unknown', 'usage': None},
        'native_usage': None, 'http_status': None, 'returned_model': None, 'request_id': None,
        'response_id': None, 'metering_status': 'unknown/incomplete'}
    try:
        envelope = sender(prepared['wire_utf8'], deadline_ms=start + 30000)
    except (OSError, ValueError, TypeError):
        return result | {'protocol_diagnostic': {'stage': 'transport', 'code': 'unknown_send_state'},
            'network_ms': clock() - start}
    result.update(provider.response_diagnostic(envelope), usage=provider.engineering_usage(envelope),
        network_ms=clock() - start, responses_requests=1 if envelope.get('http_status') is not None else None)
    body = envelope.get('body') if isinstance(envelope.get('body'), dict) else {}
    result['completion_status'] = body.get('status') if body.get('status') in (
        'completed', 'incomplete', 'failed', 'cancelled', 'queued', 'in_progress') else 'unknown'
    structure = []
    for index, item in enumerate(body.get('output') if isinstance(body.get('output'), list) else []):
        item = item if isinstance(item, dict) else {}
        content = item.get('content') if isinstance(item.get('content'), list) else []
        structure.append({'index': index, 'type': item.get('type') if item.get('type') in
            ('reasoning', 'message', 'function_call', 'refusal') else 'unknown',
            'has_arguments': 'arguments' in item, 'has_call_id': 'call_id' in item,
            'content_types': [p.get('type') if isinstance(p, dict) and p.get('type') in
                ('output_text', 'refusal') else 'unknown' for p in content]})
    result['output_structure'] = structure
    try:
        normalized = provider.normalize(envelope, request, pricing=None, engineering=True)
        result.update(terminal='first_response_protocol_passed', tool_call_valid=bool(normalized['message']['tool_requests']),
            strict_role_schema_valid=normalized['message']['content'] is not None, json_valid=True)
    except provider.ProtocolError as exc:
        result['protocol_diagnostic'] = exc.diagnostic
        if exc.diagnostic['stage'] == 'json_decode':
            result['json_valid'] = False
        if exc.diagnostic['stage'] == 'role_schema':
            result.update(json_valid=True, strict_role_schema_valid=False)
        if exc.diagnostic['stage'] == 'tool_call':
            result['tool_call_valid'] = False
    except (ValueError, TypeError, KeyError, AttributeError):
        result['protocol_diagnostic'] = {'stage': 'unknown', 'code': 'unclassified_validation_failure'}
    if result['network_ms'] > 30000:
        result.update(terminal='diagnostic_failed', deadline_exceeded=True)
    return result


def prepare_first_request():
    from experiment_runner import assemble_task
    from recommendation_runner import compose_role_request
    public = _public_binding(PUBLIC_CONFIG)
    assembly = assemble_task(p1.PILOT, p1.TASK_KEYS['S'])
    b = copy.deepcopy(assembly['binding'])
    if (assembly['plan_id'] != p1.PILOT_ID or b['root_task_id'] != p1.D1 or b['method'] != 'S'
            or assembly['scene']['label'] != 'V00' or b['plan_source_scope'] != 'development_pilot'
            or len(b['C']) != 1493 or b['C_sha256'] != '6ce1fa2372935c80f0a66fc035b466acdc2c703726cedb56cecb82dc69f9a874'):
        raise ValueError('diagnostic_frozen_scope_mismatch')
    b.update(run_id=RUN_ID, execution_kind='fourrouter_responses', orchestration='batch32-0.1.0')
    state = {'queue': sorted(b['C'], key=lambda p: (-b['base_scores'][b['C'].index(p)], p.encode())),
        'cursor': 0, 'stop_reason': None, 'assessments': {}, 'G': [], 'drafts': [], 'visible_issues': [],
        'messages': [], 'batches': [], 'input_projection_sha256': digest(encoded(assembly['initial_messages']))}
    request = compose_role_request(binding=b, state=state, acquired={'candidates': {}},
        initial_messages=assembly['initial_messages'], quality={}, ordered=[], role='需求解析', kind='analysis',
        stage='需求解析', output_cap=8192, request_id=RUN_ID + ':message:0', protocol='rsm-runner-4router-0.1.0')
    prepared = provider.prepare(request, public | {'execution_kind': 'fourrouter_responses',
        'project_id': 'Thesis-task14-P1', 'provenance': '4router', 'max_request_bytes': 2 * 1024**2})
    if prepared.get('missing') or not provider.verify_prepared(prepared):
        raise ValueError('diagnostic_prepared_invalid')
    actual = _request_bytes(prepared['wire_body'], 2 * 1024**2)
    meta = {'authorization_id': AUTHORIZATION, 'run_id': RUN_ID, 'task_key': p1.TASK_KEYS['S'],
        'parent_plan_id': p1.PLAN_ID, 'pilot_id': p1.PILOT_ID, 'candidate_count': len(b['C']),
        'C_sha256': b['C_sha256'], 'input_sha256': b['assembled_input_sha256'],
        'prepared_id': prepared['prepared_id'], 'tool_schema_sha256': prepared['tool_schema_sha256'],
        'role_schema_sha256': prepared['role_schema_sha256'], 'actual_POST_bytes': len(actual),
        'actual_POST_sha256': digest(actual), 'max_output_tokens': 8192, 'reasoning_effort': 'none'}
    return request, prepared, meta


def main():
    candidate = sys.argv[1]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise ValueError('fixed_candidate_required')
    receipt = claim_first_execution(PACKAGE, p1.OUTPUT / RUN_ID / 'attempt.json', candidate)
    guard = DiagnosticStorage(p1.OUTPUT, 64 * 1024**2)
    with guard:
        request, prepared, meta = prepare_first_request()
        (p1.OUTPUT / RUN_ID).mkdir()
        write_artifact(p1.OUTPUT / RUN_ID / 'attempt.json', encoded(meta), package=PACKAGE, output=p1.OUTPUT / RUN_ID)
        guard.authorize_diagnostic(AUTHORIZATION)
        result = diagnose(request, prepared, sender=provider.make_sender(clock=lambda: time.monotonic() * 1000,
            max_request_bytes=2 * 1024**2, storage_guard=guard), clock=lambda: time.monotonic() * 1000)
        result.update(meta, code_candidate=candidate, publication_path=None, tool_executions=0,
            engineering_run_completed=False, cost_metering_complete=False,
            guard_allowed=guard.allowed, guard_denied=guard.attempts)
        raw = encoded(result)
        write_artifact(p1.OUTPUT / RUN_ID / 'result.json', raw, package=PACKAGE, output=p1.OUTPUT / RUN_ID)
    summary = {'terminal': result['terminal'], 'result_path': str(p1.OUTPUT / RUN_ID / 'result.json'),
        'sha256': digest(raw), 'responses_requests': result['responses_requests']}
    write_artifact(receipt, encoded(summary), package=PACKAGE, output=p1.OUTPUT / RUN_ID)
    print(json.dumps({'terminal': result['terminal'], 'receipt': receipt.name}))
    return 0


if __name__ == '__main__':
    if sys.stdin.buffer.readline() != b'GO\n':
        raise SystemExit(2)
    try:
        code = main()
    except Exception:
        print('{"terminal":"entry_failed_no_retry"}')
        code = 2
    raise SystemExit(code)
