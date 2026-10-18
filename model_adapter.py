"""Closed native message seam. Only explicitly scripted transports are bound here."""
import copy
import json


ROLES = ('需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验', '单智能体')
REQUEST_KEYS = set('schema_version execution_kind request_id attempt_id run_id session_id role reply_to model_id '
                   'messages tools output_kind max_output_tokens input_token_upper_bound deadline_ms reservation_id'.split())


def require(value):
    if not value:
        raise ValueError('invalid_model_contract')


def error_result(status, category, *, attempted=False, usage=None, raw=None):
    try:
        json.dumps(raw, allow_nan=False)
    except (ValueError, TypeError):
        raw = repr(raw)
    return {'status': status, 'attempted': attempted, 'error': {'category': category, 'code': status,
        'retryable': category in ('format', 'transport', 'timeout', 'truncated', 'rate_limit'),
        'request_sent': None if attempted else False},
        'usage': usage or dict.fromkeys(('input_tokens', 'output_tokens', 'cost_microusd'), None if attempted else 0),
        'provider_requests_sent': 0, 'usage_basis': 'synthetic', 'provenance': 'scripted', 'raw_response': raw,
        'usage_known': usage is not None and all(usage.get(k) is not None for k in
                                                ('input_tokens', 'output_tokens', 'cost_microusd'))}


def validate_request(request):
    require(isinstance(request, dict) and set(request) == REQUEST_KEYS)
    require(request['schema_version'] in ('rsm-model-request-0.1.0', 'rsm-model-request-0.2.0') and request['role'] in ROLES)
    tool_names = ('candidate_page', 'list_evidence', 'read_evidence') + (
        ('acquire_batch',) if request['schema_version'] == 'rsm-model-request-0.2.0' else ())
    require(all(isinstance(request[k], str) and request[k] for k in
                ('request_id', 'attempt_id', 'run_id', 'session_id', 'reservation_id')))
    require(request['reply_to'] is None or isinstance(request['reply_to'], str))
    require(request['output_kind'] in ('analysis', 'dispatch', 'draft', 'verification', 'final_submit', 'acquire'))
    require(all(type(request[k]) is int and request[k] >= 0 for k in
                ('max_output_tokens', 'input_token_upper_bound', 'deadline_ms')))
    json.dumps(request, allow_nan=False)
    require(isinstance(request['messages'], list) and bool(request['messages']))
    pending, seen = set(), set()
    for message in request['messages']:
        require(isinstance(message, dict) and message.get('role') in ('system', 'user', 'assistant', 'tool'))
        allowed = {'role', 'content'} | ({'tool_call_id'} if message['role'] == 'tool' else
                                      {'tool_requests'} if message['role'] == 'assistant' else set())
        require({'role', 'content'} <= set(message) <= allowed)
        if message['role'] == 'tool':
            require(message.get('tool_call_id') in pending)
            pending.remove(message['tool_call_id'])
        else:
            require(not pending)
            require(isinstance(message.get('tool_requests', []), list))
            require(not message.get('tool_requests') or message['content'] is None)
            for call in message.get('tool_requests', []):
                validate_call(call, [{'name': n} for n in tool_names])
                require(call['call_id'] not in seen)
                pending.add(call['call_id'])
                seen.add(call['call_id'])
    require(not pending)
    require(isinstance(request['tools'], list) and all(t.get('name') in
        tool_names for t in request['tools']))


def validate_call(call, tools):
    require(isinstance(call, dict) and set(call) == {'call_id', 'name', 'arguments'})
    require(isinstance(call['call_id'], str) and bool(call['call_id']))
    require(call['name'] in {t['name'] for t in tools} and isinstance(call['arguments'], dict))
    args = call['arguments']
    if call['name'] == 'acquire_batch':
        require(set(args) == {'schema_version', 'start_candidate', 'candidate_limit', 'claim_ids',
                              'max_list_pages', 'max_read_batches', 'stop_policy'})
        require(args['schema_version'] == 'acquisition-batch-0.1.0' and isinstance(args['start_candidate'], str))
        require(all(type(args[k]) is int and args[k] >= 1
                    for k in ('candidate_limit', 'max_list_pages', 'max_read_batches')) and args['candidate_limit'] <= 32)
        require(isinstance(args['claim_ids'], list) and all(isinstance(c, str) for c in args['claim_ids']))
        require(args['stop_policy'] in ('first_10_qualified', 'fixed_prefix'))
    elif call['name'] == 'read_evidence':
        require(set(args) == {'evidence_refs'} and isinstance(args['evidence_refs'], list))
        refs = args['evidence_refs']
        require(1 <= len(refs) <= 32 and all(isinstance(r, str) and r for r in refs) and len(set(refs)) == len(refs))
    else:
        keys = {'cursor', 'order'} if call['name'] == 'candidate_page' else {'cursor'}
        require(set(args) == keys and (args['cursor'] is None or isinstance(args['cursor'], str)))
        if 'order' in args:
            require(args['order'] in ('parent', 'base'))


class ModelAdapter:
    version = 'rsm-model-adapter-0.1.0'

    def __init__(self, transport, *, capability_binding, counter=None, root_budget=None):
        self.transport = transport
        self.binding = copy.deepcopy(capability_binding)
        self.prepared = {}
        self.counter, self.root_budget = counter, root_budget
        self.native_attempts = set()

    def prepare(self, request):
        from provider_openai import MODEL, prepare
        try:
            require(set(request) == REQUEST_KEYS | {'output_schema'})
            require(request['schema_version'] == 'rsm-model-request-0.3.0')
            require(self.binding == {'execution_kind': 'openai_native_fixture', 'model_id': MODEL,
                                    'provenance': 'fixture', 'project_id': self.binding.get('project_id')}
                    and isinstance(self.binding['project_id'], str) and bool(self.binding['project_id']))
            require(request['execution_kind'] == 'openai_native_fixture' and request['model_id'] == MODEL)
            legacy = {k: copy.deepcopy(v) for k, v in request.items() if k != 'output_schema'}
            legacy['schema_version'] = 'rsm-model-request-0.2.0'
            validate_request(legacy)
            result = prepare(request, self.binding['project_id'])
            self.prepared[result['prepared_id']] = copy.deepcopy(result)
            return copy.deepcopy(result)
        except (ValueError, TypeError, KeyError, AttributeError):
            return {'status': 'invalid_request', 'input_tokens': None, 'missing': ['invalid_native_contract']}

    def invoke(self, request):
        if isinstance(request, dict) and request.get('schema_version') == 'rsm-model-request-0.3.0':
            return self._invoke_native(request)
        try:
            validate_request(request)
        except (ValueError, TypeError, KeyError, AttributeError):
            return error_result('invalid_request', 'format')
        if (self.binding != {'execution_kind': 'scripted_public', 'model_id': None, 'provenance': 'scripted'}
                or request.get('execution_kind') != 'scripted_public' or request.get('model_id') is not None):
            return error_result('preflight_denied', 'capability')
        try:
            raw = self.transport(copy.deepcopy(request))
        except (OSError, TimeoutError) as exc:
            category = 'timeout' if isinstance(exc, TimeoutError) else 'transport'
            return error_result(category, category, attempted=True, raw={'exception': str(exc)})
        usage = copy.deepcopy(raw.get('usage')) if isinstance(raw, dict) else None
        try:
            require(isinstance(usage, dict) and {'input_tokens', 'output_tokens', 'cost_microusd'} <= set(usage)
                    <= {'input_tokens', 'output_tokens', 'cost_microusd', 'cached_input_tokens', 'reasoning_output_tokens'})
            require(all(v is None or type(v) is int and v >= 0 for v in usage.values()))
            for subset, total in (('cached_input_tokens', 'input_tokens'), ('reasoning_output_tokens', 'output_tokens')):
                require(usage.get(subset) is None or usage[total] is None or usage[subset] <= usage[total])
        except (ValueError, TypeError, KeyError):
            return error_result('format_error', 'format', attempted=True, raw=copy.deepcopy(raw))
        try:
            require(isinstance(raw, dict) and set(raw) == {'request_id', 'model_id', 'finish_reason', 'message', 'usage', 'error'})
            require(raw['request_id'] == request['request_id'] and raw['model_id'] is None)
            if raw['finish_reason'] in ('refusal', 'length', 'error'):
                category = 'refusal' if raw['finish_reason'] == 'refusal' else 'truncated' if raw['finish_reason'] == 'length' else raw['error']['category']
                require(category in ('refusal', 'truncated', 'auth', 'capability', 'rate_limit', 'transport', 'timeout'))
                return error_result(category, category, attempted=True, usage=usage, raw=copy.deepcopy(raw))
            require(raw['error'] is None)
            message = raw['message']
            require(isinstance(message, dict) and set(message) == {'role', 'content', 'tool_requests'} and message['role'] == 'assistant')
            require(isinstance(message['tool_requests'], list))
            calls = message['tool_requests']
            if calls:
                require(raw['finish_reason'] == 'tool_calls' and message['content'] is None)
                for call in calls:
                    validate_call(call, request['tools'])
                prior = {c['call_id'] for m in request['messages'] for c in m.get('tool_requests', [])}
                require(not prior.intersection(c['call_id'] for c in calls))
                require(len({c['call_id'] for c in calls}) == len(calls))
            else:
                content = message['content']
                require(raw['finish_reason'] == 'stop' and isinstance(content, dict)
                        and set(content) == {'kind', 'data'} and content['kind'] == request['output_kind']
                        and isinstance(content['data'], dict))
            json.dumps(raw, allow_nan=False)
        except (ValueError, TypeError, KeyError, AttributeError):
            return error_result('format_error', 'format', attempted=True, usage=usage, raw=copy.deepcopy(raw))
        if usage is None or any(usage.get(k) is None for k in ('input_tokens', 'output_tokens', 'cost_microusd')):
            return error_result('unknown_usage', 'unknown_usage', attempted=True, usage=usage, raw=copy.deepcopy(raw))
        return {'status': 'ok', 'request_id': request['request_id'], 'message': copy.deepcopy(raw['message']),
                'usage': copy.deepcopy(raw['usage']), 'raw_response': copy.deepcopy(raw),
                'usage_basis': 'synthetic', 'provenance': 'scripted', 'provider_requests_sent': 0,
                'attempted': True, 'usage_known': True, 'error': None}

    def _invoke_native(self, request):
        from provider_openai import cost_microusd, normalize, normalized_usage, terminal_error, verify_prepared
        try:
            require(set(request) == REQUEST_KEYS | {'output_schema', 'prepared_id', 'count_receipt_id'})
            prepared = copy.deepcopy(self.prepared[request['prepared_id']])
            require(verify_prepared(prepared))
            again = self.prepare({k: v for k, v in request.items() if k not in ('prepared_id', 'count_receipt_id')})
            require(again.get('prepared_id') == prepared['prepared_id'])
            require(all(prepared['source'][k] == request[k] for k in ('run_id', 'session_id', 'role', 'output_kind')))
            count = self.counter.count(prepared, authorization=None)
            require(count['status'] == 'counted' and count['basis'] == 'fixture'
                    and count['receipt_id'] == request['count_receipt_id'])
            i, cap = count['input_tokens'], prepared['wire_body']['max_output_tokens']
            require(request['input_token_upper_bound'] == i and 0 < cap <= 128000 and i + cap <= 400000)
            audit = self.root_budget.audit_view()
            entry = audit['reservations'][request['reservation_id']]
            require(not audit['halted'] and audit['binding']['run_id'] == request['run_id']
                    and audit['binding'].get('project_id') == prepared['project_id']
                    and entry['settled'] is None and request['reservation_id'] not in self.native_attempts)
            require(all(entry['operation'].get(k) == v for k, v in {'kind': 'model', 'request_id': request['request_id'],
                'prepared_id': prepared['prepared_id'], 'wire_sha256': prepared['wire_sha256'],
                'count_receipt_id': count['receipt_id']}.items()))
            require(all(entry['held'][k] >= v for k, v in {'model_calls': 1, 'input_tokens': i,
                'output_tokens': cap, 'cost_microusd': cost_microusd(i, cap)}.items()))
            reservation = next(r for r in audit['receipts'] if r.get('reservation_id') == request['reservation_id'] and 'phase' in r)
            phase = 'final' if request['output_kind'] == 'final_submit' else 'work'
            end = self.root_budget.started + audit['limits']['elapsed_ms'] - (audit['final_reserve']['elapsed_ms'] if phase == 'work' else 0)
            reserved_end = self.root_budget.started + reservation['usage_before']['elapsed_ms'] + entry['held']['elapsed_ms']
            require(reservation['phase'] == phase and self.root_budget.clock() <= request['deadline_ms'] <= min(end, reserved_end))
        except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
            return error_result('preflight_denied', 'capability')
        self.native_attempts.add(request['reservation_id'])
        try:
            raw = self.transport(prepared['wire_utf8'], deadline_ms=request['deadline_ms'])
        except (OSError, TimeoutError) as exc:
            result = error_result('timeout' if isinstance(exc, TimeoutError) else 'transport',
                                  'timeout' if isinstance(exc, TimeoutError) else 'transport', attempted=True, raw=str(exc))
        else:
            try:
                result = normalize(raw, request)
                calls = result['message']['tool_requests']
                prior = {c['call_id'] for m in request['messages'] for c in m.get('tool_requests', [])}
                require(len({c['call_id'] for c in calls}) == len(calls) and not prior.intersection(c['call_id'] for c in calls))
                for call in calls:
                    validate_call(call, request['tools'])
            except (ValueError, TypeError, KeyError, AttributeError):
                try:
                    usage = normalized_usage(raw)
                except (ValueError, TypeError, KeyError, AttributeError):
                    usage = None
                status, category = terminal_error(raw) if isinstance(raw, dict) else ('format_error', 'format')
                if status in ('provider_binding_mismatch', 'unsupported_provider_tool') and usage is not None:
                    usage['cost_microusd'] = None
                result = error_result(status, category, attempted=True, usage=usage, raw=copy.deepcopy(raw))
            usage = result['usage']
            if (usage.get('input_tokens') is not None and usage['input_tokens'] != i
                    or usage.get('output_tokens') is not None and usage['output_tokens'] > cap
                    or usage.get('cost_microusd') is not None and usage['cost_microusd'] > entry['held']['cost_microusd']):
                result = error_result('usage_mismatch', 'capability', attempted=True,
                                      usage=usage, raw=copy.deepcopy(raw))
            body = raw.get('body', {}) if isinstance(raw, dict) else {}
            body = body if isinstance(body, dict) else {}
            headers = raw.get('headers') if isinstance(raw, dict) and isinstance(raw.get('headers'), dict) else {}
            result.update(provider_request_id=headers.get('x-request-id'),
                provider_response_id=body.get('id'), returned_model=body.get('model'), service_tier=body.get('service_tier'))
        if self.root_budget.clock() > request['deadline_ms']:
            result = {**result, 'status': 'usage_mismatch' if result['status'] == 'usage_mismatch' else 'timeout', 'late': True,
                'error': {'category': 'timeout', 'code': 'late_result', 'retryable': False, 'request_sent': None}}
            result.pop('message', None)
        result.update(provenance='fixture', usage_basis='fixture', provider_requests_sent=0)
        return result
