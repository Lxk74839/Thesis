import shutil
import tempfile
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from tests.evidence_fixtures import EvidenceFixture, wire, sha


class EvidenceAccessTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix='evidence-test-', dir='.tmp'))
        self.addCleanup(shutil.rmtree, self.directory)
        self.fixture = EvidenceFixture(self.directory)

    def test_list_acquires_real_registrations_and_initial_dependencies(self):
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(page['status'], 'ok')
        self.assertEqual([r['target_id'] for r in page['entries']], ['BATCH-A'])
        self.assertTrue(page['enumeration_complete'])
        acquired = session.audit_view()['acquired']
        self.assertIn('raw_utf8', acquired['context']['policy'])
        self.assertIn('raw_utf8', acquired['context']['snapshot'])
        self.assertEqual(len(acquired['candidates']['PUBLIC-A']['registrations']), 1)
        self.assertNotIn('sequence', page['entries'][0])

    def test_read_returns_exact_scoped_bytes_and_keeps_acquired_source(self):
        session = self.fixture.session()
        entry = session.dispatch('list_evidence', {'cursor': None})['entries'][0]
        result = session.dispatch('read_evidence', {'evidence_refs': [entry['evidence_ref']]})
        original = result['items'][0]
        raw = wire(self.fixture.rows['batches.jsonl'][0])
        self.assertEqual(original['raw_utf8'].encode(), raw)
        self.assertEqual(original['sha256'], sha(raw))
        audit = session.audit_view()
        saved = audit['acquired']['candidates']['PUBLIC-A']['originals'][entry['evidence_ref']]
        self.assertEqual(saved['source']['line'], 1)
        audit['acquired']['context'].clear()
        self.assertIn('snapshot', session.audit_view()['acquired']['context'])

    def test_thirty_three_records_close_only_on_the_bound_last_page(self):
        for number in range(32):
            self.fixture.add('events.jsonl', {'event_id': 'EVENT-' + str(number), 'version': 1,
                'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'actor_id': 'SIM-PRODUCER'})
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        first = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(len(first['entries']), 32)
        self.assertFalse(first['enumeration_complete'])
        second = session.dispatch('list_evidence', {'cursor': first['next_cursor']})
        self.assertEqual(len(second['entries']), 1)
        self.assertTrue(second['enumeration_complete'])
        self.assertEqual(len(session.audit_view()['acquired']['candidates']['PUBLIC-A']['registrations']), 33)
        other = self.fixture.session()
        self.assertEqual(other.dispatch('list_evidence', {'cursor': first['next_cursor']})['status'], 'access_denied')

    def test_initial_dependencies_and_each_returned_fact_have_public_receipts(self):
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(page['receipt']['usage_delta']['logical_tools'], 4)
        self.assertEqual(page['receipt']['usage_delta']['physical_tools'], 1)
        ref = page['entries'][0]['evidence_ref']
        read = session.dispatch('read_evidence', {'evidence_refs': [ref]})
        self.assertEqual(read['receipt']['usage_delta']['logical_tools'], 1)
        self.assertEqual(read['receipt']['root_usage_after']['logical_tools'], 5)
        audit = session.audit_view()
        self.assertEqual(len(audit['receipts']), 2)
        saved = audit['acquired']['candidates']['PUBLIC-A']['originals'][ref]
        self.assertEqual(saved['receipt_id'], read['receipt']['receipt_id'])
        self.assertGreater(read['receipt']['response_bytes'], 0)

    def test_read_denial_is_enforced_before_any_original_request(self):
        self.fixture.policy['read_denials'] = [{'principal_id': 'SIM-VERIFIER', 'target_kind': 'batch',
                                                'target_id': 'BATCH-A', 'version': 1}]
        self.fixture.seal()
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        before = session.audit_view()['setup'].copy()
        result = session.dispatch('read_evidence', {'evidence_refs': [page['entries'][0]['evidence_ref']]})
        self.assertEqual(result['items'][0]['status'], 'access_denied')
        self.assertEqual(result['receipt']['usage_delta']['physical_tools'], 0)
        self.assertEqual(before, session.audit_view()['setup'])
        for payload in ({'cursor': None, 'principal_id': 'evaluator'}, {'cursor': None, 'root_task_id': 'OTHER'},
                        {'cursor': None, 'snapshot_id': 'OTHER'}, {'cursor': None, 'path': 'private/gold.json'}):
            self.assertEqual(session.dispatch('list_evidence', payload)['status'], 'access_denied')

    def test_outer_component_damage_stops_source_without_inventing_candidate_state(self):
        session = self.fixture.session()
        (self.fixture.root / 'materials.jsonl').write_bytes(b'broken')
        result = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(result['status'], 'source_integrity_error')
        self.assertEqual(session.audit_view()['acquired']['candidates'], {})
        self.assertEqual(result['receipt']['usage_delta']['physical_tools'], 1)
        second = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(second['status'], 'source_integrity_error')
        self.assertEqual(second['receipt']['usage_delta']['physical_tools'], 0)

    def test_metering_example_counts_missing_items_and_repeated_cached_facts(self):
        for number in range(2):
            self.fixture.add('events.jsonl', {'event_id': 'EVENT-' + str(number), 'version': 1,
                'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'actor_id': 'SIM-PRODUCER'})
        self.fixture.register_all()
        self.fixture.rows['events.jsonl'].pop()
        self.fixture.seal()
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(page['receipt']['usage_delta']['logical_tools'], 6)
        refs = [row['evidence_ref'] for row in page['entries']]
        first = session.dispatch('read_evidence', {'evidence_refs': refs})
        self.assertEqual([v['status'] for v in first['items']], ['ok', 'ok', 'unavailable'])
        self.assertEqual(first['receipt']['usage_delta'], {'logical_tools': 3, 'physical_tools': 1})
        repeated = session.dispatch('read_evidence', {'evidence_refs': refs[:2]})
        self.assertEqual(repeated['receipt']['usage_delta'], {'logical_tools': 2, 'physical_tools': 0})
        self.assertTrue(all(v['cache_hit'] for v in repeated['items']))

    def test_six_roles_share_one_atomic_root_budget_and_final_reserve(self):
        limits = {'logical_tools': 37, 'physical_tools': 20, 'candidates': 1, 'retries': 2, 'elapsed_ms': 600000}
        session = self.fixture.session(limits=limits)
        page = session.dispatch('list_evidence', {'cursor': None})
        arguments = {'evidence_refs': [page['entries'][0]['evidence_ref']]}
        for _ in range(30):
            self.assertEqual(session.dispatch('read_evidence', arguments)['status'], 'ok')
        roles = ('需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验')
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda role: session.dispatch('read_evidence', arguments, actor_role=role), roles))
        self.assertEqual(sum(row['status'] == 'ok' for row in results), 1)
        self.assertEqual(sum(row['status'] == 'budget_exhausted' for row in results), 5)
        self.assertEqual(session.audit_view()['usage']['logical_tools'], 35)
        self.assertEqual(session.audit_view()['usage']['candidates'], 1)
        self.assertTrue(all(row['receipt']['usage_delta']['physical_tools'] == 0 for row in results))

    def test_failed_adapter_request_and_host_retry_both_remain_in_root_receipts(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class FlakySource(LocalEvidenceSource):
            def read(self, registrations):
                if not getattr(self, 'failed_once', False):
                    self.failed_once = True
                    raise OSError('public transient fault')
                return super().read(registrations)
        normal = self.fixture.session()
        session = EvidenceSession(self.fixture.binding(), FlakySource(self.fixture.snapshot_ref),
                                  limits=normal.limits, final_reserve=normal.final_reserve)
        page = session.dispatch('list_evidence', {'cursor': None})
        failed = session.dispatch('read_evidence', {'evidence_refs': [page['entries'][0]['evidence_ref']]})
        self.assertEqual(failed['status'], 'io_error')
        self.assertEqual(failed['receipt']['usage_delta'], {'logical_tools': 1, 'physical_tools': 1})
        success = session.retry(failed['receipt']['request_id'])
        self.assertEqual(success['items'][0]['status'], 'ok')
        self.assertEqual(success['receipt']['retry_of'], failed['receipt']['request_id'])
        self.assertEqual(success['receipt']['root_usage_after']['retries'], 1)
        self.assertEqual(len(session.audit_view()['receipts']), 3)

    def test_late_real_bytes_are_retained_but_cannot_start_more_root_work(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        now = [0]
        class LateSource(LocalEvidenceSource):
            def read(self, registrations):
                values = super().read(registrations)
                now[0] = 600001
                return values
        normal = self.fixture.session()
        session = EvidenceSession(self.fixture.binding(), LateSource(self.fixture.snapshot_ref),
            limits=normal.limits, final_reserve=normal.final_reserve, clock=lambda: now[0])
        page = session.dispatch('list_evidence', {'cursor': None})
        ref = page['entries'][0]['evidence_ref']
        late = session.dispatch('read_evidence', {'evidence_refs': [ref]})
        self.assertEqual(late['status'], 'deadline_exceeded')
        self.assertTrue(late['receipt']['late'])
        self.assertIn(ref, session.audit_view()['acquired']['candidates']['PUBLIC-A']['originals'])
        again = session.dispatch('read_evidence', {'evidence_refs': [ref]})
        self.assertEqual(again['status'], 'deadline_exceeded')
        self.assertEqual(again['receipt']['usage_delta']['physical_tools'], 0)

    def test_candidate_paging_reuses_joint_projection_and_charges_only_returned_rows(self):
        from joint_access import JointSession
        parents = ['PUBLIC-A'] + ['PUBLIC-' + str(n) for n in range(32)]
        joint = JointSession({'root_task_id': 'PUBLIC-ROOT'},
            {'C': parents, 'b': [.5] * 33, 'batches': ['BATCH-' + p for p in parents],
             'background_statistics': [{}] * 33},
            [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in parents],
            {'arm': 'necessary', 'request': {'design_text': 'PUBLIC', 'necessary_clauses': []}}, 'PUBLIC-HANDLE')
        joint.candidates['batches'][0] = 'BATCH-A'
        session = self.fixture.session(joint=joint)
        first = session.dispatch('candidate_page', {'order': 'parent', 'cursor': None})
        self.assertEqual(first['candidates'], joint.dispatch('candidate_page', {'order': 'parent', 'cursor': None})['candidates'])
        self.assertEqual(first['receipt']['usage_delta'], {'logical_tools': 32, 'physical_tools': 0})
        second = session.dispatch('candidate_page', {'order': 'parent', 'cursor': first['next_cursor']})
        self.assertEqual(len(second['candidates']), 1)
        self.assertEqual(session.audit_view()['usage']['candidates'], 0)
        self.assertEqual(joint.request['tools'], [])


    def test_refs_are_bound_to_root_even_when_test_randomness_is_held_fixed(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        with patch('secrets.token_bytes', return_value=b'p' * 32):
            first = self.fixture.session()
            first_page = first.dispatch('list_evidence', {'cursor': None})
            other = EvidenceSession(self.fixture.binding(root_task_id='OTHER-ROOT'),
                LocalEvidenceSource(self.fixture.snapshot_ref), limits=first.limits, final_reserve=first.final_reserve)
            other.dispatch('list_evidence', {'cursor': None})
            result = other.dispatch('read_evidence', {'evidence_refs': [first_page['entries'][0]['evidence_ref']]})
        self.assertEqual(result['status'], 'access_denied')
        self.assertEqual(result['receipt']['usage_delta']['physical_tools'], 0)


    def test_receipt_items_resolve_every_returned_fact_to_host_only_provenance(self):
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(len(page['receipt']['items']), 4)
        read = session.dispatch('read_evidence', {'evidence_refs': [page['entries'][0]['evidence_ref']]})
        self.assertTrue(read['receipt']['items'][0]['adapter_request_id'])
        audit = session.audit_view()
        for receipt in (page['receipt'], read['receipt']):
            for item in receipt['items']:
                self.assertIn(item['source_ref'], audit['provenance'])
                self.assertNotIn('component_path', item)


    def test_material_kind_permission_denies_the_original_without_target_read(self):
        self.fixture.normal()
        self.fixture.policy['read_scope']['material_kinds'].remove('inspection_report')
        self.fixture.seal()
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        report = next(r for r in page['entries'] if r['target_id'] == 'D-inspection_report')
        result = session.dispatch('read_evidence', {'evidence_refs': [report['evidence_ref']]})
        self.assertEqual(result['items'][0]['status'], 'access_denied')
        self.assertEqual(result['receipt']['usage_delta']['physical_tools'], 0)


    def test_unknown_usage_keeps_reservation_and_blocks_free_retry(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class UnknownSource(LocalEvidenceSource):
            def read(self, registrations):
                return [{'status': 'io_error', 'usage_known': False} for _ in registrations]
        normal = self.fixture.session()
        session = EvidenceSession(self.fixture.binding(), UnknownSource(self.fixture.snapshot_ref),
                                  limits=normal.limits, final_reserve=normal.final_reserve)
        page = session.dispatch('list_evidence', {'cursor': None})
        result = session.dispatch('read_evidence', {'evidence_refs': [page['entries'][0]['evidence_ref']]})
        self.assertTrue(result['receipt']['reservation']['unresolved'])
        self.assertIsNone(result['receipt']['reservation']['settled']['physical_tools'])
        after = session.audit_view()['usage'].copy()
        retry = session.retry(result['receipt']['request_id'])
        self.assertEqual(retry['receipt']['usage_delta']['physical_tools'], 0)
        self.assertEqual(session.audit_view()['usage']['physical_tools'], after['physical_tools'])
        self.assertTrue(session.audit_view()['unsettled_reservations'])


    def test_scenario_change_action_component_is_read_via_the_same_refs(self):
        self.fixture.normal().revise()
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(page['status'], 'ok')
        action = next(row for row in page['entries'] if row['target_kind'] == 'change_action')
        result = session.dispatch('read_evidence', {'evidence_refs': [action['evidence_ref']]})
        self.assertEqual(result['items'][0]['status'], 'ok')
        origin = session.audit_view()['provenance'][result['items'][0]['source_ref']]
        self.assertTrue(origin['component_path'].endswith('change-actions.jsonl'))


    def test_tool_schema_exports_only_closed_list_and_read_inputs(self):
        session = self.fixture.session()
        schemas = session.tool_schemas()
        self.assertEqual([row['name'] for row in schemas], ['list_evidence', 'read_evidence'])
        for row in schemas:
            self.assertFalse(row['input_schema']['additionalProperties'])
            self.assertFalse({'root_task_id', 'principal_id', 'snapshot_id', 'path', 'role'} & set(row['input_schema']['properties']))
        self.assertEqual(schemas[1]['input_schema']['properties']['evidence_refs']['maxItems'], 32)

    def test_mismatched_source_binding_stops_before_candidate_facts_are_scanned(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        normal = self.fixture.session()
        for change in ({'snapshot_id': 'OTHER'}, {'verify_at_ms': 1001}, {'principal_id': 'OTHER'}):
            with self.subTest(change=change):
                session = EvidenceSession(self.fixture.binding(**change), LocalEvidenceSource(self.fixture.snapshot_ref),
                    limits=normal.limits, final_reserve=normal.final_reserve)
                result = session.dispatch('list_evidence', {'cursor': None})
                self.assertEqual(result['status'], 'source_integrity_error')
                audit = session.audit_view()
                self.assertEqual(audit['acquired']['candidates'], {})
                self.assertEqual(audit['acquired']['context'], {})
                self.assertLessEqual(audit['setup']['file_reads'], 2)
                self.assertEqual(session.dispatch('list_evidence', {'cursor': None})['receipt']['usage_delta']['physical_tools'], 0)


    def test_retry_cap_and_failed_request_refs_are_root_receipted(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class FailedSource(LocalEvidenceSource):
            def read(self, registrations):
                raise OSError('public repeatable failure')
        normal = self.fixture.session()
        delays = []
        session = EvidenceSession(self.fixture.binding(), FailedSource(self.fixture.snapshot_ref),
            limits=normal.limits, final_reserve=normal.final_reserve, clock=lambda: 0, sleeper=delays.append)
        page = session.dispatch('list_evidence', {'cursor': None})
        ref = page['entries'][0]['evidence_ref']
        failed = session.dispatch('read_evidence', {'evidence_refs': [ref]})
        self.assertEqual(failed['receipt']['requested_refs'], [ref])
        session.retry(failed['receipt']['request_id'])
        session.retry(failed['receipt']['request_id'])
        exhausted = session.retry(failed['receipt']['request_id'])
        self.assertEqual(delays, [1, 2])
        self.assertEqual(exhausted['status'], 'budget_exhausted')
        self.assertEqual(session.audit_view()['usage']['retries'], 2)
        self.assertEqual(exhausted['receipt']['usage_delta']['physical_tools'], 0)

    def test_direct_redispatch_of_failed_refs_uses_the_same_root_retry_cap(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class FailedSource(LocalEvidenceSource):
            def read(self, registrations):
                raise OSError('public repeatable failure')
        self.fixture.normal()
        normal = self.fixture.session()
        delays = []
        session = EvidenceSession(self.fixture.binding(), FailedSource(self.fixture.snapshot_ref),
            limits=normal.limits, final_reserve=normal.final_reserve, clock=lambda: 0, sleeper=delays.append)
        page = session.dispatch('list_evidence', {'cursor': None})
        refs = [row['evidence_ref'] for row in page['entries'][:2]]
        first = session.dispatch('read_evidence', {'evidence_refs': refs})
        second = session.dispatch('read_evidence', {'evidence_refs': list(reversed(refs))})
        third = session.dispatch('read_evidence', {'evidence_refs': refs[:1]})
        exhausted = session.dispatch('read_evidence', {'evidence_refs': refs})
        self.assertEqual(second['receipt']['retry_of'], first['receipt']['request_id'])
        self.assertEqual(third['receipt']['retry_of'], second['receipt']['request_id'])
        self.assertEqual(delays, [1, 2])
        self.assertEqual(session.audit_view()['usage']['retries'], 2)
        self.assertEqual(exhausted['status'], 'budget_exhausted')
        self.assertEqual(exhausted['receipt']['usage_delta']['physical_tools'], 0)

    def test_operation_time_and_retry_backoff_are_reserved_before_io(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        limits = {'logical_tools': 4096, 'physical_tools': 512, 'candidates': 1, 'retries': 2, 'elapsed_ms': 60000}
        reserve = {'logical_tools': 2, 'physical_tools': 1, 'elapsed_ms': 1000}
        now = [0]
        session = EvidenceSession(self.fixture.binding(), LocalEvidenceSource(self.fixture.snapshot_ref),
            limits=limits, final_reserve=reserve, clock=lambda: now[0])
        now[0] = 59000
        denied = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(denied['status'], 'deadline_exceeded')
        self.assertEqual(denied['receipt']['usage_delta'], {'logical_tools': 0, 'physical_tools': 0})
        self.assertEqual(session.audit_view()['setup']['file_reads'], 0)
        class FailedSource(LocalEvidenceSource):
            def read(self, registrations):
                raise OSError('public transient fault')
        now[0] = 0
        delays = []
        retry_session = EvidenceSession(self.fixture.binding(), FailedSource(self.fixture.snapshot_ref),
            limits=limits, final_reserve=reserve, clock=lambda: now[0], sleeper=delays.append)
        page = retry_session.dispatch('list_evidence', {'cursor': None})
        failed = retry_session.dispatch('read_evidence', {'evidence_refs': [page['entries'][0]['evidence_ref']]})
        now[0] = 14000
        retry = retry_session.retry(failed['receipt']['request_id'])
        self.assertEqual(retry['status'], 'deadline_exceeded')
        self.assertEqual(delays, [])
        self.assertEqual(retry['receipt']['usage_delta']['physical_tools'], 0)
        self.assertEqual(page['receipt']['reservation']['held']['elapsed_ms'], 45000)
        self.assertEqual(page['receipt']['deadline_at_ms'], 45000)

    def test_partial_batch_retains_failure_but_does_not_charge_unexecuted_items(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class PartialSource(LocalEvidenceSource):
            def read(self, registrations):
                return [*super().read(registrations[:1]), {'status': 'io_error'}, {'status': 'not_attempted'}]
        self.fixture.normal()
        normal = self.fixture.session()
        session = EvidenceSession(self.fixture.binding(), PartialSource(self.fixture.snapshot_ref),
            limits=normal.limits, final_reserve=normal.final_reserve)
        page = session.dispatch('list_evidence', {'cursor': None})
        refs = [row['evidence_ref'] for row in page['entries'][:3]]
        result = session.dispatch('read_evidence', {'evidence_refs': refs})
        self.assertEqual([item['status'] for item in result['items']], ['ok', 'io_error', 'not_attempted'])
        self.assertEqual(result['receipt']['usage_delta'], {'logical_tools': 2, 'physical_tools': 1})
        self.assertEqual(result['receipt']['reservation']['settled']['logical_tools'], 2)
        self.assertEqual(result['receipt']['reservation']['released']['logical_tools'], 1)
        saved = session.audit_view()['acquired']['candidates']['PUBLIC-A']
        self.assertEqual(set(saved['originals']), {refs[0]})
        self.assertEqual(saved['attempts'][refs[2]]['status'], 'not_attempted')

    def test_rejected_batch_cannot_erase_failed_refs_or_reset_the_retry_cap(self):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        class FailedSource(LocalEvidenceSource):
            def read(self, registrations):
                raise OSError('public repeatable failure')
        self.fixture.normal()
        normal = self.fixture.session()
        delays = []
        session = EvidenceSession(self.fixture.binding(), FailedSource(self.fixture.snapshot_ref),
            limits=normal.limits, final_reserve=normal.final_reserve, clock=lambda: 0, sleeper=delays.append)
        page = session.dispatch('list_evidence', {'cursor': None})
        refs = [row['evidence_ref'] for row in page['entries'][:3]]
        session.dispatch('read_evidence', {'evidence_refs': refs})
        rejected = session.dispatch('read_evidence', {'evidence_refs': [refs[0], *refs]})
        self.assertEqual(rejected['status'], 'access_denied')
        self.assertEqual(rejected['receipt']['usage_delta']['physical_tools'], 0)
        attempts = [session.dispatch('read_evidence', {'evidence_refs': [ref]}) for ref in refs]
        self.assertEqual([row['status'] for row in attempts], ['io_error', 'budget_exhausted', 'budget_exhausted'])
        self.assertEqual(delays, [1, 2])
        self.assertEqual(session.audit_view()['usage']['retries'], 2)
        self.assertEqual(session.audit_view()['usage']['physical_tools'], 3)


if __name__ == '__main__':
    unittest.main()
