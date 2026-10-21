"""PUBLIC artifact/read-policy fixtures; no real pilot or reference evaluation."""
import unittest
from pathlib import Path
import tempfile


class EvaluationReadPolicy(unittest.TestCase):
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
