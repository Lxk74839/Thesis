"""Public root ledger behavior; synthetic limits are not execution budgets."""
from pathlib import Path
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
RESOURCES = ('model_calls', 'input_tokens', 'output_tokens', 'logical_tools', 'physical_tools',
             'candidates', 'retries', 'elapsed_ms', 'cost_microusd')


class RootBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/recommendation-runtime')
        self.addCleanup(self.temp.cleanup)
        self.now = [0]
        self.binding = {'run_id': 'PUBLIC-RUN', 'root_task_id': 'PUBLIC-ROOT', 'snapshot_id': 'PUBLIC-SNAPSHOT',
                        'principal_id': 'SIM-VERIFIER', 'verify_at_ms': 1000, 'method': 'M',
                        'execution_kind': 'scripted_public'}

    def budget(self, **changes):
        from evidence_access import RootBudget
        limits = dict.fromkeys(RESOURCES, 100)
        limits.update(model_calls=2, elapsed_ms=600000, retries=2)
        limits.update(changes)
        reserve = dict.fromkeys(RESOURCES, 0)
        reserve.update(model_calls=1, logical_tools=1, elapsed_ms=1000)
        return RootBudget(self.binding, limits, reserve, clock=lambda: self.now[0],
                          journal_path=Path(self.temp.name) / 'budget.jsonl')

    def test_final_capacity_is_protected_and_consumed_once_across_roles(self):
        ledger = self.budget()
        first = ledger.reserve('model:需求解析', {'model_calls': 1}, phase='work', retry_of=None)
        ledger.settle(first['reservation_id'], {'usage': {'model_calls': 1}, 'status': 'ok'})
        denied = ledger.reserve('model:生命周期追溯', {'model_calls': 1}, phase='work', retry_of=None)
        self.assertEqual(denied['status'], 'budget_exhausted')

        final = ledger.reserve('model:推荐管理', {'model_calls': 1}, phase='final', retry_of=None)
        ledger.settle(final['reservation_id'], {'usage': {'model_calls': 1}, 'status': 'ok'})
        self.assertEqual(ledger.audit_view()['usage']['model_calls'], 2)
        with self.assertRaises(ValueError):
            ledger.settle(final['reservation_id'], {'usage': {'model_calls': 1}, 'status': 'ok'})
        self.assertEqual(ledger.audit_view()['usage']['model_calls'], 2)

    def test_unknown_tokens_keep_their_hold_and_block_new_work(self):
        ledger = self.budget()
        reservation = ledger.reserve('model:追溯', {'model_calls': 1, 'input_tokens': 80, 'output_tokens': 10},
                                     phase='work', retry_of=None)
        result = ledger.settle(reservation['reservation_id'], {'status': 'timeout',
            'usage': {'model_calls': 1, 'input_tokens': None, 'output_tokens': None}})
        self.assertEqual(result['status'], 'unresolved')
        view = ledger.audit_view()
        self.assertEqual((view['usage']['model_calls'], view['held']['input_tokens'], view['held']['output_tokens']), (1, 80, 10))
        self.assertFalse(view['usage_exact'])
        denied = ledger.reserve('model:换会话', {'model_calls': 1}, phase='final', retry_of=None)
        self.assertEqual(denied['status'], 'usage_unresolved')

    def test_evidence_and_model_attempts_share_one_injected_root(self):
        from tests.evidence_fixtures import EvidenceFixture, acquire_all
        from evidence_access import EvidenceSession, LocalEvidenceSource
        fixture = EvidenceFixture(Path(self.temp.name) / 'facts').normal()
        self.binding['snapshot_id'] = fixture.snapshot['snapshot_id']
        ledger = self.budget(logical_tools=512)
        request = ledger.reserve('model:需求解析', {'model_calls': 1}, phase='work', retry_of=None)
        ledger.settle(request['reservation_id'], {'status': 'ok', 'usage': {'model_calls': 1}})
        session = EvidenceSession(fixture.binding(), LocalEvidenceSource(fixture.snapshot_ref),
            limits=ledger.limits, final_reserve=ledger.final_reserve, root_budget=ledger)
        acquire_all(session)
        self.assertTrue(session.assess_current()['assessment']['eligible'])
        self.assertEqual(ledger.audit_view()['usage']['model_calls'], 1)
        self.assertEqual(ledger.audit_view()['usage']['logical_tools'], 24)
        self.assertEqual(session.audit_view()['usage'], ledger.audit_view()['usage'])

    def test_tool_and_model_retries_use_the_same_two_attempt_allowance(self):
        ledger = self.budget()
        attempt = ledger.reserve('tool:read', {'physical_tools': 1}, phase='work', retry_of=None)
        ledger.settle(attempt['reservation_id'], {'status': 'io_error', 'usage': {'physical_tools': 1}})
        for name in ('model:format', 'tool:read'):
            attempt = ledger.reserve(name, {'physical_tools': 1}, phase='work', retry_of=attempt['reservation_id'])
            ledger.settle(attempt['reservation_id'], {'status': 'io_error', 'usage': {'physical_tools': 1}})
        self.assertEqual(ledger.audit_view()['usage']['retries'], 2)
        denied = ledger.reserve('model:new-session', {}, phase='work', retry_of=attempt['reservation_id'])
        self.assertEqual(denied['status'], 'budget_exhausted')

    def test_a_late_request_stops_the_root_even_before_the_root_deadline(self):
        ledger = self.budget()
        reservation = ledger.reserve('read', {'physical_tools': 1, 'elapsed_ms': 10}, phase='work', retry_of=None)
        self.now[0] = 11
        ledger.settle(reservation['reservation_id'], {'status': 'deadline_exceeded', 'late': True,
                                                    'usage': {'physical_tools': 1}})
        self.assertEqual(ledger.reserve('model:later', {}, phase='work', retry_of=None)['status'], 'deadline_exceeded')

    def test_actual_usage_over_a_reservation_is_preserved_and_stops_new_work(self):
        ledger = self.budget()
        attempt = ledger.reserve('model:需求解析', {'input_tokens': 10}, phase='work', retry_of=None)
        ledger.settle(attempt['reservation_id'], {'status': 'ok', 'usage': {'input_tokens': 11}})
        self.assertEqual(ledger.audit_view()['usage']['input_tokens'], 11)
        self.assertEqual(ledger.reserve('model:推荐管理', {}, phase='final', retry_of=None)['status'], 'budget_exhausted')

    def test_zero_hold_is_still_pending_and_a_root_journal_cannot_be_reopened(self):
        ledger = self.budget()
        attempt = ledger.reserve('intent', {}, phase='work', retry_of=None)
        self.assertFalse(ledger.audit_view()['usage_exact'])
        with self.assertRaises(FileExistsError):
            self.budget()
        ledger.settle(attempt['reservation_id'], {'status': 'ok', 'usage': {}})
        self.assertTrue(ledger.audit_view()['usage_exact'])

    def test_only_a_bound_authoritative_receipt_can_resolve_unknown_usage_once(self):
        ledger = self.budget()
        attempt = ledger.reserve('model', {'model_calls': 1, 'input_tokens': 80}, phase='work', retry_of=None)
        identity = attempt['reservation_id']
        ledger.settle(identity, {'status': 'timeout', 'usage': {'model_calls': 1, 'input_tokens': None}})
        with self.assertRaises(ValueError):
            ledger.settle(identity, {'status': 'timeout', 'usage': {'model_calls': 1, 'input_tokens': 60}})
        ledger.settle(identity, {'status': 'timeout', 'authoritative_receipt': identity,
                                 'usage': {'model_calls': 1, 'input_tokens': 60}})
        view = ledger.audit_view()
        self.assertEqual((view['usage']['model_calls'], view['usage']['input_tokens']), (1, 60))
        self.assertTrue(view['usage_exact'])
        with self.assertRaises(ValueError):
            ledger.settle(identity, {'status': 'timeout', 'authoritative_receipt': identity,
                                     'usage': {'model_calls': 1, 'input_tokens': 60}})
