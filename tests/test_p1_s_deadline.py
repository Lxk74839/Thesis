"""Real frozen input + recorded request, fixture transport only. Never a live S result."""
import copy
import json
from pathlib import Path
import os
import sys
import tempfile
import time
import unittest

import p1_runtime as p1
from recommendation_runner import RunStop

PACKAGE = p1.PROJECT / '.scratch/ticket14-s-deadline-20261020'
OLD = p1.PROJECT / 'data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-ENGINEERING-ONCE-20261020/audit.json'


class AdvancingClock:
    def __init__(self):
        self.start = time.monotonic()
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return 137000.25 + (time.monotonic() - self.start) * 1000 + self.calls * 5


def setUpModule():
    def offline(event, args):
        if event.startswith(('socket.', 'http.client.', 'subprocess.')):
            raise OSError('deadline_test_network_forbidden')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            parts = {p.lower() for p in Path(os.fsdecode(args[0])).parts}
            if parts & {'.secrets', 'private', 'evaluation', 'gold'}:
                raise OSError('deadline_test_credentials_labels_forbidden')
    sys.addaudithook(offline)


class SDeadline(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads(OLD.read_bytes())
        self.original = self.audit['messages'][0]['request']
        self.cfg = json.loads((p1.PROJECT / '.scratch/ticket14-s-engineering-20261020/s.config.json').read_bytes())
        parent = p1.PROJECT / '.tmp/recommendation-runtime/s-deadline-fixtures'
        parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='fixture-', dir=parent)
        self.addCleanup(temp.cleanup)
        self.guard = p1.P1StorageGuard(temp.name, 64 * 1024**2)
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)
        assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={'run_id': self.audit['binding']['run_id']})
        self.run = p1.build_runtime(assembly, self.cfg, 'S', counter=None, output_root=Path(temp.name))
        self.clock = AdvancingClock()
        self.run.budget.clock = self.clock
        self.run.budget.started = self.clock()
        self.calls = []
        def sentinel(text, *, deadline_ms):
            from fourrouter_probe import _request_bytes
            body_bytes = len(_request_bytes(json.loads(text), 2 * 1024**2))
            self.calls.append({'deadline_ms': deadline_ms, 'now_ms': self.clock(), 'body_bytes': body_bytes})
            raise OSError('fixture_transport_sentinel')
        self.run.model.transport = sentinel

    def reserved_request(self):
        from p1_engineering import reservation_deadline
        request = copy.deepcopy(self.original)
        for key in ('prepared_id', 'count_receipt_id'):
            request.pop(key)
        prepared = self.run.model.prepare(request)
        self.assertEqual(prepared['status'], 'prepared')
        intent = {'kind': 'model', 'request_id': request['request_id'], 'prepared_id': prepared['prepared_id'],
            'wire_sha256': prepared['wire_sha256'], 'count_receipt_id': None}
        reserved = self.run.budget.reserve(intent,
            {'model_calls': 1, 'request_output_tokens': request['max_output_tokens'], 'elapsed_ms': 30000},
            phase='work', retry_of=None)
        self.assertEqual(reserved['status'], 'reserved')
        request.update(prepared_id=prepared['prepared_id'], count_receipt_id=None,
            reservation_id=reserved['reservation_id'], deadline_ms=int(reservation_deadline(self.run.budget, reserved['reservation_id'])))
        return request

    def test_expired_deadline_still_rejected(self):
        request = self.reserved_request()
        request['deadline_ms'] = int(self.clock()) - 1
        response = self.run.model.invoke(request)
        self.assertEqual(response['status'], 'not_started')
        self.assertFalse(response['preflight_diagnostic']['not_expired'])
        self.assertEqual(len(self.calls), 0)

    def test_beyond_frozen_window_still_rejected(self):
        request = self.reserved_request()
        request['deadline_ms'] += 2
        response = self.run.model.invoke(request)
        self.assertEqual(response['status'], 'not_started')
        self.assertFalse(response['preflight_diagnostic']['within_reserved_window'])
        self.assertEqual(len(self.calls), 0)

    def test_mismatched_reservation_still_rejected(self):
        request = self.reserved_request()
        self.run.budget.reservations[request['reservation_id']]['operation']['request_id'] = 'PUBLIC-wrong-owner'
        self.assertEqual(self.run.model.invoke(request)['status'], 'not_started')
        self.assertEqual(len(self.calls), 0)

    def test_duplicate_consumption_still_rejected(self):
        request = self.reserved_request()
        self.run.model.invoke(request)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.run.model.invoke(request)['status'], 'not_started')
        self.assertEqual(len(self.calls), 1)

    def test_old_and_new_authorizations_cannot_be_crossed_at_adapter(self):
        from p1_engineering import RETRY_AUTHORIZATION
        request = self.reserved_request()
        self.run.model.binding['engineering_authorization'] = RETRY_AUTHORIZATION
        self.assertEqual(self.run.model.invoke(request)['status'], 'not_started')
        self.assertEqual(len(self.calls), 0)

    def test_new_S_grant_exactly_binds_task_and_cannot_borrow_old_grant(self):
        from p1_engineering import RETRY_AUTHORIZATION, AUTHORIZATION
        cfg_path = PACKAGE / 's.config.json'
        ready = p1.prepare_p1(cfg_path, 'S', storage_guard=p1.P1StorageGuard(p1.OUTPUT, 64 * 1024**2))
        self.assertEqual(ready['terminal'], 'ready', ready['missing'])
        cfg = json.loads(cfg_path.read_bytes())
        assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['S'], execution_record={'run_id': 'P1-D1-V00-S-' + RETRY_AUTHORIZATION})
        run = p1.build_runtime(assembly, cfg, 'S', counter=None, output_root=self.run.output_root / 'new-grant')
        run._preflight()
        self.assertEqual(len(run.binding['C']), 1493)
        altered = copy.deepcopy(run.binding)
        altered['authorization_id'] = AUTHORIZATION
        self.assertEqual(p1.frozen_snapshot_error(altered, assembly['snapshot_ref']), 'frozen_task_identity')
        calls = []
        def sentinel(text, *, deadline_ms):
            from fourrouter_probe import _request_bytes
            calls.append({'deadline_ms': deadline_ms, 'now_ms': run.budget.clock(),
                'body_bytes': len(_request_bytes(json.loads(text), 2 * 1024**2))})
            raise OSError('fixture_transport_sentinel')
        run.model.transport = sentinel
        with self.assertRaises(RunStop):
            req = self.original
            run._invoke(req['role'], req['output_kind'], copy.deepcopy(req['messages']), copy.deepcopy(req['tools']))
        self.assertEqual(len(calls), 1)
        self.assertGreater(calls[0]['now_ms'], 0)
        self.assertLessEqual(calls[0]['deadline_ms'] - calls[0]['now_ms'], 30000)
        self.assertEqual(self.guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})

    def test_recorded_1493_request_reaches_transport_under_advancing_clock(self):
        self.run._preflight()
        self.assertEqual(len(self.run.binding['C']), 1493)
        req = self.original
        with self.assertRaises(RunStop):
            self.run._invoke(req['role'], req['output_kind'], copy.deepcopy(req['messages']), copy.deepcopy(req['tools']))
        message = self.run.state['messages'][0]
        request = message['request']
        entry = self.run.budget.reservations[request['reservation_id']]
        receipt = next(r for r in self.run.budget.receipts if r.get('reservation_id') == request['reservation_id'] and 'phase' in r)
        reserved_end = self.run.budget.started + receipt['usage_before']['elapsed_ms'] + entry['held']['elapsed_ms']
        diagnostic = {'provenance': 'fixture', 'candidate_count': 1493,
            'request_id': request['request_id'], 'reservation_id': request['reservation_id'],
            'deadline_ms': request['deadline_ms'], 'reserved_end_ms': reserved_end,
            'within_reserved_window': request['deadline_ms'] <= reserved_end,
            'transport_sentinel_calls': len(self.calls), 'clock_calls': self.clock.calls,
            'native_status': message['response']['status'], 'missing': message['response'].get('missing'),
            'actual_POST_body_bytes': self.calls[0]['body_bytes'] if self.calls else None,
            'within_HTTP_window': request['deadline_ms'] - self.clock() <= 30000,
            'real_HTTP_requests': 0, 'actual_credentials_read': 0, 'actual_claim_created': False}
        # Outside the active storage guard, the test runner archives only this safe diagnostic.
        self.diagnostic = diagnostic
        self.guard.__exit__(None, None, None)
        (PACKAGE / 'fixture-control-diagnostic.json').write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
        self.guard.active = False
        self.assertEqual(len(self.calls), 1, {k: diagnostic[k] for k in ('native_status', 'missing', 'within_reserved_window')})
        self.assertTrue(diagnostic['within_reserved_window'])


if __name__ == '__main__':
    unittest.main()
