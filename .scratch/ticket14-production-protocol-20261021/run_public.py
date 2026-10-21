"""Two PUBLIC requests through production prepare/normalize/tool validation only."""
import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import p1_runtime as p1
import provider_fourrouter as provider
from evidence_access import encoded, digest
from model_adapter import ModelAdapter
from p1_storage import P1StorageGuard
from fourrouter_probe import _request_bytes

PACKAGE = Path(__file__).resolve().parent / 'PUBLIC'
RUN_ID = 'PUBLIC-PRODUCTION-PROTOCOL-20261021'
AUTHORIZATION = 'PUBLIC-PRODUCTION-ONCE-20261021'


def ensure_first_execution(package, attempt_path):
    if any((Path(package) / name).exists() for name in ('execution-claim.json', 'execution-result.json',
            'execution-resources.jsonl')) or Path(attempt_path).exists():
        raise FileExistsError('PUBLIC_authorization_consumed')
    return Path(package) / 'execution-result.json'


def public_request():
    from provider_openai import object_schema
    return {'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': 'fourrouter_responses',
        'request_id': RUN_ID + ':1', 'attempt_id': RUN_ID + ':1', 'run_id': RUN_ID,
        'session_id': RUN_ID + ':manager', 'role': '推荐管理', 'reply_to': None, 'model_id': provider.MODEL,
        'output_kind': 'final_submit', 'max_output_tokens': 1024,
        'messages': [{'role': 'system', 'content': 'PUBLIC fictional protocol check. First call list_evidence exactly once '
            'with cursor null. Do not answer before the tool result. After its result, return strict JSON '
            '{"kind":"final_submit","data":{"draft_id":"<the first entry evidence_ref>"}}. '
            'Never call another tool or repeat a tool.'},
            {'role': 'user', 'content': 'Read the PUBLIC fictional draft identifier from list_evidence and submit it.'}],
        'tools': [{'name': 'list_evidence', 'version': 'restricted-evidence-0.1.0',
            'input_schema': object_schema({'cursor': {'type': ['string', 'null']}})}],
        'output_schema': object_schema({'kind': {'type': 'string', 'enum': ['final_submit']},
            'data': object_schema({'draft_id': {'type': 'string'}})})}


def run_protocol(sender, *, clock=time.monotonic):
    started = clock()
    adapter = ModelAdapter(None, capability_binding={'execution_kind': 'fourrouter_responses',
        'model_id': provider.MODEL, 'channel': provider.CHANNEL, 'base_url': 'https://4router.net/v1',
        'project_id': 'Thesis-PUBLIC-production', 'provenance': '4router', 'max_request_bytes': 16384})
    request = public_request()
    result = {'run_id': RUN_ID, 'status': 'failed', 'send_attempts': 0, 'responses': [], 'request_bytes': [],
        'tool_call_valid': False, 'tool_result_sent': False, 'strict_json_valid': False,
        'protocol_items_replayed': False, 'reasoning_covered': False, 'count_api': 0, 'other_api': 0,
        'reasoning_validated': False, 'encrypted_context_present': False, 'encrypted_context_replayed': False,
        'prepared_ids': [], 'wire_sha256': [], 'actual_POST_sha256': [],
        'cost': None, 'metering_status': 'unknown/incomplete', 'protocol_diagnostic': None}
    first_output = None
    try:
        for index in range(2):
            prepared = adapter.prepare(request)
            if prepared.get('status') != 'prepared' or prepared.get('missing') or not provider.verify_prepared(prepared):
                raise provider.ProtocolError('prepare', 'PUBLIC_prepared_invalid', field='prepared')
            raw = _request_bytes(prepared['wire_body'], 16384)
            if index:
                result['protocol_items_replayed'] = prepared['wire_body']['input'][2:2 + len(first_output)] == first_output
                if not result['protocol_items_replayed']:
                    raise provider.ProtocolError('continuation', 'PUBLIC_replay_mismatch', field='input')
            result['request_bytes'].append(len(raw))
            result['prepared_ids'].append(prepared['prepared_id'])
            result['wire_sha256'].append(prepared['wire_sha256'])
            result['actual_POST_sha256'].append(digest(raw))
            deadline = min(started + 270, clock() + 120)
            if clock() >= deadline:
                raise TimeoutError('PUBLIC_deadline')
            result['send_attempts'] += 1
            if index:
                result['tool_result_sent'] = None
            reply = sender(prepared['wire_utf8'], deadline_ms=deadline * 1000)
            diagnostic = provider.response_diagnostic(reply)
            if index and diagnostic['http_status'] is not None:
                result['tool_result_sent'] = True
            result['responses'].append(diagnostic)
            result['reasoning_covered'] |= any(s['type'] == 'reasoning' for s in diagnostic.get('output_structure') or [])
            normalized = provider.normalize(reply, request, pricing=None, engineering=True,
                continuations=adapter.protocol_context)
            diagnostic['parse_status'] = 'ok'
            result['reasoning_validated'] |= any(s['type'] == 'reasoning' for s in diagnostic.get('output_structure') or [])
            if clock() > deadline:
                raise TimeoutError('PUBLIC_response_late')
            observed = normalized['usage']['output_tokens']
            if observed is not None and observed > 1024:
                raise provider.ProtocolError('native_usage', 'output_token_cap_exceeded', field='output_tokens')
            if index == 0:
                calls = normalized['message']['tool_requests']
                if len(calls) != 1 or calls[0]['name'] != 'list_evidence' or calls[0]['arguments'] != {'cursor': None}:
                    raise provider.ProtocolError('tool_call', 'PUBLIC_expected_one_tool_call', field='function_call')
                result['tool_call_valid'] = True
                first_output = copy.deepcopy(reply['body']['output'])
                result['encrypted_context_present'] = any(i.get('type') == 'reasoning'
                    and isinstance(i.get('encrypted_content'), str) and bool(i['encrypted_content']) for i in first_output)
                request['messages'].extend([normalized['message'], {'role': 'tool', 'tool_call_id': calls[0]['call_id'],
                    'content': {'entries': [{'evidence_ref': 'PUBLIC-DRAFT-7'}], 'next_cursor': None}}])
                request.update(request_id=RUN_ID + ':2', attempt_id=RUN_ID + ':2', reply_to=RUN_ID + ':1')
            else:
                result['encrypted_context_replayed'] = result['encrypted_context_present'] and result['protocol_items_replayed']
                if normalized['message']['tool_requests'] or normalized['message']['content'] != {
                        'kind': 'final_submit', 'data': {'draft_id': 'PUBLIC-DRAFT-7'}}:
                    raise provider.ProtocolError('role_schema', 'PUBLIC_final_value_mismatch', field='data/draft_id')
                result.update(status='passed', strict_json_valid=True,
                    public_result=normalized['message']['content'])
    except provider.ProtocolError as exc:
        result['protocol_diagnostic'] = exc.diagnostic
    except (OSError, TimeoutError):
        result['protocol_diagnostic'] = {'stage': 'transport', 'code': 'PUBLIC_send_failed_or_unknown'}
    except (ValueError, TypeError, KeyError, AttributeError):
        result['protocol_diagnostic'] = {'stage': 'unknown', 'code': 'PUBLIC_processing_failed'}
    result['elapsed_seconds'] = clock() - started
    result['provider_requests_sent'] = (len(result['responses']) if len(result['responses']) == result['send_attempts']
        and all(r['http_status'] is not None for r in result['responses']) else None)
    return result


class PublicStorage(P1StorageGuard):
    def authorize_public(self):
        if not self.active:
            raise OSError('PUBLIC_guard_inactive')
        self.S_authorized = True  # Existing exact worker/credential aperture only.


def main():
    candidate = sys.argv[1]
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise ValueError('fixed_candidate_required')
    receipt = ensure_first_execution(PACKAGE, p1.OUTPUT / RUN_ID / 'attempt.json')
    with (PACKAGE / 'execution-claim.json').open('x', encoding='utf-8') as stream:
        json.dump({'authorization_id': AUTHORIZATION, 'candidate': candidate, 'maximum_generate': 2}, stream)
    guard = PublicStorage(p1.OUTPUT, 64 * 1024**2)
    with guard:
        output = p1.OUTPUT / RUN_ID
        output.mkdir()
        (output / 'attempt.json').write_bytes(encoded({'authorization_id': AUTHORIZATION, 'candidate': candidate}))
        guard.authorize_public()
        result = run_protocol(provider.make_sender(clock=lambda: time.monotonic() * 1000,
            max_request_bytes=16384, http_timeout_seconds=120, storage_guard=guard))
        result.update(candidate=candidate, guard_allowed=guard.allowed, guard_denied=guard.attempts,
            S_run=False, evaluation_read=0)
        raw = encoded(result)
        (output / 'result.json').write_bytes(raw)
    receipt.write_bytes(encoded({'status': result['status'], 'result_path': str(output / 'result.json'), 'sha256': digest(raw)}))
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
