"""Real frozen assembly and preflight only; never execute recommendations."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import p1_runtime as p1
from evidence_access import digest, encoded
from recommendation_runner import RecommendationRun, RunStop

PACKAGE = p1.PROJECT / '.scratch/ticket14-r-frozen-preflight-20261020'
OLD_RECEIPT = p1.PROJECT / '.scratch/ticket14-r-baseline-20261020/result.json'
DIAGNOSTICS = []


def condition_matrix(run):
    b, e = run.binding, run.evidence
    payloads = [json.loads(m['content']) for m in run.initial_messages]
    return {
        'budget_binding': b == run.budget.binding,
        'schema_version': b['schema_version'] == 'rsm-run-0.4.0',
        'execution_kind': b['execution_kind'] == 'fourrouter_responses',
        'development_identity': b['plan_source_scope'] == 'development_pilot' and b['root_task_id'] == p1.D1
            and b['pilot_id'] == p1.PILOT_ID and b['task_key'] == p1.TASK_KEYS['R']
            and b['execution_authorized'] is True and b['execution_budget'] == run.budget.limits,
        'method_and_arm': (b['method'], b['arm']) == ('R', 'necessary'),
        'K_and_clauses': type(b['K']) is int and b['K'] == 10 and b['necessary_clauses'] == ['c1', 'c2'],
        'C_shapes': len(b['C']) == len(set(b['C'])) == len(b['base_scores']) == len(b['batches']),
        'score_values': all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in b['base_scores']),
        'C_hash': b['C_sha256'] == digest(encoded(b['C'])),
        'scores_hash': b['base_score_sha256'] == digest(encoded(list(zip(b['C'], b['base_scores'])))),
        'initial_root_H_clauses': all(p['root_task_id'] == b['root_task_id'] and
            p['H_sha256'] == b['H_sha256'] == digest(encoded(p['H'])) and
            [c['clause_id'] if isinstance(c, dict) else c for c in p['request']['necessary_clauses']]
                == b['necessary_clauses'] for p in payloads),
        'assembled_projection_hash': run.state['input_projection_sha256'] == b['assembled_input_sha256'],
        'source_ref_equality': b['source_snapshot_ref'] == e.source.snapshot_ref,
        'legacy_source_root_informational_only': any(Path(e.source.snapshot_ref['path']).resolve().is_relative_to(p1.PROJECT / p)
            for p in ('.tmp/recommendation-runtime', 'data/recommendation-runtime-audit')),
        'frozen_source_error': p1.frozen_snapshot_error(b, e.source.snapshot_ref),
        'joint_C_scores_batches': (e.joint.candidates['C'], e.joint.candidates['b'], e.joint.candidates['batches'])
            == (b['C'], b['base_scores'], b['batches']),
        'first_evidence_candidate': e.binding['parent_asin'] == run.queue[0],
        'R_zero_limits_and_reserve': all(run.budget.limits[k] == run.budget.final_reserve[k] == 0
            for k in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd')),
        'quality_branch': 'not_applicable_necessary',
        'model_branch': 'not_applicable_R',
        'PUBLIC_and_on_demand_branches': 'not_applicable_real_4router'}


def tearDownModule():
    (PACKAGE / 'preflight-conditions.json').write_text(json.dumps(DIAGNOSTICS, indent=2), encoding='utf-8')


class FrozenPreflight(unittest.TestCase):
    def setUp(self):
        parent = p1.PROJECT / '.tmp/recommendation-runtime/frozen-R-preflight-diagnostics'
        parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='real-D1-preflight-', dir=parent)
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name)
        self.guard = p1.P1StorageGuard(Path(temp.name), 64 * 1024**2)
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)
        self.cfg = json.loads((PACKAGE / 'r.config.json').read_bytes())
        self.assembly = p1.assemble_task(p1.PILOT, p1.TASK_KEYS['R'], execution_record={
            'run_id': 'P1-D1-V00-R-PREFLIGHT-ONLY'})
        self.run = p1.build_runtime(self.assembly, self.cfg, 'R', counter=None, output_root=Path(temp.name))

    def assert_rejected(self, run, reason):
        with self.assertRaises(RunStop) as caught:
            run._preflight()
        self.assertEqual(caught.exception.reason, reason)
        self.assertTrue(all(v == 0 for k, v in run.budget.audit_view()['usage'].items() if k != 'elapsed_ms'))

    def altered_runtime(self, change):
        assembly = copy.deepcopy(self.assembly)
        change(assembly)
        return p1.build_runtime(assembly, self.cfg, 'R', counter=None, output_root=self.output / 'altered')

    def test_wrong_view_is_rejected_with_other_binding_checks_consistent(self):
        run = self.altered_runtime(lambda a: a['binding'].update(view_id='q-WRONG-VIEW'))
        self.assertEqual(run.binding, run.budget.binding)
        self.assert_rejected(run, 'frozen_view_binding')

    def test_self_consistent_reference_cannot_replace_frozen_reference(self):
        def change(a):
            a['snapshot_ref']['sha256'] = '0' * 64
            a['binding']['source_snapshot_ref'] = copy.deepcopy(a['snapshot_ref'])
        run = self.altered_runtime(change)
        self.assertEqual(run.binding['source_snapshot_ref'], run.evidence.source.snapshot_ref)
        self.assert_rejected(run, 'frozen_snapshot_reference')

    def test_same_length_changed_content_is_rejected_by_SHA_without_modifying_source(self):
        self.changed_content_case(lambda raw: raw[:-1] + b' ', 'frozen_snapshot_sha256')

    def test_changed_length_is_rejected_before_SHA_without_modifying_source(self):
        self.changed_content_case(lambda raw: raw + b'\n', 'frozen_snapshot_bytes')

    def changed_content_case(self, change, reason):
        expected = (p1.PROJECT / self.assembly['snapshot_ref']['path']).resolve()
        original = Path.read_bytes
        reads = []
        def read(path):
            raw = original(path)
            if path.resolve() == expected:
                reads.append(str(path))
                return change(raw)
            return raw
        before = digest(original(expected))
        with patch.object(Path, 'read_bytes', read):
            self.assert_rejected(self.run, reason)
        self.assertEqual(len(reads), 1)
        self.assertEqual(digest(original(expected)), before)

    def test_outside_and_other_directory_members_are_rejected_without_reading_them(self):
        for index, wrong in enumerate((str(p1.PROJECT.parent / 'outside/snapshot.json'),
                'data/sim-scenarios/unapproved/snapshot.json', '.tmp/recommendation-runtime/snapshot.json')):
            with self.subTest(path=wrong):
                assembly = copy.deepcopy(self.assembly)
                assembly['snapshot_ref']['path'] = wrong
                assembly['binding']['source_snapshot_ref'] = copy.deepcopy(assembly['snapshot_ref'])
                run = p1.build_runtime(assembly, self.cfg, 'R', counter=None,
                    output_root=self.output / ('outside-' + str(index)))
                self.assert_rejected(run, 'frozen_snapshot_reference')

    def test_real_1493_candidate_assembly_passes_complete_preflight_without_execution(self):
        old = json.loads(OLD_RECEIPT.read_bytes())
        old_audit = json.loads(Path(old['audit_path']).read_bytes())
        self.assertEqual((old_audit['terminal'], old_audit['reason']), ('failed_protocol', 'runtime_preflight_failed'))
        self.assertEqual(len(self.run.binding['C']), 1493)
        self.assertEqual(self.run.binding['C_sha256'], old['C_sha256'])
        DIAGNOSTICS.append({'case': self._testMethodName, 'conditions': condition_matrix(self.run)})
        with patch.object(RecommendationRun, 'run', side_effect=AssertionError('recommendation_execution_forbidden')) as execute:
            self.run._preflight()
            execute.assert_not_called()
        usage = self.run.budget.audit_view()['usage']
        self.assertTrue(all(v == 0 for k, v in usage.items() if k != 'elapsed_ms'))
        self.assertIsNone(self.run.model)
        self.assertEqual(self.guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})


if __name__ == '__main__':
    unittest.main()
