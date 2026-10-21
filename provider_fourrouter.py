"""4Router Responses mapping and guards; no count endpoint or credential discovery."""
import copy
import json
import math

from provider_openai import canonical, matches, prepare_responses, role_output_schema, sha

MODEL = 'gpt-6-luna'
CHANNEL = '4Router'
ENDPOINT = 'https://4router.net/v1/responses'
MAPPER = '4router-responses-mapper-0.2.0'
RATE_KEYS = ('input_microusd_per_million', 'output_microusd_per_million', 'cached_microusd_per_million')
REASONING_FIELDS = {'type', 'id', 'summary', 'content', 'encrypted_content', 'status'}


class ProtocolError(ValueError):
    """Fixed codes and structural locations, never provider text or exception prose."""
    def __init__(self, stage, code, **location):
        self.diagnostic = {'stage': stage, 'code': code, **location}
        super().__init__(code)


def output_structure(item, index):
    """Known names and shapes only: no text, ciphertext, or unknown field names."""
    def field(value):
        result = {'present': True, 'type': {dict: 'object', list: 'array', str: 'string', int: 'integer',
            float: 'number', bool: 'boolean', type(None): 'null'}.get(type(value), 'unknown')}
        if isinstance(value, (str, list, dict)):
            result['length'] = len(value)
        return result
    if not isinstance(item, dict):
        return {'output_index': index, 'type': 'unknown', 'item': field(item)}
    known = REASONING_FIELDS | {'call_id', 'name', 'arguments', 'role', 'phase'}
    return {'output_index': index, 'type': item.get('type') if item.get('type') in (
        'reasoning', 'function_call', 'message', 'refusal') else 'unknown',
        'fields': {k: field(item[k]) if k in item else {'present': False} for k in sorted(known)},
        'unknown_field_count': len(set(item) - known)}


def validate_reasoning(item, index):
    def reject(code, name, **location):
        raise ProtocolError('reasoning', code, field=name, output_index=index,
            structure=output_structure(item, index), **location)
    if set(item) - REASONING_FIELDS:
        reject('reasoning_unknown_fields', 'reasoning', unexpected_field_count=len(set(item) - REASONING_FIELDS))
    for name in ('id', 'type', 'summary'):
        if name not in item:
            reject('reasoning_required_field', name)
    if not isinstance(item['id'], str) or not item['id']:
        reject('reasoning_invalid_id', 'id')
    if item['type'] != 'reasoning':
        reject('reasoning_invalid_type', 'type')
    if 'status' in item and item['status'] not in ('in_progress', 'completed', 'incomplete'):
        reject('reasoning_invalid_status', 'status')
    if 'encrypted_content' in item and item['encrypted_content'] is not None and not isinstance(item['encrypted_content'], str):
        reject('reasoning_invalid_encrypted_type', 'encrypted_content')
    for name, kind in (('summary', 'summary_text'), ('content', 'reasoning_text')):
        if name not in item:
            continue
        if not isinstance(item[name], list):
            reject('reasoning_invalid_array', name)
        for part_index, part in enumerate(item[name]):
            if not isinstance(part, dict) or set(part) != {'type', 'text'}:
                reject('reasoning_invalid_part_fields', name, part_index=part_index)
            if part['type'] != kind:
                reject('reasoning_invalid_part_type', name, part_index=part_index)
            if not isinstance(part['text'], str):
                reject('reasoning_invalid_part_text', name, part_index=part_index)


def _decode_response_JSON(text, code, **location):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError('json_decode', code, position=exc.pos, line=exc.lineno,
            column=exc.colno, **location) from None
    except (TypeError, ValueError):
        raise ProtocolError('json_decode', code, **location) from None


def contract_missing(binding, counter):
    missing = []
    from p1_engineering import authorized
    if authorized(binding):
        if binding.get('max_request_bytes') != 2 * 1024**2 or binding.get('max_output_tokens') != 8192:
            missing.append('S_engineering_request_limits')
        return missing
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


def prepare(request, binding, *, continuations=None):
    from model_adapter import REQUEST_KEYS, validate_request
    if (binding.get('model_id') != MODEL or binding.get('channel') != CHANNEL
            or binding.get('base_url') != 'https://4router.net/v1'
            or request['execution_kind'] != 'fourrouter_responses' or request['model_id'] != MODEL):
        raise ValueError('4router_binding_mismatch')
    if binding.get('provenance') == 'fixture' and not request['run_id'].startswith('PUBLIC-'):
        raise ValueError('fixture_scope_mismatch')
    logical = {k: copy.deepcopy(v) for k, v in request.items() if k != 'output_schema'}
    from p1_engineering import authorized
    if authorized(binding):
        for k in ('input_token_upper_bound', 'deadline_ms', 'reservation_id'):
            logical.pop(k, None)
        logical['schema_version'] = 'rsm-model-prepare-0.1.0'
    if logical['schema_version'] == 'rsm-model-prepare-0.1.0':
        validate_request(logical, prepare_only=True)
    else:
        if set(request) != REQUEST_KEYS | {'output_schema'} or logical['schema_version'] != 'rsm-model-request-0.3.0':
            raise ValueError('invalid_native_request')
        logical['schema_version'] = 'rsm-model-request-0.2.0'
        validate_request(logical)
    protocol_items = {}
    native_session = any(stored['owner'] == [request['run_id'], request['session_id']]
        for stored in (continuations or {}).values())
    for index, message in enumerate(request['messages']):
        if 'protocol_ref' not in message:
            if native_session and message.get('role') == 'assistant':
                raise ProtocolError('continuation', 'missing_protocol_reference', field='protocol_ref', message_index=index)
            continue
        stored = (continuations or {}).get(message['protocol_ref'])
        business = {k: v for k, v in message.items() if k != 'protocol_ref'}
        if (not stored or stored['owner'] != [request['run_id'], request['session_id']]
                or stored['message'] != business):
            raise ProtocolError('continuation', 'invalid_protocol_reference', field='protocol_ref', message_index=index)
        protocol_items[index] = stored['items']
    result = prepare_responses(request, binding['project_id'], model_id=MODEL, mapper=MAPPER,
        protocol_items=protocol_items, include_reasoning=True)
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


def engineering_usage(envelope):
    """Independently observed counters survive unrelated output protocol failures."""
    diagnostic = usage_diagnostic(envelope.get('body') if isinstance(envelope, dict) else None)
    return (diagnostic['usage'] or dict.fromkeys(('input_tokens', 'output_tokens',
        'cached_input_tokens', 'reasoning_output_tokens'))) | {'cost_microusd': None}


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
    from fourrouter_probe import _native_usage
    body = envelope.get('body')
    body = body if isinstance(body, dict) else {}
    return {'http_status': envelope.get('http_status'), 'returned_model': body.get('model'),
        'response_id': body.get('id'), 'request_id': envelope.get('request_id'),
        'usage_diagnostic': usage_diagnostic(envelope.get('body')), 'native_usage': _native_usage(body.get('usage')),
        'output_structure': [output_structure(item, n) for n, item in enumerate(body.get('output', []))]
            if isinstance(body.get('output'), list) else None,
        'request_body_bytes': envelope.get('request_body_bytes')}


def terminal_error(envelope):
    body = envelope.get('body')
    if isinstance(body, dict) and body.get('model') != MODEL:
        return 'provider_binding_mismatch', 'capability'
    if envelope.get('http_status') != 200:
        return 'HTTP_error', 'transport'
    if usage_diagnostic(body)['state'] != 'accepted':
        return 'unknown_usage', 'unknown_usage'
    return 'format_error', 'format'


def normalize(envelope, request, *, pricing, engineering=False, continuations=None):
    from model_adapter import validate_call
    if not isinstance(envelope, dict):
        raise ProtocolError('response_status', 'invalid_response_envelope', field='body')
    if envelope.get('http_status') != 200:
        raise ProtocolError('response_status', 'http_status_not_200', field='http_status')
    if not isinstance(envelope.get('body'), dict):
        raise ProtocolError('response_status', 'invalid_response_body', field='body')
    body = envelope['body']
    if body.get('model') != MODEL:
        raise ProtocolError('response_status', 'model_mismatch', field='model')
    if body.get('status') != 'completed':
        status = body.get('status')
        raise ProtocolError('response_status', 'response_not_completed', field='status',
            status=status if status in ('incomplete', 'failed', 'cancelled', 'queued', 'in_progress') else 'unknown')
    if not isinstance(body.get('output'), list) or not body['output']:
        raise ProtocolError('output_item', 'invalid_output_shape', field='output')
    calls, texts, seen, reasoning_items = [], [], set(), []
    prior = {c['call_id'] for m in request['messages'] for c in m.get('tool_requests', [])}
    for index, item in enumerate(body['output']):
        if not isinstance(item, dict):
            raise ProtocolError('output_item', 'invalid_output_item', field='output', output_index=index)
        kind = item.get('type')
        if kind == 'reasoning':
            validate_reasoning(item, index)
            reasoning_items.append({'output_index': index, 'id': item['id'], 'summary_count': len(item['summary'])})
            continue
        if kind not in ('function_call', 'message'):
            raise ProtocolError('output_item', 'unsupported_output_type', field='type', output_index=index,
                item_type=kind if kind in ('reasoning', 'refusal') else 'unknown')
        if kind == 'function_call':
            arguments = _decode_response_JSON(item.get('arguments'), 'invalid_tool_JSON',
                field='arguments', output_index=index)
            call = {'call_id': item.get('call_id'), 'name': item.get('name'), 'arguments': arguments}
            try:
                validate_call(call, request['tools'])
            except (ValueError, TypeError, KeyError):
                raise ProtocolError('tool_call', 'invalid_tool_call', field='function_call', output_index=index) from None
            if call['call_id'] in seen or call['call_id'] in prior:
                raise ProtocolError('tool_call', 'reused_tool_call_id', field='call_id', output_index=index)
            seen.add(call['call_id'])
            calls.append(call)
        else:
            if not isinstance(item.get('content'), list):
                raise ProtocolError('output_item', 'invalid_content_shape', field='content', output_index=index)
            for content_index, part in enumerate(item['content']):
                if not isinstance(part, dict) or part.get('type') != 'output_text':
                    raise ProtocolError('output_item', 'unsupported_content_type', field='type',
                        output_index=index, content_index=content_index)
                if not isinstance(part.get('text'), str):
                    raise ProtocolError('output_item', 'invalid_output_text', field='text',
                        output_index=index, content_index=content_index)
                texts.append(part['text'])
    if calls:
        if texts:
            raise ProtocolError('output_item', 'mixed_tool_and_text_output', field='output')
        content = None
    else:
        content = _decode_response_JSON(''.join(texts), 'invalid_role_JSON', field='output_text')
        if not matches(content, request['output_schema']):
            raise ProtocolError('role_schema', 'role_schema_mismatch', field='output_schema')
    if engineering:
        diagnostic = usage_diagnostic(body)
        if diagnostic['state'] == 'parser_rejected':
            raise ProtocolError('native_usage', 'invalid_native_usage', field='usage')
        usage = engineering_usage(envelope)
    else:
        try:
            usage = normalized_usage(envelope, pricing=pricing)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ProtocolError('native_usage', 'native_usage_unavailable', field='usage') from None
    if not engineering and usage['cost_microusd'] is None:
        raise ProtocolError('native_usage', 'native_cost_unknown', field='cost_microusd')
    message = {'role': 'assistant', 'content': content, 'tool_requests': calls}
    if continuations is not None:
        ref = sha([request['run_id'], request['session_id'], body['output'], message])
        continuations[ref] = {'owner': [request['run_id'], request['session_id']],
            'message': copy.deepcopy(message), 'items': copy.deepcopy(body['output'])}
        message['protocol_ref'] = ref
    elif calls and reasoning_items:
        raise ProtocolError('continuation', 'protocol_context_required', field='protocol_ref')
    return {'status': 'ok', 'request_id': request['request_id'], 'attempted': True,
        'message': message, 'usage': usage,
        'raw_response': response_diagnostic(envelope) | ({'reasoning_items': reasoning_items} if reasoning_items else {}),
        'usage_known': not engineering, 'error': None,
        'provider_request_id': envelope.get('request_id'), 'provider_response_id': body.get('id'),
        'returned_model': body['model']}


def prepared_diagnostic(prepared):
    """Persist identities, never native wire/count bodies holding opaque state."""
    return {k: copy.deepcopy(v) for k, v in prepared.items()
        if k not in ('wire_body', 'wire_utf8', 'count_body', 'count_utf8')}


def make_sender(*, clock, max_request_bytes, credential_path=None, http_sender=None, storage_guard=None, http_timeout_seconds=30):
    from pathlib import Path
    from fourrouter_probe import LOCAL_CREDENTIAL, _safe_identifier, send_response, _request_bytes
    path = Path(credential_path) if credential_path is not None else LOCAL_CREDENTIAL
    if http_timeout_seconds not in (30, 120):
        raise ValueError('invalid_HTTP_window')
    http_sender = send_response if http_sender is None else http_sender
    def sender(wire_utf8, *, deadline_ms):
        request = json.loads(wire_utf8)
        timeout = min(http_timeout_seconds, (deadline_ms - clock()) / 1000)
        if timeout <= 0:
            raise TimeoutError('before_send_deadline')
        if request.get('model') != MODEL or len(wire_utf8.encode('utf-8')) > max_request_bytes:
            raise OSError('4router_wire_or_size_mismatch')
        try:
            body_bytes = len(_request_bytes(request, max_request_bytes))
        except ValueError:
            raise OSError('actual_POST_body_limit') from None
        try:
            if storage_guard is not None:
                storage_guard.credential_read = path.absolute()
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
            finally:
                if storage_guard is not None:
                    storage_guard.credential_read = None
            key = data['api_key']
            if (set(data) != {'api_key'} or not isinstance(key, str) or not key
                    or any(c.isspace() or not 33 <= ord(c) <= 126 for c in key)):
                raise ValueError('invalid_credential')
        except (OSError, ValueError, TypeError, KeyError):
            raise OSError('credential_unavailable') from None
        if storage_guard is not None:
            storage_guard.sender_active = True
        try:
            if storage_guard is not None and hasattr(storage_guard, 'claim_S_request'):
                storage_guard.claim_S_request(request)
            timeout = min(http_timeout_seconds, (deadline_ms - clock()) / 1000)
            if timeout <= 0:
                raise TimeoutError('before_send_deadline')
            reply = http_sender(ENDPOINT, request, key, timeout, max_request_bytes=max_request_bytes)
        finally:
            if storage_guard is not None:
                storage_guard.sender_active = False
        reply['request_id'] = _safe_identifier(reply.get('request_id'), key)
        reply['request_body_bytes'] = body_bytes
        if isinstance(reply.get('body'), dict):
            for name in ('id', 'model'):
                reply['body'][name] = _safe_identifier(reply['body'].get(name), key)
        return reply
    return sender
