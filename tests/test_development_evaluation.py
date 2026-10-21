"""PUBLIC artifact/read-policy fixtures; no real pilot or reference evaluation."""
import unittest
from pathlib import Path
import tempfile


class EvaluationReadPolicy(unittest.TestCase):
    def test_actual_evaluation_output_shape_is_denied_to_the_normal_runtime_guard(self):
        from development_evaluation import evaluation_directory
        from p1_storage import P1StorageGuard
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            target = evaluation_directory(output, 'T14-D1-EVALUATION-PUBLIC')
            target.mkdir(parents=True)
            source = target / 'preference.jsonl'
            source.write_text('{"scope":"PUBLIC fixture"}')
            with P1StorageGuard(output, 1024**3, development=True):
                with self.assertRaises(OSError):
                    source.read_bytes()

    def test_legacy_R_sidecar_binds_original_A_and_preserves_old_bytes(self):
        from tests import test_live_integration as fixture
        from development_evaluation import legacy_R_sidecar
        from experiment_io import load_evaluation_inputs, _execution, _read, _public_path
        from experiment_evaluation import score_task
        case = fixture.LiveIntegration('test_public_artifacts_and_native_reference_rows_reach_score_task')
        case.setUp()
        try:
            sources = case.evaluation_sources()
            _, run = case.make_assembled()
            run.trace_artifacts = False  # PUBLIC legacy shape, before acquired_ref existed.
            result = run.run()
            files = [fixture.file_ref(run.output_root / name) for name in ('audit.json', 'publication.json', 'budget.jsonl')]
            # PUBLIC legacy attempt record, never an actual development claim.
            attempt = run.output_root / 'attempt.json'
            attempt.write_text('{"scope":"PUBLIC fixture"}')
            files.append(fixture.file_ref(attempt))
            original = {r['path']: Path(r['path']).read_bytes() for r in files}
            target = case.root / 'legacy-evaluation'
            target.mkdir()
            ref = legacy_R_sidecar(target, run_root=run.output_root, task_key='PUBLIC-TASK',
                plan_id=case.manifest['plan_id'], expected_files=files)
            plan, observations = load_evaluation_inputs(case.plan, execution_index={}, reference_sources=sources)
            selected = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
            with self.assertRaisesRegex(ValueError, 'audit_scope_mismatch'):
                _execution(selected['task'], ref, plan['plan_id'])
            execution = _execution(selected['task'], ref, plan['plan_id'], legacy_R=True,
                read_artifact=_read, resolve_artifact=_public_path)
            self.assertEqual(score_task(selected['task'], execution, selected['reference'])['status'], 'scored')
            self.assertEqual(execution['usage']['basis'], 'no_model')
            self.assertEqual(execution['usage']['input_tokens'], 0)
            self.assertEqual({p: Path(p).read_bytes() for p in original}, original)
            bad = [r | {'sha256': '0'*64} if Path(r['path']).name == 'audit.json' else r for r in files]
            with self.assertRaisesRegex(ValueError, 'legacy_R_evidence_changed'):
                legacy_R_sidecar(target, run_root=run.output_root, task_key='PUBLIC-TASK',
                    plan_id=plan['plan_id'], expected_files=bad)
        finally:
            case.temp.cleanup()

    def test_evaluation_guard_allows_only_pinned_reference_reads_and_never_a_sender(self):
        from p1_storage import P1StorageGuard
        from development_pilot import AUTHORIZATION
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / 'sim-reference/PUBLIC-reference.json'
            forbidden = root / 'sim-reference/PUBLIC-other.json'
            allowed.parent.mkdir()
            allowed.write_text('PUBLIC fixture')
            forbidden.write_text('PUBLIC fixture')
            output = root / 'output'
            target = output / 'evaluation-PUBLIC'
            with P1StorageGuard(output, 1024**3, run_root=target, run_limit_bytes=128*1024**2,
                    development=True, evaluation_sources=[allowed]) as guard:
                self.assertEqual(allowed.read_text(), 'PUBLIC fixture')
                with self.assertRaises(OSError):
                    forbidden.read_bytes()
                with self.assertRaises(OSError):
                    guard.authorize_development(AUTHORIZATION)
                with self.assertRaises(OSError):
                    allowed.write_text('overwrite')

    def test_existing_score_and_summary_accept_explicit_readonly_artifact_access(self):
        from tests import test_live_integration as fixture
        from experiment_runner import run_task
        from experiment_io import load_evaluation_inputs, _read, _public_path
        from experiment_evaluation import score_task, summarize
        case = fixture.LiveIntegration('test_public_artifacts_and_native_reference_rows_reach_score_task')
        case.setUp()
        try:
            sources = case.evaluation_sources()
            _, run = case.make_assembled()
            run_task(case.plan, 'PUBLIC-TASK', runtime=run, output_root=run.output_root, execution_record=case.record)
            reads = []
            def reader(ref):
                reads.append(ref['path'])
                return _read(ref)
            plan, observations = load_evaluation_inputs(case.plan,
                execution_index={'PUBLIC-TASK': fixture.file_ref(run.output_root / 'task.json')},
                reference_sources=sources, read_artifact=reader, resolve_artifact=_public_path)
            selected = next(o for o in observations if o['task']['task_key'] == 'PUBLIC-TASK')
            self.assertEqual(score_task(**selected)['status'], 'scored')
            self.assertEqual(summarize(plan, [score_task(**o) for o in observations])['status'], 'incomplete')
            self.assertEqual(len(observations), 50)
            self.assertTrue(reads)
        finally:
            case.temp.cleanup()
