"""Local setup and one authorized PUBLIC probe; no token counter."""
import copy
import http.client
import json
from pathlib import Path
import re
import subprocess
import sys
import time


PROJECT = Path(__file__).resolve().parent
PUBLIC_CONFIG = PROJECT / '.scratch/ticket14-live-integration-20261020/B-4router/config.draft.json'
LOCAL_CREDENTIAL = PROJECT / '.secrets/4router.json'
LIVE_RECEIPT = PROJECT / '.scratch/ticket14-public-8k-once-20261020/result.jsonl'


def _public_binding(path):
    binding = json.loads(Path(path).read_text(encoding='utf-8-sig'))['model_binding']
    expected = {'channel': '4Router', 'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna'}
    if any(binding.get(k) != v for k, v in expected.items()):
        raise ValueError('invalid_public_configuration')
    return {k: binding[k] for k in expected}


def check_config(*, public_path=PUBLIC_CONFIG, credential_path=LOCAL_CREDENTIAL):
    filled, valid = False, False
    try:
        data = json.loads(Path(credential_path).read_text(encoding='utf-8-sig'))
        key = data['api_key']
        filled = isinstance(key, str) and bool(key.strip())
        valid = (set(data) == {'api_key'} and isinstance(key, str)
                 and not any(c.isspace() or not 33 <= ord(c) <= 126 for c in key))
    except (OSError, ValueError, TypeError, KeyError):
        pass
    try:
        _public_binding(public_path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        valid = False
    return {'api_key_filled': filled, 'local_config_valid': valid}


def prepare_probe(*, public_path=PUBLIC_CONFIG):
    binding = _public_binding(public_path)
    request = {'model': binding['model_id'], 'store': False, 'stream': False,
        'max_output_tokens': 256, 'reasoning': {'effort': 'none'}, 'parallel_tool_calls': False,
        'input': [{'role': 'user', 'content':
            'PUBLIC fictional protocol test. Read PUBLIC-REF-1, then report PUBLIC-OK.'}],
        'tools': [{'type': 'function', 'name': 'read_evidence', 'strict': True, 'parameters': {
            'type': 'object', 'properties': {'evidence_refs': {'type': 'array',
                'items': {'type': 'string', 'enum': ['PUBLIC-REF-1']}, 'minItems': 1, 'maxItems': 1}},
            'required': ['evidence_refs'], 'additionalProperties': False}}],
        'tool_choice': {'type': 'function', 'name': 'read_evidence'},
        'text': {'format': {'type': 'json_schema', 'name': 'PUBLIC_protocol_probe', 'strict': True,
            'schema': {'type': 'object', 'properties': {
                'probe': {'type': 'string', 'enum': ['PUBLIC-4ROUTER']},
                'result': {'type': 'string', 'enum': ['PUBLIC-OK']}},
                'required': ['probe', 'result'], 'additionalProperties': False}}}}
    return {'status': 'prepared_offline', 'input_scope': 'PUBLIC_fictional_only',
        'endpoint': binding['base_url'] + '/responses', 'request': request,
        'max_generate_requests': 2, 'max_count_requests': 0, 'cost': None,
        'execution_authorized': False}


def _run_protocol(transport, *, public_path=PUBLIC_CONFIG):
    prepared = prepare_probe(public_path=public_path)
    request = prepared['request']
    result = {'protocol_calls': 0, 'tool_call_valid': False, 'strict_json_valid': False}
    stage = 'first_response'
    try:
        result['protocol_calls'] += 1
        first = transport(prepared['endpoint'], copy.deepcopy(request))
        if first['status'] != 'completed' or first['model'] != request['model'] or len(first['output']) != 1:
            raise ValueError('invalid_first_response')
        call = first['output'][0]
        if (call['type'] != 'function_call' or call['name'] != 'read_evidence'
                or not isinstance(call['call_id'], str) or not call['call_id'].strip()
                or json.loads(call['arguments']) != {'evidence_refs': ['PUBLIC-REF-1']}):
            raise ValueError('invalid_tool_call')
        result['tool_call_valid'] = True
        request['input'].extend([copy.deepcopy(call), {'type': 'function_call_output',
            'call_id': call['call_id'], 'output': json.dumps({'marker': 'PUBLIC-OK'})}])
        request['tool_choice'] = 'none'
        stage = 'final_response'
        result['protocol_calls'] += 1
        final = transport(prepared['endpoint'], copy.deepcopy(request))
        if final['status'] != 'completed' or final['model'] != request['model'] or len(final['output']) != 1:
            raise ValueError('invalid_final_response')
        message = final['output'][0]
        if message['type'] != 'message' or len(message['content']) != 1:
            raise ValueError('invalid_final_message')
        content = message['content'][0]
        if (content['type'] != 'output_text' or json.loads(content['text']) != {
                'probe': 'PUBLIC-4ROUTER', 'result': 'PUBLIC-OK'}):
            raise ValueError('invalid_structured_output')
        return result | {'status': 'protocol_passed', 'strict_json_valid': True}
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return result | {'status': 'protocol_failed', 'error': stage}


def run_fixture_probe(transport, *, public_path=PUBLIC_CONFIG):
    """Test-only external transport injection; never establishes live provenance."""
    result = _run_protocol(transport, public_path=public_path)
    calls = result.pop('protocol_calls')
    return result | {'provenance': 'fixture', 'provider_requests_sent': 0, 'fixture_calls': calls,
        'cost': None, 'status': 'fixture_passed' if result['status'] == 'protocol_passed' else 'fixture_failed'}


def _safe_identifier(value, key):
    return value if (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9._:/-]{1,200}', value)
                     and key not in value) else None


def _native_usage(value):
    if value is None or type(value) is int and value >= 0:
        return value
    if isinstance(value, dict) and len(value) <= 32 and all(
            isinstance(k, str) and re.fullmatch(r'[a-z_]{1,64}', k) for k in value):
        clean = {k: _native_usage(v) for k, v in value.items()}
        if all(v is None or clean[k] is not None for k, v in value.items()):
            return clean
    return None


def _request_bytes(request, max_request_bytes=8192):
    raw = json.dumps(request).encode('utf-8')
    if type(max_request_bytes) is not int or not 0 < max_request_bytes <= 2 * 1024**2 or len(raw) > max_request_bytes:
        raise ValueError('request_body_limit')
    return raw


def send_response(endpoint, request, api_key, timeout, *, process_run=subprocess.run, max_request_bytes=8192):
    """One process, one POST; run() kills the worker on timeout, with no replay."""
    unknown = {'http_status': None, 'body': None, 'request_id': None}
    try:
        _request_bytes(request, max_request_bytes)
        child = process_run([sys.executable, '-B', str(Path(__file__).resolve()), '_http_once'],
            input=json.dumps({'endpoint': endpoint, 'request': request, 'api_key': api_key,
                              'timeout': timeout, 'max_request_bytes': max_request_bytes}).encode('utf-8'),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        if child.returncode != 0:
            return unknown
        result = json.loads(child.stdout)
        return result if isinstance(result, dict) else unknown
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return unknown


def http_response(endpoint, request, api_key, timeout, *, connection_factory=http.client.HTTPSConnection,
                  max_request_bytes=8192):
    """Single HTTPS request; HTTP redirects are returned, never followed."""
    result = {'http_status': None, 'body': None, 'request_id': None}
    if endpoint != 'https://4router.net/v1/responses':
        return result
    try:
        raw_body = _request_bytes(request, max_request_bytes)
    except ValueError:
        return result
    connection = connection_factory('4router.net', timeout=timeout)
    try:
        connection.request('POST', '/v1/responses', body=raw_body,
            headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        result.update(http_status=response.status, request_id=response.getheader('x-request-id'))
        raw = response.read(65537)
        if len(raw) <= 65536:
            result['body'] = json.loads(raw)
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        connection.close()
    return result


def run_live_probe(*, public_path=PUBLIC_CONFIG, credential_path=LOCAL_CREDENTIAL,
                   receipt_path=LIVE_RECEIPT, sender=send_response, clock=time.monotonic):
    """Consume this single PUBLIC authorization even when sending becomes uncertain."""
    result = {'provenance': 'live_HTTP', 'status': 'not_started', 'send_attempts': 0,
        'provider_requests_sent': 0, 'count_requests_sent': 0, 'other_API_requests_sent': 0,
        'responses': [], 'tool_call_valid': False, 'tool_result_sent': False,
        'strict_json_valid': False, 'request_body_bytes': [], 'cost': None, 'network_seconds': 0}
    receipt = Path(receipt_path)
    if receipt.exists():
        return result | {'status': 'authorization_already_consumed'}
    config = check_config(public_path=public_path, credential_path=credential_path)
    if not all(config.values()):
        return result | {'status': 'invalid_local_configuration'}
    key = json.loads(Path(credential_path).read_text(encoding='utf-8-sig'))['api_key']
    receipt.parent.mkdir(parents=True, exist_ok=True)
    try:
        journal = receipt.open('x', encoding='utf-8')
    except FileExistsError:
        return result | {'status': 'authorization_already_consumed'}
    with journal:
        def record():
            journal.write(json.dumps(result, ensure_ascii=True) + '\n')
            journal.flush()
        result['status'] = 'claimed'
        record()
        started = clock()
        def transport(endpoint, request):
            try:
                body_size = len(_request_bytes(request))
            except ValueError:
                result['error'] = 'request_body_limit'
                raise
            remaining = 60 - (clock() - started)
            if remaining <= 0:
                result['error'] = 'total_deadline'
                raise TimeoutError('probe_deadline')
            result['send_attempts'] += 1
            result['request_body_bytes'].append(body_size)
            result['provider_requests_sent'] = None
            result['status'] = 'sending'
            result['tool_call_valid'] = result['send_attempts'] == 2
            record()
            try:
                reply = sender(endpoint, request, key, min(30, remaining))
            except (OSError, ValueError):
                reply = {'http_status': None, 'body': None, 'request_id': None}
            body = reply.get('body')
            known = isinstance(reply.get('http_status'), int)
            result['responses'].append({'http_status': reply.get('http_status'),
                'model': _safe_identifier(body.get('model'), key) if isinstance(body, dict) else None,
                'request_id': _safe_identifier(reply.get('request_id'), key),
                'response_id': _safe_identifier(body.get('id'), key) if isinstance(body, dict) else None,
                'usage': _native_usage(body.get('usage')) if isinstance(body, dict) else None,
                'send_state': 'response_received' if known else 'unknown'})
            result['provider_requests_sent'] = result['send_attempts'] if known else None
            if result['send_attempts'] == 2:
                result['tool_result_sent'] = True if known else None
            record()
            if not known or reply['http_status'] != 200 or not isinstance(body, dict):
                result['error'] = 'HTTP_or_unknown_send_state'
                raise ValueError('HTTP_failure')
            return body
        protocol = _run_protocol(transport, public_path=public_path)
        result.update({k: v for k, v in protocol.items() if k != 'protocol_calls' and k != 'error'})
        if 'error' in protocol:
            result.setdefault('error', protocol['error'])
        result['network_seconds'] = round(clock() - started, 6)
        record()
    return result


def main(argv=None, *, public_path=PUBLIC_CONFIG, credential_path=LOCAL_CREDENTIAL,
         receipt_path=LIVE_RECEIPT, sender=send_response):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['check']:
        result = check_config(public_path=public_path, credential_path=credential_path)
        print(json.dumps(result))
        return 0 if result['local_config_valid'] else 2
    if argv == ['prepare']:
        try:
            result = prepare_probe(public_path=public_path)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            result = {'status': 'invalid_public_configuration'}
        print(json.dumps(result))
        return 0 if result['status'] == 'prepared_offline' else 2
    if argv == ['probe']:
        try:
            result = run_live_probe(public_path=public_path, credential_path=credential_path,
                                    receipt_path=receipt_path, sender=sender)
        except (OSError, ValueError, TypeError, KeyError):
            result = {'status': 'local_error_stopped', 'provider_requests_sent': None, 'cost': None}
        print(json.dumps(result))
        return 0 if result['status'] == 'protocol_passed' else 2
    if argv == ['_http_once']:
        try:
            data = json.loads(sys.stdin.buffer.read(8 * 1024**2 + 1))
            result = http_response(data['endpoint'], data['request'], data['api_key'], data['timeout'],
                                   max_request_bytes=data.get('max_request_bytes', 8192))
        except (OSError, ValueError, TypeError, KeyError):
            result = {'http_status': None, 'body': None, 'request_id': None}
        print(json.dumps(result))
        return 0
    print(json.dumps({'status': 'invalid_command'}))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
