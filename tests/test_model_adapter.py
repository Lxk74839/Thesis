"""Native public transport examples; never a provider capability probe."""
import copy
import unittest


def request():
    return {'schema_version': 'rsm-model-request-0.1.0', 'execution_kind': 'scripted_public',
        'request_id': 'REQUEST', 'attempt_id': 'ATTEMPT', 'run_id': 'PUBLIC-RUN', 'session_id': 'PUBLIC-SESSION',
        'role': '需求解析', 'reply_to': None, 'model_id': None,
        'messages': [{'role': 'user', 'content': {'request': 'PUBLIC'}}], 'tools': [],
        'output_kind': 'analysis', 'max_output_tokens': 100, 'input_token_upper_bound': 1000,
        'deadline_ms': 45000, 'reservation_id': 'PUBLIC-RESERVATION'}


def response():
    return {'request_id': 'REQUEST', 'model_id': None, 'finish_reason': 'stop',
        'message': {'role': 'assistant', 'content': {'kind': 'analysis', 'data': {}}, 'tool_requests': []},
        'usage': {'input_tokens': 100, 'cached_input_tokens': 40, 'output_tokens': 30,
                  'reasoning_output_tokens': 20, 'cost_microusd': 0}, 'error': None}


class ModelAdapterTests(unittest.TestCase):
    def adapter(self, transport, **binding):
        from model_adapter import ModelAdapter
        return ModelAdapter(transport, capability_binding={'execution_kind': 'scripted_public',
                                                         'model_id': None, 'provenance': 'scripted', **binding})

    def test_cache_and_reasoning_are_subsets_not_additional_tokens(self):
        raw = response()
        result = self.adapter(lambda req: copy.deepcopy(raw)).invoke(request())
        self.assertEqual((result['usage']['input_tokens'], result['usage']['output_tokens']), (100, 30))
        self.assertEqual(result['raw_response'], raw)
        self.assertEqual(result['provider_requests_sent'], 0)
        self.assertEqual(result['usage_basis'], 'synthetic')

    def test_unbound_provider_mode_never_reaches_the_transport(self):
        def forbidden(req):
            self.fail('unbound provider was invoked')
        req = {**request(), 'execution_kind': 'provider_real', 'model_id': 'UNAPPROVED'}
        result = self.adapter(forbidden, execution_kind='provider_real', model_id='UNAPPROVED').invoke(req)
        self.assertEqual(result['status'], 'preflight_denied')
        self.assertFalse(result['attempted'])

    def test_extra_host_identity_and_unmatched_tool_results_are_rejected_before_transport(self):
        def forbidden(req):
            self.fail('invalid request reached transport')
        for req in ({**request(), 'principal_id': 'OVERRIDE'},
                    {**request(), 'messages': [{'role': 'tool', 'content': {}, 'tool_call_id': 'UNKNOWN'}]}):
            with self.subTest(req=req):
                result = self.adapter(forbidden).invoke(req)
                self.assertEqual(result['status'], 'invalid_request')
                self.assertFalse(result['attempted'])

    def test_malformed_responses_keep_known_usage_but_do_not_become_role_outputs(self):
        from evidence_access import EvidenceSession
        req = request()
        req['tools'] = EvidenceSession.tool_schemas()
        malformed = []
        wrong_id = response()
        wrong_id['request_id'] = 'OTHER'
        malformed.append(wrong_id)
        for calls in ([{'call_id': 'X', 'name': 'list_evidence', 'arguments': {'cursor': None}}] * 2,
                      [{'call_id': 'X', 'name': 'list_evidence', 'arguments': {'cursor': None, 'path': 'private'}}]):
            raw = response()
            raw.update(finish_reason='tool_calls', message={'role': 'assistant', 'content': None, 'tool_requests': calls})
            malformed.append(raw)
        raw = response()
        raw['message']['content']['kind'] = 'final_submit'
        malformed.append(raw)
        for raw in malformed:
            with self.subTest(raw=raw):
                result = self.adapter(lambda r: copy.deepcopy(raw)).invoke(req)
                self.assertEqual(result['status'], 'format_error')
                self.assertEqual(result['usage']['input_tokens'], 100)
                self.assertTrue(result['attempted'])

    def test_transport_timeout_refusal_and_unknown_usage_remain_distinct(self):
        def timeout(req):
            raise TimeoutError('PUBLIC timeout')
        result = self.adapter(timeout).invoke(request())
        self.assertEqual(result['error']['category'], 'timeout')
        self.assertIsNone(result['usage']['output_tokens'])
        raw = response()
        raw.update(finish_reason='refusal', message=None,
                   error={'category': 'refusal', 'code': 'PUBLIC-REFUSAL', 'request_sent': True})
        result = self.adapter(lambda req: raw).invoke(request())
        self.assertEqual(result['error']['category'], 'refusal')
        self.assertFalse(result['error']['retryable'])
        raw = response()
        raw['usage']['output_tokens'] = None
        result = self.adapter(lambda req: raw).invoke(request())
        self.assertFalse(result['usage_known'])
        self.assertEqual(result['status'], 'unknown_usage')

    def test_invalid_usage_is_never_reported_as_exact_or_serialized_as_nan(self):
        for field, value in (('input_tokens', True), ('cost_microusd', -1),
                             ('cached_input_tokens', 101), ('output_tokens', float('nan'))):
            raw = response()
            raw['usage'][field] = value
            with self.subTest(field=field):
                result = self.adapter(lambda req: raw).invoke(request())
                self.assertEqual(result['status'], 'format_error')
                self.assertFalse(result['usage_known'])

    def test_assistant_history_cannot_smuggle_tool_identity_or_reuse_a_prior_call(self):
        def forbidden(req):
            self.fail('malformed history reached transport')
        call = {'call_id': 'X', 'name': 'list_evidence', 'arguments': {'cursor': None, 'principal_id': 'OVERRIDE'}}
        req = request()
        req['messages'] += [{'role': 'assistant', 'content': None, 'tool_requests': [call]},
                            {'role': 'tool', 'tool_call_id': 'X', 'content': {'status': 'access_denied'}}]
        self.assertEqual(self.adapter(forbidden).invoke(req)['status'], 'invalid_request')
        call['arguments'].pop('principal_id')
        from evidence_access import EvidenceSession
        req['tools'] = EvidenceSession.tool_schemas()
        raw = response()
        raw.update(finish_reason='tool_calls', message={'role': 'assistant', 'content': None, 'tool_requests': [call]})
        self.assertEqual(self.adapter(lambda r: raw).invoke(req)['status'], 'format_error')
