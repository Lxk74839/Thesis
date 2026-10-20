"""Bounded PUBLIC tests; the actual D1 R run is a separate one-shot command."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import p1_runtime as p1

PACKAGE = p1.PROJECT / '.scratch/ticket14-r-baseline-20261020'


class ROnce(unittest.TestCase):
    def test_PUBLIC_inputs_cannot_be_relabelled_as_frozen_development_scope(self):
        from tests.runtime_fixtures import RuntimeFixture
        from p1_storage import P1StorageGuard
        parent = p1.PROJECT / '.tmp/recommendation-runtime/R-once'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            fixture = RuntimeFixture(Path(tmp))
            fixture.candidates(['PUBLIC-A', 'PUBLIC-B'])
            source = fixture.make('R')
            public_result = source.run()
            self.assertEqual(public_result['terminal'], 'released')
            self.assertEqual(public_result['release_scope'], 'public_fixture_only')
            binding = source.binding | {'root_task_id': p1.D1, 'plan_source_scope': 'development_pilot',
                'task_key': p1.TASK_KEYS['R']}
            assembly = {'binding': binding, 'root': {'root_task_id': p1.D1, 'H': [], 'H_sha256': binding['H_sha256']},
                'candidates': {'C': fixture.parents, 'b': fixture.scores, 'batches': fixture.batches,
                    'background_statistics': [{}, {}]},
                'catalog': [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in fixture.parents],
                'view': {'arm': 'necessary', 'request': {'design_text': 'PUBLIC R1 AND R5',
                    'necessary_clauses': ['c1', 'c2']}},
                'snapshot_ref': source.evidence.source.snapshot_ref}
            cfg = json.loads((PACKAGE / 'r.config.json').read_text(encoding='utf-8'))
            root = Path(tmp) / 'executed'
            guard = P1StorageGuard(root, 64 * 1024**2)
            with guard:
                run = p1.build_runtime(assembly, cfg, 'R', counter=None, output_root=root)
                result = run.run()
            self.assertEqual(result['terminal'], 'failed_protocol')
            self.assertEqual(result['reason'], 'frozen_view_binding')
            self.assertEqual(result['binding']['C'], ['PUBLIC-A', 'PUBLIC-B'])
            self.assertEqual(len(result['assessments']), 0)
            self.assertEqual(len(result['delivered']), 0)
            self.assertIsNone(run.model)
            self.assertEqual({k: result['budget']['usage'][k] for k in (
                'model_calls', 'input_tokens', 'output_tokens', 'cost_microusd')},
                {'model_calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'cost_microusd': 0})
            self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})
            self.assertIsNone(result['publication_path'])

    def test_failed_R_assembly_is_claimed_and_cannot_be_automatically_repeated(self):
        from p1_storage import P1StorageGuard
        parent = p1.PROJECT / '.tmp/recommendation-runtime/R-once'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp, patch('p1_runtime.assemble_task',
                side_effect=OSError('PUBLIC-assembly-failed')) as assembly:
            root = Path(tmp) / 'output'
            cfg = json.loads((PACKAGE / 'r.config.json').read_text(encoding='utf-8'))
            cfg['authorization_id'] = 'PUBLIC-CLAIM'
            path = Path(tmp) / 'PUBLIC-config.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            with patch('p1_runtime.OUTPUT', root):
                with self.assertRaisesRegex(OSError, 'PUBLIC-assembly-failed'):
                    p1.execute_p1(path, 'R', storage_guard=P1StorageGuard(root, cfg['storage_limit_bytes']))
                self.assertTrue((root / 'P1-D1-V00-R-PUBLIC-CLAIM/attempt.json').exists())
                repeated = p1.execute_p1(path, 'R', storage_guard=P1StorageGuard(root, cfg['storage_limit_bytes']))
                self.assertEqual(repeated['missing'], ['existing_execution_no_retry'])
                self.assertIs(repeated['started'], False)
                self.assertEqual(assembly.call_count, 1)

    def test_frozen_R_assembly_reuses_membership_before_reading_any_user_row(self):
        from experiment_runner import assemble_task
        # Only frozen metadata is read; the first actual input-row read stops here.
        with patch('experiment_runner._source_row', side_effect=RuntimeError('PUBLIC-input-read-stop')) as read:
            with self.assertRaisesRegex(RuntimeError, 'PUBLIC-input-read-stop'):
                assemble_task(p1.PILOT, p1.TASK_KEYS['R'])
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read.call_args.args[0]['path'],
            'data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0/model/roots.jsonl')

    def test_R_authorization_rejects_other_methods_keys_and_property_only_guard(self):
        from p1_storage import P1StorageGuard
        from tests.test_p1_project_id import public_config
        parent = p1.PROJECT / '.tmp/recommendation-runtime/R-once'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp, patch('p1_runtime.assemble_task',
                side_effect=AssertionError('assembly_forbidden')) as assembly:
            cfg = public_config()
            cfg['authorized_task_keys'] = [p1.TASK_KEYS['R']]
            path = Path(tmp) / 'PUBLIC-config.json'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            guard = P1StorageGuard(p1.OUTPUT, cfg['storage_limit_bytes'])
            self.assertEqual(p1.prepare_p1(path, 'R', storage_guard=guard)['terminal'], 'ready')
            for method in ('S', 'M'):
                with self.subTest(method=method):
                    self.assertIn('execution_task_authorization', p1.prepare_p1(
                        path, method, counter=Mock(), storage_guard=guard)['missing'])
                    result = p1.execute_p1(path, method, counter=Mock(), storage_guard=guard)
                    self.assertEqual(result['terminal'], 'not_started')
                    self.assertIn('execution_task_authorization', result['missing'])
            cfg['authorized_task_keys'] = [p1.TASK_KEYS['S']]
            path.write_text(json.dumps(cfg), encoding='utf-8')
            self.assertIn('execution_task_authorization', p1.prepare_p1(path, 'R', storage_guard=guard)['missing'])
            self.assertIn('execution_task_authorization', p1.execute_p1(path, 'R', storage_guard=guard)['missing'])
            cfg['authorized_task_keys'] = [p1.TASK_KEYS['R']]
            path.write_text(json.dumps(cfg), encoding='utf-8')
            fake = Mock(root=p1.OUTPUT, limit_bytes=cfg['storage_limit_bytes'])
            self.assertIn('controlled_storage_guard', p1.prepare_p1(path, 'R', storage_guard=fake)['missing'])
            self.assertIn('controlled_storage_guard', p1.execute_p1(path, 'R', storage_guard=fake)['missing'])
            cfg['task_keys']['R'] = p1.TASK_KEYS['S']
            path.write_text(json.dumps(cfg), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'P1_identity_mismatch'):
                p1.execute_p1(path, 'R', storage_guard=guard)
            assembly.assert_not_called()

    def test_storage_guard_enforces_actual_writes_and_scope(self):
        from p1_storage import P1StorageGuard
        parent = p1.PROJECT / '.tmp/recommendation-runtime/R-once'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            root = Path(tmp) / 'output'
            root.mkdir()
            guard = P1StorageGuard(root, 5)
            with guard:
                (root / 'first').write_bytes(b'12345')
                with self.assertRaisesRegex(OSError, 'storage_quota'):
                    (root / 'too-large').write_bytes(b'6')
                with self.assertRaisesRegex(OSError, 'outside_output'):
                    (Path(tmp) / 'outside').write_bytes(b'0')
                with self.assertRaisesRegex(OSError, 'credentials_forbidden'):
                    (Path(tmp) / '.secrets/PUBLIC-key.json').read_bytes()
                with self.assertRaisesRegex(OSError, 'evaluation_forbidden'):
                    (Path(tmp) / 'private/PUBLIC-label.json').read_bytes()
                import socket
                with self.assertRaisesRegex(OSError, 'network_forbidden'):
                    socket.socket()
            self.assertEqual(guard.charged_bytes, 5)
            self.assertEqual((root / 'first').read_bytes(), b'12345')
            self.assertFalse((Path(tmp) / 'outside').exists())


if __name__ == '__main__':
    unittest.main()
