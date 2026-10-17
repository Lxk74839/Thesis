import shutil
import tempfile
from pathlib import Path
import unittest
import copy
from unittest.mock import patch

from tests.evidence_fixtures import EvidenceFixture, acquire_all


class EvidenceVerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix='evidence-verify-', dir='.tmp'))
        self.addCleanup(shutil.rmtree, self.directory)
        self.fixture = EvidenceFixture(self.directory)

    def test_no_attempted_evidence_stays_unassessed_without_any_io(self):
        from evidence_verification import assess_evidence
        session = self.fixture.session()
        before = session.audit_view()['setup']
        result = assess_evidence(self.fixture.binding(), session.audit_view()['acquired'])
        self.assertEqual(result['assessment_status'], 'unassessed')
        self.assertIsNone(result['evidence_state'])
        self.assertFalse(result['eligible'])
        self.assertFalse(result['advance_allowed'])
        self.assertEqual(session.audit_view()['setup'], before)

    def test_actual_empty_terminal_scope_is_pending_and_can_be_safely_rejected(self):
        self.fixture.registrations.clear()
        self.fixture.seal()
        session = self.fixture.session()
        self.assertEqual(session.assess_current()['assessment']['assessment_status'], 'unassessed')
        page = session.dispatch('list_evidence', {'cursor': None})
        self.assertEqual(page['entries'], [])
        self.assertTrue(page['enumeration_complete'])
        result = session.assess_current()['assessment']
        self.assertEqual(result['assessment_status'], 'assessed')
        self.assertEqual(result['evidence_state'], 'Pending')
        self.assertTrue(result['advance_allowed'])
        self.assertFalse(result['completion']['required_reads_complete'])
        self.assertTrue(result['completion']['attempts_settled'])
        observation = next(item for item in page['receipt']['items'] if item['kind'] == 'empty_registration_scope')
        origin = session.audit_view()['provenance'][observation['source_ref']]
        self.assertEqual(origin['scope_records'], 0)
        self.assertEqual(page['receipt']['usage_delta'], {'logical_tools': 4, 'physical_tools': 1})

    def test_unread_unrelated_harvest_material_cannot_block_r1_or_r5(self):
        self.fixture.normal()
        self.fixture.add('materials.jsonl', {'schema_version': 'sim-material-1.0.0', 'source': 'SIM',
            'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'version': 1, 'evidence_id': 'D-HARVEST',
            'kind': 'harvest_record', 'issuer_id': 'SIM-PRODUCER', 'event_id': 'E-harvest',
            'issued_at_ms': 22, 'temporal_mode': 'historical_fact', 'facts': {'origin_area_id': 'AREA-2'}})
        self.fixture.policy['issuers'][0]['material_kinds'].append('harvest_record')
        self.fixture.policy['read_scope']['material_kinds'].append('harvest_record')
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        page = session.dispatch('list_evidence', {'cursor': None})
        refs = [r['evidence_ref'] for r in page['entries'] if r['target_id'] != 'D-HARVEST']
        session.dispatch('read_evidence', {'evidence_refs': refs})
        result = session.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Supported')
        self.assertTrue(result['advance_allowed'])

    def test_conflicting_lineages_need_a_sample_inside_the_inspection_event(self):
        self.fixture.normal()
        report = next(r for r in self.fixture.rows['materials.jsonl'] if r['kind'] == 'inspection_report')
        opposite = copy.deepcopy(report)
        opposite['evidence_id'] = 'D-INDEPENDENT'
        opposite['facts']['conclusion'] = 'fail'
        self.fixture.add('materials.jsonl', opposite)
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        acquire_all(session)
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Conflict')
        sample = next(r for r in self.fixture.rows['materials.jsonl'] if r['kind'] == 'inspection_sample')
        sample['facts']['sampled_at_ms'] = 5
        self.fixture.register_all()
        self.fixture.seal()
        wrong_event = self.fixture.session()
        acquire_all(wrong_event)
        self.assertEqual(wrong_event.assess_current()['assessment']['evidence_state'], 'Pending')

    def test_complete_public_sample_report_and_retail_are_supported_from_actual_a(self):
        self.fixture.normal()
        session = self.fixture.session()
        acquire_all(session)
        before = session.audit_view()['usage']['logical_tools']
        result = session.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Supported')
        self.assertEqual([result['claims'][c]['evidence_state'] for c in ('c1', 'c2')], ['Supported', 'Supported'])
        self.assertTrue(result['eligible'])
        self.assertTrue(result['advance_allowed'])
        self.assertTrue(all(result['completion'].values()))
        self.assertEqual(session.audit_view()['usage']['logical_tools'], before + 1)
        self.assertTrue(all(r['receipt_id'] and r['pointer'] for r in result['accepted']))

    def test_confirmed_missing_original_is_pending_and_settled_not_refuted(self):
        self.fixture.normal()
        self.fixture.rows['materials.jsonl'] = [r for r in self.fixture.rows['materials.jsonl'] if r['kind'] != 'inspection_report']
        self.fixture.seal()
        session = self.fixture.session()
        acquire_all(session)
        result = session.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Pending')
        self.assertFalse(result['completion']['required_reads_complete'])
        self.assertTrue(result['completion']['attempts_settled'])
        self.assertTrue(result['advance_allowed'])
        self.assertIn('unavailable', [r['reason'] for r in result['rejected']])

    def test_identical_fail_bytes_refute_only_when_registration_digest_matches(self):
        self.fixture.normal()
        report = next(r for r in self.fixture.rows['materials.jsonl'] if r['kind'] == 'inspection_report')
        report['facts']['conclusion'] = 'fail'
        self.fixture.seal()
        mismatch = self.fixture.session()
        acquire_all(mismatch)
        rejected = mismatch.assess_current()['assessment']
        self.assertEqual(rejected['evidence_state'], 'Pending')
        self.assertIn('digest_mismatch', [r['reason'] for r in rejected['rejected']])
        self.fixture.register_all()
        self.fixture.seal()
        valid = self.fixture.session()
        acquire_all(valid)
        result = valid.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Refuted')
        self.assertEqual(result['claims']['c1']['r'], 1)
        self.assertFalse(result['eligible'])


    def test_legal_new_report_replaces_old_support_and_never_falls_back_when_missing(self):
        self.fixture.normal().revise('fail')
        session = self.fixture.session()
        acquire_all(session)
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Refuted')
        self.fixture.rows['materials.jsonl'] = [r for r in self.fixture.rows['materials.jsonl'] if r['version'] != 2]
        self.fixture.seal()
        missing_head = self.fixture.session()
        acquire_all(missing_head)
        result = missing_head.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Pending')
        self.assertFalse(result['eligible'])


    def test_snapshot_cutoff_excludes_future_version_and_action_from_tool_scope(self):
        self.fixture.normal().revise('fail')
        self.fixture.seal({'cutoff_sequence': 10})
        session = self.fixture.session()
        entries = acquire_all(session)
        self.assertEqual(len(entries), 10)
        self.assertFalse(any(r['target_kind'] == 'change_action' or r['version'] == 2 for r in entries))
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Supported')


    def test_only_a_typed_authorized_effective_revocation_can_remove_support(self):
        self.fixture.normal().revoke()
        valid = self.fixture.session()
        acquire_all(valid)
        self.assertEqual(valid.assess_current()['assessment']['evidence_state'], 'Pending')
        self.fixture.rows['actions.jsonl'][0]['target_version'] = True
        self.fixture.register_all()
        self.fixture.seal()
        malformed = self.fixture.session()
        acquire_all(malformed)
        self.assertEqual(malformed.assess_current()['assessment']['evidence_state'], 'Supported')
        self.fixture.rows['actions.jsonl'][0].update(target_version=1, effective_from_ms=1001)
        self.fixture.register_all()
        self.fixture.seal()
        future = self.fixture.session()
        acquire_all(future)
        self.assertEqual(future.assess_current()['assessment']['evidence_state'], 'Supported')


    def test_current_expiry_does_not_apply_a_ttl_to_historical_inspection(self):
        self.fixture.normal()
        retail = next(r for r in self.fixture.rows['materials.jsonl'] if r['kind'] == 'retail_status')
        retail['valid_to_ms'] = 1000
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        acquire_all(session)
        result = session.assess_current()['assessment']
        self.assertEqual(result['claims']['c1']['evidence_state'], 'Supported')
        self.assertEqual(result['claims']['c2']['evidence_state'], 'Pending')
        self.assertEqual(result['evidence_state'], 'Pending')


    def test_positive_first_page_cannot_hide_negative_last_page_or_unread_original(self):
        self.fixture.normal()
        for number in range(22):
            self.fixture.add('materials.jsonl', {'schema_version': 'sim-material-1.0.0', 'source': 'SIM',
                'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'version': 1,
                'evidence_id': 'D-H-' + str(number), 'kind': 'harvest_record', 'issuer_id': 'SIM-PRODUCER',
                'event_id': 'E-harvest', 'issued_at_ms': 22, 'temporal_mode': 'historical_fact', 'facts': {'origin_area_id': 'AREA-1'}})
        report = copy.deepcopy(next(r for r in self.fixture.rows['materials.jsonl'] if r['kind'] == 'inspection_report'))
        report['evidence_id'] = 'D-SECOND-REPORT'
        report['facts']['conclusion'] = 'fail'
        self.fixture.add('materials.jsonl', report)
        self.fixture.policy['issuers'][0]['material_kinds'].append('harvest_record')
        self.fixture.policy['read_scope']['material_kinds'].append('harvest_record')
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        first = session.dispatch('list_evidence', {'cursor': None})
        session.dispatch('read_evidence', {'evidence_refs': [r['evidence_ref'] for r in first['entries']]})
        incomplete = session.assess_current()['assessment']
        self.assertEqual(incomplete['evidence_state'], 'Pending')
        self.assertFalse(incomplete['advance_allowed'])
        last = session.dispatch('list_evidence', {'cursor': first['next_cursor']})
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Pending')
        session.dispatch('read_evidence', {'evidence_refs': [last['entries'][0]['evidence_ref']]})
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Conflict')


    def test_host_cursor_cannot_advance_an_unassessed_candidate_or_reuse_old_refs(self):
        from joint_access import JointSession
        self.fixture.normal()
        joint = JointSession({'root_task_id': 'PUBLIC-ROOT'},
            {'C': ['PUBLIC-A', 'PUBLIC-B'], 'b': [.9, .6], 'batches': ['BATCH-A', 'BATCH-B'],
             'background_statistics': [{}, {}]},
            [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in ('PUBLIC-A', 'PUBLIC-B')],
            {'arm': 'necessary', 'request': {'design_text': 'PUBLIC', 'necessary_clauses': []}}, 'PUBLIC-HANDLE')
        session = self.fixture.session(joint=joint)
        self.assertEqual(session.advance_current()['status'], 'current_incomplete')
        entries = acquire_all(session)
        session.assess_current()
        self.assertEqual(session.advance_current()['status'], 'ok')
        old = session.dispatch('read_evidence', {'evidence_refs': [entries[0]['evidence_ref']]})
        self.assertEqual(old['status'], 'access_denied')
        self.assertEqual(session.audit_view()['usage']['candidates'], 1)
        self.assertEqual(session.audit_view()['acquired']['assessments']['PUBLIC-A']['evidence_state'], 'Supported')


    def test_q_conversion_uses_same_a_and_mean_includes_acquired_objects_outside_actual_g(self):
        from evidence_verification import rank_acquired_quality
        self.fixture.quality()
        session = self.fixture.session(joint=self.fixture.joint())
        acquire_all(session)
        session.assess_current()
        session.advance_current()
        acquire_all(session)
        binding = self.fixture.fusion_binding()
        before = session.audit_view()
        full = rank_acquired_quality(binding, before['acquired'])
        binding['mode'] = 'mean_quality'
        mean = rank_acquired_quality(binding, before['acquired'])
        control = rank_acquired_quality({**binding, 'mode': 'no_quality'}, before['acquired'])
        boundary = rank_acquired_quality({**binding, 'mode': 'boundary', 'alpha': 1}, before['acquired'])
        self.assertEqual(full['G'], ['PUBLIC-A'])
        self.assertEqual(full['order'], ['PUBLIC-A'])
        self.assertEqual([r['q'] for r in full['candidates']], [.6, .9])
        self.assertEqual(mean['mean_quality'], {'value': .75, 'denominator': 2})
        self.assertEqual(mean['candidates'][0]['score'], .73125)
        self.assertEqual([r['score'] for r in control['candidates']], [.825, .8])
        self.assertEqual([r['score'] for r in boundary['candidates']], [.9, .6])
        self.assertEqual(session.audit_view(), before)


    def test_q_missing_dispatch_does_not_invent_a_checks_or_change_the_denominator(self):
        from evidence_verification import rank_acquired_quality
        self.fixture.quality()
        session = self.fixture.session(joint=self.fixture.joint())
        page = session.dispatch('list_evidence', {'cursor': None})
        session.dispatch('read_evidence', {'evidence_refs': [r['evidence_ref'] for r in page['entries']
                                                           if r['target_id'] != 'D-transport_dispatch']})
        session.assess_current()
        before = session.audit_view()
        result = rank_acquired_quality(self.fixture.fusion_binding(), before['acquired'])
        self.assertEqual(result['candidates'][0]['A'], {'numerator': 0, 'denominator': 2})
        self.assertEqual(result['candidates'][0]['q'], .35)
        self.assertEqual(result['G'], ['PUBLIC-A'])
        self.assertEqual(session.audit_view(), before)


    def test_private_canary_changes_cannot_change_visible_trace_cost_or_assessment(self):
        self.fixture.normal()
        canary = self.fixture.root / 'private-gold-F-target-plan.json'
        def trace():
            with patch('secrets.token_bytes', return_value=b'p' * 32):
                session = self.fixture.session(clock=lambda: 0)
                page = session.dispatch('list_evidence', {'cursor': None})
                read = session.dispatch('read_evidence', {'evidence_refs': [r['evidence_ref'] for r in page['entries']]})
                result = session.assess_current()
            return page, read, result, session.audit_view()
        canary.write_text('{"gold":"Supported","target":"PUBLIC-A"}', encoding='utf-8')
        first = trace()
        canary.write_text('{"gold":"Conflict","target":"PUBLIC-B","plan":"other"}', encoding='utf-8')
        self.assertEqual(trace(), first)
        self.assertFalse(any('private-gold' in item['component_path'] for item in first[-1]['provenance'].values()))


    def test_illegal_revision_action_is_rejected_instead_of_admitted_as_a_source(self):
        self.fixture.normal().revise('fail')
        self.fixture.rows['actions.jsonl'][0]['issuer_id'] = 'SIM-RETAIL'
        self.fixture.register_all()
        self.fixture.seal()
        session = self.fixture.session()
        acquire_all(session)
        result = session.assess_current()['assessment']
        self.assertEqual(result['evidence_state'], 'Supported')
        self.assertNotIn('ACTION-REVISE', [r['target_id'] for r in result['accepted']])
        self.assertIn('ACTION-REVISE', [r['target_id'] for r in result['rejected']])


    def test_missing_sample_or_wrong_object_cannot_turn_a_fail_report_into_refutation(self):
        from tests.evidence_fixtures import sha, wire
        for case in ('missing_sample', 'wrong_batch', 'wrong_test_scope'):
            with self.subTest(case=case):
                fixture = EvidenceFixture(self.directory / case).normal()
                report = next(r for r in fixture.rows['materials.jsonl'] if r['kind'] == 'inspection_report')
                report['facts']['conclusion'] = 'fail'
                fixture.register_all()
                if case == 'missing_sample':
                    fixture.rows['materials.jsonl'] = [r for r in fixture.rows['materials.jsonl'] if r['kind'] != 'inspection_sample']
                elif case == 'wrong_batch':
                    report['sim_batch_id'] = 'BATCH-OTHER'
                    next(r for r in fixture.registrations if r['target_id'] == report['evidence_id'])['content_sha256'] = sha(wire(report))
                else:
                    report['facts']['test_scope'] = ['OTHER']
                    fixture.register_all()
                fixture.seal()
                session = fixture.session()
                acquire_all(session)
                self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Pending')

    def test_new_pass_or_unusable_new_head_preserves_version_rules(self):
        self.fixture.normal().revise('pass')
        session = self.fixture.session()
        acquire_all(session)
        self.assertEqual(session.assess_current()['assessment']['evidence_state'], 'Supported')
        newer = next(r for r in self.fixture.rows['materials.jsonl'] if r['version'] == 2)
        newer['facts']['conclusion'] = 'fail'
        self.fixture.seal()
        mismatch = self.fixture.session()
        acquire_all(mismatch)
        self.assertEqual(mismatch.assess_current()['assessment']['evidence_state'], 'Pending')
        self.fixture.revoke(version=2)
        revoked = self.fixture.session()
        acquire_all(revoked)
        self.assertEqual(revoked.assess_current()['assessment']['evidence_state'], 'Pending')

    def test_q_conversion_refuses_nonempty_action_scope_without_expanding_old_rank(self):
        from evidence_verification import rank_acquired_quality
        self.fixture.quality().revoke()
        session = self.fixture.session(joint=self.fixture.joint())
        acquire_all(session)
        session.assess_current()
        with self.assertRaisesRegex(ValueError, 'unsupported_quality_scope'):
            rank_acquired_quality(self.fixture.fusion_binding(), session.audit_view()['acquired'])


if __name__ == '__main__':
    unittest.main()
