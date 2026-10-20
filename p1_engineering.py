"""One D1/V00/S engineering grant; measured tokens/cost are not execution quotas."""
import copy

from evidence_access import RootBudget

AUTHORIZATION = 'S-ENGINEERING-ONCE-20261020'
RETRY_AUTHORIZATION = 'S-DEADLINE-RETRY-20261020'
AUTHORIZATIONS = (AUTHORIZATION, RETRY_AUTHORIZATION)
TASK = 'a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4'
UNKNOWN = ('input_tokens', 'output_tokens', 'cost_microusd')


def authorized(binding):
    return (binding.get('engineering_authorization') in AUTHORIZATIONS
        and binding.get('execution_authorized') is True
        and binding.get('execution_kind') == 'fourrouter_responses'
        and isinstance(binding.get('project_id'), str) and bool(binding['project_id'].strip())
        and (binding.get('model_id'), binding.get('channel'), binding.get('base_url')) == (
            'gpt-6-luna', '4Router', 'https://4router.net/v1'))


def reservation_deadline(budget, reservation_id):
    """The window frozen by reserve(), never shifted by subsequent I/O."""
    receipt = next(r for r in budget.receipts if r.get('reservation_id') == reservation_id and 'phase' in r)
    root_end = budget.started + budget.limits['elapsed_ms'] - (
        budget.final_reserve['elapsed_ms'] if receipt['phase'] == 'work' else 0)
    reserved_end = budget.started + receipt['usage_before']['elapsed_ms'] + receipt['held']['elapsed_ms']
    return min(root_end, reserved_end)


class SEngineeringBudget(RootBudget):
    resources = tuple(k for k in RootBudget.resources if k not in UNKNOWN) + ('request_output_tokens',)

    def __init__(self, binding, limits, final_reserve, **kwargs):
        public = (binding.get('fixture') == 'public_runtime_adapter'
            and binding['run_id'].startswith('PUBLIC-') and binding['root_task_id'].startswith('PUBLIC-'))
        real = (binding.get('task_key') == TASK and binding.get('fixture') is None
            and binding.get('plan_source_scope') == 'development_pilot'
            and binding.get('root_task_id') == '015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e'
            and binding.get('authorization_id') in AUTHORIZATIONS
            and binding['run_id'] == 'P1-D1-V00-S-' + binding['authorization_id'])
        if binding.get('method') != 'S' or not (public or real):
            raise ValueError('S_engineering_scope')
        if (not 1 <= limits['model_calls'] <= 12 or not 1500 <= limits['request_output_tokens'] <= 98304
                or limits['retries'] != 0 or limits['elapsed_ms'] > 350000
                or final_reserve['model_calls'] < 1 or final_reserve['request_output_tokens'] < 1500
                or final_reserve['elapsed_ms'] < 10000):
            raise ValueError('S_engineering_limits')
        self.metering = []
        super().__init__(binding, limits, final_reserve, **kwargs)

    def settle(self, reservation_id, observation):
        observation = copy.deepcopy(observation)
        operation = self.reservations[reservation_id]['operation']
        if isinstance(operation, dict) and operation.get('kind') == 'model':
            self.metering.append({k: observation['usage'].get(k) for k in UNKNOWN})
            observation['usage']['request_output_tokens'] = self.reservations[reservation_id]['held']['request_output_tokens']
        observation['usage'] = {k: v for k, v in observation['usage'].items() if k in self.resources}
        return super().settle(reservation_id, observation)

    def audit_view(self):
        result = super().audit_view()
        for key in UNKNOWN:
            values = [m[key] for m in self.metering]
            result['usage'][key] = sum(values) if values and all(v is not None for v in values) else None
        result.update(metering_status='unknown/incomplete', metering_reason='count_waived_rates_unknown_native_usage_optional',
            usage_exact=False, engineering_limits_settled=result['usage_exact'])
        return result


def invoke(adapter, request):
    """Keep prepared-body, reservation, nonce, deadline and response validation."""
    import provider_fourrouter as provider
    from model_adapter import REQUEST_KEYS, require, error_result, validate_call
    diagnostic = None
    try:
        budget = adapter.root_budget
        require(type(budget) is SEngineeringBudget and authorized(adapter.binding))
        if budget.binding.get('fixture') is None:
            require(adapter.binding['engineering_authorization'] == budget.binding['authorization_id'])
        require(set(request) == REQUEST_KEYS | {'output_schema', 'prepared_id', 'count_receipt_id'})
        require(request['count_receipt_id'] is None and request['input_token_upper_bound'] is None)
        prepared = adapter.prepared[request['prepared_id']]
        require(provider.verify_prepared(prepared) and prepared['wire_bytes'] <= 2 * 1024**2)
        again = adapter.prepare({k: v for k, v in request.items() if k not in ('prepared_id', 'count_receipt_id')})
        require(again.get('prepared_id') == prepared['prepared_id'])
        require(all(prepared['source'][k] == request[k] for k in ('run_id', 'session_id', 'role', 'output_kind')))
        audit = budget.audit_view()
        entry = budget.reservations[request['reservation_id']]
        cap = prepared['wire_body']['max_output_tokens']
        phase = 'final' if request['output_kind'] == 'final_submit' else 'work'
        require(type(cap) is int and 0 < cap <= (1500 if phase == 'final' else 8192))
        require(not audit['halted'] and budget.binding['run_id'] == request['run_id']
            and budget.binding.get('project_id') == prepared['project_id']
            and entry['settled'] is None and request['reservation_id'] not in adapter.native_attempts)
        require(all(entry['operation'].get(k) == v for k, v in {'kind': 'model',
            'request_id': request['request_id'], 'prepared_id': prepared['prepared_id'],
            'wire_sha256': prepared['wire_sha256'], 'count_receipt_id': None}.items()))
        require(entry['held']['model_calls'] == 1 and entry['held']['request_output_tokens'] >= cap)
        reservation = next(r for r in audit['receipts'] if r.get('reservation_id') == request['reservation_id'] and 'phase' in r)
        now, frozen_end = budget.clock(), reservation_deadline(budget, request['reservation_id'])
        diagnostic = {'request_id': request['request_id'], 'reservation_id': request['reservation_id'],
            'now_ms': now, 'deadline_ms': request['deadline_ms'], 'reserved_deadline_ms': frozen_end,
            'phase_matches': entry['phase'] == reservation['phase'] == phase,
            'not_expired': now <= request['deadline_ms'], 'within_reserved_window': request['deadline_ms'] <= frozen_end}
        require(all(diagnostic[k] for k in ('phase_matches', 'not_expired', 'within_reserved_window')))
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
        return provider.not_started(['S_engineering_reservation_or_deadline']) | {'preflight_diagnostic': diagnostic}
    adapter.native_attempts.add(request['reservation_id'])
    raw = None
    try:
        raw = adapter.transport(prepared['wire_utf8'], deadline_ms=request['deadline_ms'])
        result = provider.normalize(raw, request, pricing=None, engineering=True)
        calls = result['message']['tool_requests']
        prior = {c['call_id'] for m in request['messages'] for c in m.get('tool_requests', [])}
        require(len({c['call_id'] for c in calls}) == len(calls) and not prior.intersection(c['call_id'] for c in calls))
        for call in calls:
            validate_call(call, request['tools'])
        require(result['usage']['output_tokens'] is None or result['usage']['output_tokens'] <= cap)
    except (OSError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
        code = ('timeout' if isinstance(raw, dict) and raw.get('http_status') is None else
            'provider_binding_mismatch' if isinstance(raw, dict) and isinstance(raw.get('body'), dict)
            and raw['body'].get('model') != 'gpt-6-luna' else 'engineering_response_error')
        result = error_result(code, 'protocol', attempted=True)
    late = budget.clock() > request['deadline_ms']
    if late:
        result = error_result('timeout', 'timeout', attempted=True)
    fixture = adapter.binding.get('provenance') == 'fixture'
    diagnostic = provider.response_diagnostic(raw) if isinstance(raw, dict) else {
        'http_status': None, 'returned_model': None, 'response_id': None, 'request_id': None,
        'usage_diagnostic': {'state': 'unknown', 'usage': None}}
    result.update(provenance='fixture' if fixture else '4router', usage_basis=(
        'provider_native' if not fixture and diagnostic['usage_diagnostic']['state'] == 'accepted' else 'fixture' if fixture else None),
        provider_requests_sent=0 if fixture else 1 if isinstance(diagnostic['http_status'], int) else None,
        raw_response=diagnostic, usage_diagnostic=diagnostic['usage_diagnostic'],
        provider_request_id=diagnostic['request_id'], provider_response_id=diagnostic['response_id'],
        returned_model=diagnostic['returned_model'], metering_status='unknown/incomplete',
        metering_reason='count_waived_rates_unknown_native_usage_optional')
    if result.get('error'):
        result['error']['retryable'] = False
    return result
