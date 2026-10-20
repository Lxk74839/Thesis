"""4Router Responses mapping and guards; no count endpoint or credential discovery."""
import copy
import json
import math

from provider_openai import canonical, matches, prepare_responses, role_output_schema, sha

MODEL = 'gpt-6-luna'
CHANNEL = '4Router'
ENDPOINT = 'https://4router.net/v1/responses'
MAPPER = '4router-responses-mapper-0.1.0'
RATE_KEYS = ('input_microusd_per_million', 'output_microusd_per_million', 'cached_microusd_per_million')


def contract_missing(binding, counter):
    missing = []
    if (binding.get('model_id'), binding.get('channel'), binding.get('base_url')) != (
            MODEL, CHANNEL, 'https://4router.net/v1'):
        missing.append('exact_4router_binding')
    price = binding.get('pricing')
    if not isinstance(price, dict) or any(type(price.get(k)) is not int or price[k] < 0 for k in RATE_KEYS):
        missing.append('pricing')
    if counter is None:
        missing.append('verified_full_input_count')
    if type(binding.get('max_request_bytes')) is not int or not 0 < binding['max_request_bytes'] <= 2 * 1024**2:
        missing.append('max_request_bytes')
    if type(binding.get('context_token_limit')) is not int or binding['context_token_limit'] <= 0:
        missing.append('context_token_limit')
    if type(binding.get('max_output_tokens')) is not int or binding['max_output_tokens'] <= 0:
        missing.append('max_output_tokens')
    if binding.get('provenance') != 'fixture':
        if binding.get('execution_authorized') is not True:
            missing.append('execution_authorization')
        if type(binding.get('api_budget_microusd')) is not int or binding['api_budget_microusd'] <= 0:
            missing.append('api_budget_microusd')
        if binding.get('usage_policy') != 'require_native':
            missing.append('native_usage_policy')
    return missing


def not_started(missing):
    return {'status': 'not_started', 'attempted': False, 'missing': missing,
        'usage': dict.fromkeys(('input_tokens', 'output_tokens', 'cost_microusd')),
        'usage_known': False, 'provenance': '4router', 'usage_basis': None, 'raw_response': None,
        'provider_requests_sent': 0, 'error': {'category': 'configuration', 'code': 'not_started',
                                            'retryable': False, 'request_sent': False}}


def prepare(request, binding):
    from model_adapter import REQUEST_KEYS, validate_request
    if (binding.get('model_id') != MODEL or binding.get('channel') != CHANNEL
            or binding.get('base_url') != 'https://4router.net/v1'
            or request['execution_kind'] != 'fourrouter_responses' or request['model_id'] != MODEL):
        raise ValueError('4router_binding_mismatch')
    if binding.get('provenance') == 'fixture' and not request['run_id'].startswith('PUBLIC-'):
        raise ValueError('fixture_scope_mismatch')
    logical = {k: copy.deepcopy(v) for k, v in request.items() if k != 'output_schema'}
    if logical['schema_version'] == 'rsm-model-prepare-0.1.0':
        validate_request(logical, prepare_only=True)
    else:
        if set(request) != REQUEST_KEYS | {'output_schema'} or logical['schema_version'] != 'rsm-model-request-0.3.0':
            raise ValueError('invalid_native_request')
        logical['schema_version'] = 'rsm-model-request-0.2.0'
        validate_request(logical)
    result = prepare_responses(request, binding['project_id'], model_id=MODEL, mapper=MAPPER)
    result['schema_version'] = '4router-prepared-0.1.0'
    limit = binding.get('max_request_bytes')
    if type(limit) is int and result['wire_bytes'] > limit:
        result['missing'] = ['request_body_limit']
    return result


def usage_diagnostic(body):
    if not isinstance(body, dict):
        return {'state': 'unknown', 'usage': None}
    if 'usage' not in body:
        return {'state': 'field_absent', 'usage': None}
    raw = body['usage']
    if raw is None:
        return {'state': 'value_null', 'usage': None}
    try:
        i, o = raw['input_tokens'], raw['output_tokens']
        if any(type(v) is not int or v < 0 for v in (i, o)) or raw.get('total_tokens', i + o) != i + o:
            raise ValueError('invalid_usage')
        c = raw.get('input_tokens_details', {}).get('cached_tokens')
        r = raw.get('output_tokens_details', {}).get('reasoning_tokens')
        if any(v is not None and (type(v) is not int or not 0 <= v <= total) for v, total in ((c, i), (r, o))):
            raise ValueError('invalid_usage')
        return {'state': 'accepted', 'usage': {'input_tokens': i, 'output_tokens': o,
            'cached_input_tokens': c, 'reasoning_output_tokens': r}}
    except (ValueError, TypeError, KeyError, AttributeError):
        return {'state': 'parser_rejected', 'usage': None}


def verify_prepared(prepared):
    try:
        return (prepared['schema_version'] == '4router-prepared-0.1.0'
            and prepared['model_id'] == prepared['wire_body']['model'] == MODEL
            and prepared['mapper_version'] == MAPPER
            and prepared['wire_utf8'] == canonical(prepared['wire_body'])
            and prepared['wire_sha256'] == sha(prepared['wire_body'])
            and prepared['count_utf8'] == canonical(prepared['count_body'])
            and prepared['count_payload_sha256'] == sha(prepared['count_body'])
            and prepared['prepared_id'] == sha({k: prepared[k] for k in ('wire_sha256',
                'count_payload_sha256', 'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')}))
    except (ValueError, TypeError, KeyError):
        return False


def cost_microusd(i, o, cached=None, *, pricing):
    a, b, c = (pricing[k] for k in RATE_KEYS)
    if cached is None and a != c:
        raise ValueError('cached_usage_missing')
    cached = 0 if cached is None else cached
    return math.ceil(((i - cached) * a + cached * c + o * b) / 1000000)


def upper_cost(i, o, *, pricing):
    a, b, c = (pricing[k] for k in RATE_KEYS)
    return math.ceil((i * max(a, c) + o * b) / 1000000)


def normalized_usage(envelope, *, pricing):
    diagnostic = usage_diagnostic(envelope.get('body'))
    if diagnostic['state'] != 'accepted':
        raise ValueError('unknown_usage')
    usage = diagnostic['usage']
    try:
        cost = cost_microusd(usage['input_tokens'], usage['output_tokens'], usage['cached_input_tokens'], pricing=pricing)
    except ValueError:
        cost = None
    return usage | {'cost_microusd': cost}


def response_diagnostic(envelope):
    body = envelope.get('body')
    body = body if isinstance(body, dict) else {}
    return {'http_status': envelope.get('http_status'), 'returned_model': body.get('model'),
        'response_id': body.get('id'), 'request_id': envelope.get('request_id'),
        'usage_diagnostic': usage_diagnostic(body)}


def terminal_error(envelope):
    body = envelope.get('body')
    if isinstance(body, dict) and body.get('model') != MODEL:
        return 'provider_binding_mismatch', 'capability'
    if envelope.get('http_status') != 200:
        return 'HTTP_error', 'transport'
    if usage_diagnostic(body)['state'] != 'accepted':
        return 'unknown_usage', 'unknown_usage'
    return 'format_error', 'format'


def normalize(envelope, request, *, pricing):
    from model_adapter import validate_call
    body = envelope['body']
    if envelope['http_status'] != 200 or body['model'] != MODEL or body['status'] != 'completed':
        raise ValueError('invalid_response')
    if any(item['type'] not in ('function_call', 'message') for item in body['output']):
        raise ValueError('unsupported_output')
    calls = [{'call_id': item['call_id'], 'name': item['name'], 'arguments': json.loads(item['arguments'])}
             for item in body['output'] if item['type'] == 'function_call']
    texts = [c['text'] for item in body['output'] if item['type'] == 'message'
             for c in item['content'] if c['type'] == 'output_text']
    if calls:
        if texts:
            raise ValueError('mixed_output')
        for call in calls:
            validate_call(call, request['tools'])
        content = None
    else:
        content = json.loads(''.join(texts))
        if not matches(content, request['output_schema']):
            raise ValueError('invalid_role_output')
    usage = normalized_usage(envelope, pricing=pricing)
    if usage['cost_microusd'] is None:
        raise ValueError('unknown_cost')
    return {'status': 'ok', 'request_id': request['request_id'], 'attempted': True,
        'message': {'role': 'assistant', 'content': content, 'tool_requests': calls}, 'usage': usage,
        'raw_response': response_diagnostic(envelope), 'usage_known': True, 'error': None,
        'provider_request_id': envelope.get('request_id'), 'provider_response_id': body.get('id'),
        'returned_model': body['model']}


def make_sender(*, clock, max_request_bytes, credential_path=None, http_sender=None):
    from pathlib import Path
    from fourrouter_probe import LOCAL_CREDENTIAL, _safe_identifier, send_response
    path = Path(credential_path) if credential_path is not None else LOCAL_CREDENTIAL
    http_sender = send_response if http_sender is None else http_sender
    def sender(wire_utf8, *, deadline_ms):
        request = json.loads(wire_utf8)
        timeout = min(30, (deadline_ms - clock()) / 1000)
        if timeout <= 0:
            raise TimeoutError('before_send_deadline')
        if request.get('model') != MODEL or len(wire_utf8.encode('utf-8')) > max_request_bytes:
            raise OSError('4router_wire_or_size_mismatch')
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            key = data['api_key']
            if (set(data) != {'api_key'} or not isinstance(key, str) or not key
                    or any(c.isspace() or not 33 <= ord(c) <= 126 for c in key)):
                raise ValueError('invalid_credential')
        except (OSError, ValueError, TypeError, KeyError):
            raise OSError('credential_unavailable') from None
        reply = http_sender(ENDPOINT, request, key, timeout, max_request_bytes=max_request_bytes)
        reply['request_id'] = _safe_identifier(reply.get('request_id'), key)
        if isinstance(reply.get('body'), dict):
            for name in ('id', 'model'):
                reply['body'][name] = _safe_identifier(reply['body'].get(name), key)
        return reply
    return sender
