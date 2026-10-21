"""Synthetic PUBLIC HTTP fixtures, no actual network or authentication."""
import json
from pathlib import Path
import subprocess
import unittest

from tests.test_p1_s_engineering import setUpModule
from fourrouter_probe import http_response, send_response


KEY = 'PUBLIC-SYNTHETIC-KEY'


def fixture_http(raw, *, status=408, headers=None, fail=None, **limits):
    class Connection:
        def __init__(self, host, timeout):
            self.status = status
        def request(self, *args, **kwargs):
            if fail:
                raise fail
        def getresponse(self):
            return self
        def getheader(self, name):
            return (headers or {}).get(name)
        def read(self, maximum):
            return raw[:maximum]
        def close(self):
            pass
    return http_response('https://4router.net/v1/responses', {'model': 'gpt-6-luna'},
        KEY, 120, connection_factory=Connection, **limits)


class HTTPDiagnostics(unittest.TestCase):
    def test_explicit_development_response_limit_keeps_large_valid_envelopes_bounded(self):
        from tests.test_fourrouter_protocol_diagnostics import public_response, public_request
        from tests.test_fourrouter_production_protocol import reasoning
        from provider_fourrouter import normalize, ProtocolError
        body = public_response()['body']
        body['output'].insert(0, reasoning() | {'encrypted_content': 'PUBLIC-opaque-' + 'x' * 70000})
        raw = json.dumps(body).encode()
        self.assertIsNone(fixture_http(raw, status=200)['body'])
        accepted = fixture_http(raw, status=200, max_response_bytes=1024**2)
        self.assertEqual(accepted['body']['status'], 'completed')
        self.assertEqual(normalize(accepted, public_request(), pricing=None, engineering=True)['status'], 'ok')
        limited = fixture_http(raw, status=200, max_response_bytes=65536)
        self.assertEqual(limited['http_diagnostic']['omission_reason'], 'response_body_limit')
        self.assertEqual(limited['http_diagnostic']['response_bytes_observed'], 65537)
        with self.assertRaises(ProtocolError) as error:
            normalize(limited, public_request(), pricing=None, engineering=True)
        self.assertEqual(error.exception.diagnostic['code'], 'response_body_limit')
        with self.assertRaises(ValueError):
            fixture_http(raw, status=200, max_response_bytes=1024**2 + 1)

    def test_actual_HTTP_408_preserves_bounded_error_and_timing_with_missing_ID(self):
        reply = fixture_http(b'{"error":{"code":"upstream_timeout","type":"gateway_error","message":"PUBLIC upstream timed out"}}')
        diag = reply['http_diagnostic']
        self.assertEqual((reply['http_status'], diag['transport_kind'], diag['send_state']),
            (408, 'http_response', 'response_received'))
        self.assertEqual(diag['error']['code'], 'upstream_timeout')
        self.assertEqual(diag['error']['type'], 'gateway_error')
        self.assertEqual(diag['error']['message'], 'PUBLIC upstream timed out')
        self.assertIsNone(reply['request_id'])
        self.assertGreater(diag['started_at_utc_ms'], 0)
        self.assertGreaterEqual(diag['ended_at_utc_ms'], diag['started_at_utc_ms'])
        self.assertGreaterEqual(diag['elapsed_ms'], 0)

    def test_non_JSON_missing_truncated_and_filtered_bodies_are_explicit(self):
        for raw in (b'PUBLIC gateway timeout', b'', b'x' * 70000,
                ('Authorization: Bearer ' + KEY).encode(),
                json.dumps({'error': {'code': KEY[:8], 'type': KEY[8:], 'message': 'PUBLIC'}}).encode()):
            error = fixture_http(raw)['http_diagnostic']['error']
            self.assertNotIn(KEY, json.dumps(error))
            self.assertLess(len(json.dumps(error).encode()), 4096)
            if len(raw) > 65536:
                self.assertTrue(error['body_truncated'])
                self.assertFalse(error['body_length_exact'])
            elif raw == b'PUBLIC gateway timeout':
                self.assertEqual(error['snippet'], 'PUBLIC gateway timeout')
                self.assertEqual(error['body_format'], 'non_json_text')
            elif raw:
                self.assertIsNotNone(error['omission_reason'])

    def test_local_timeout_connection_error_and_worker_unknown_are_distinct(self):
        for failure, kind in ((TimeoutError(KEY), 'local_timeout'), (ConnectionError(KEY), 'connection_error')):
            reply = fixture_http(b'', fail=failure)
            self.assertIsNone(reply['http_status'])
            self.assertEqual(reply['http_diagnostic']['transport_kind'], kind)
            self.assertEqual(reply['http_diagnostic']['send_state'], 'unknown')
            self.assertNotIn(KEY, json.dumps(reply))
        for timeout in (True, False):
            def process(args, **kwargs):
                if timeout:
                    raise subprocess.TimeoutExpired(args, 120, output=KEY.encode())
                return subprocess.CompletedProcess(args, 7, stdout=KEY.encode())
            reply = send_response('https://4router.net/v1/responses', {}, KEY, 120, process_run=process)
            self.assertEqual(reply['http_diagnostic']['transport_kind'], 'local_timeout' if timeout else 'unknown_send')
            self.assertNotIn(KEY, json.dumps(reply))

    def test_HTTP_failure_reaches_production_adapter_and_stops_without_retry(self):
        from tests.test_fourrouter_protocol_diagnostics import public_invocation
        for raw in (b'{"error":{"code":"timeout","type":"gateway","message":"PUBLIC timeout"}}', b'PUBLIC gateway'):
            reply = fixture_http(raw, headers={'x-request-id': 'PUBLIC-http-id'})
            with public_invocation(reply) as (model, request, budget, calls):
                result = model.invoke(request)
                self.assertEqual(result['status'], 'http_status_not_200')
                self.assertEqual(result['raw_response']['http_diagnostic']['transport_kind'], 'http_response')
                self.assertEqual(result['provider_request_id'], 'PUBLIC-http-id')
                self.assertFalse(result['error']['retryable'])
                self.assertIsNone(result['usage']['input_tokens'])
                self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
