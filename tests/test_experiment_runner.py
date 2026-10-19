"""Public planning, dispatch and bounded offline CLI behaviors."""
import socket
import unittest
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import os

PROJECT = Path(__file__).resolve().parents[1]


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class PlanFixture:
    """Upstream-shaped public files, without production builders or evaluation answers."""
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True)
        self.ids = [f'{i:064x}' for i in range(1603)]
        cohort = [{'task_id': key, 'split': 'dev' if i < 320 else 'test', 'target': 'PRIVATE-CANARY'}
                  for i, key in enumerate(self.ids)]
        roots = [{'root_task_id': key, 'C_sha256': 'c' * 64, 'H_sha256': 'a' * 64,
                  'base_scores_sha256': 'b' * 64} for key in self.ids]
        candidates = [{'root_task_id': key, 'C': ['PUBLIC-A'], 'b': [.5], 'batches': ['BATCH-A']}
                      for key in self.ids]
        components = {}
        self.scenes = []
        for i in range(16):
            view_id = 'q_' + hashlib.sha256(b'Thesis|ticket11|view|v1\0' + b'20261015\0' + f'{i:02d}'.encode()).hexdigest()
            ref = self.write('facts/' + view_id + '/snapshot.json', {'snapshot_id': 'snapshot-' + view_id})
            components['views/' + view_id + '/snapshot.json'] = ref
            self.scenes.append({'label': f'V{i:02d}', 'view_id': view_id, 'snapshot': ref,
                                'snapshot_id': 'snapshot-' + view_id, 'arm': 'necessary'})
        for label in ('Q1', 'Q2'):
            ref = self.write('facts/' + label + '/snapshot.json', {'snapshot_id': 'snapshot-' + label})
            self.scenes.append({'label': label, 'view_id': 'opaque-' + label, 'snapshot': ref,
                                'snapshot_id': 'snapshot-' + label, 'arm': 'quality'})
        original = {'V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2'}
        bindings = [dict(scene, root_task_id=key, request_profile_id='R1_AND_R5_SIM_Q1_ON_SALE',
                         principal_id='SIM-VERIFIER', verify_at_ms=1791417600000)
                    for key in self.ids for scene in self.scenes if scene['label'] in original]
        self.refs = {'scope': 'public_fixture',
            'cohort': self.write('cohort.jsonl', cohort), 'roots': self.write('roots.jsonl', roots),
            'candidates': self.write('candidates.jsonl', candidates),
            'view_bindings': self.write('views.jsonl', bindings),
            'scenarios': self.write('scenarios.json', {'components': components})}

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b''.join(wire(row) + b'\n' for row in value) if isinstance(value, list) else wire(value) + b'\n')
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


class PlanningBoundary(unittest.TestCase):
    def setUp(self):
        retain = os.environ.get('THESIS_ON_DEMAND_CASES')
        parent = Path(retain) if retain else PROJECT / '.tmp/recommendation-runtime'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=self._testMethodName + '-', dir=parent, delete=not bool(retain))
        if not retain:
            self.addCleanup(self.temp.cleanup)
        self.fixture = PlanFixture(Path(self.temp.name) / 'source')

    def test_fixed_test_pool_produces_a_small_complete_plan(self):
        from experiment_runner import build_plan
        plan = build_plan(self.fixture.refs, '20261019', Path(self.temp.name) / 'plan')
        self.assertEqual(plan['counts'], {'users': 100, 'development_overlap': 0, 'scenarios': 18,
                         'bindings': 1800, 'tasks': 5000, 'model_tasks': 3400})
        users = [json.loads(line) for line in (Path(self.temp.name) / 'plan/sample-users.jsonl').read_text().splitlines()]
        # Independently calculated with .NET SHA256 before writing the implementation.
        self.assertEqual(users[0], {'selection_rank': 1, 'root_task_id': '0' * 61 + '373',
            'selection_digest': '0008ccd047bbade8f0ceb522a84ac264aa0377bdc66614bcb40e4dc6c2b90d02'})
        self.assertEqual([u['root_task_id'][-3:] for u in users[:3]], ['373', '337', '2d9'])
        tasks = [json.loads(line) for line in (Path(self.temp.name) / 'plan/tasks.jsonl').read_text().splitlines()]
        self.assertEqual(len({row['task_key'] for row in tasks}), 5000)
        self.assertTrue(all(set(row) == {'task_key', 'binding_id', 'method', 'repeat', 'uses_model'} for row in tasks))
        self.assertTrue(all(value is None for value in plan['model_binding'].values()))

    def test_accepted_component_row_counts_do_not_change_snapshot_identity(self):
        from experiment_runner import build_plan
        record = json.loads(Path(self.fixture.refs['scenarios']['path']).read_bytes())
        for ref in record['components'].values():
            ref['records'] = 1
        self.fixture.refs['scenarios'] = self.fixture.write('scenarios.json', record)
        result = build_plan(self.fixture.refs, '20261019', Path(self.temp.name) / 'plan')
        self.assertEqual(result['counts']['bindings'], 1800)

    def test_sampling_ignores_cohort_order_and_private_answers(self):
        from experiment_runner import build_plan
        first = Path(self.temp.name) / 'first'
        build_plan(self.fixture.refs, '20261019', first)
        rows = [json.loads(line) for line in Path(self.fixture.refs['cohort']['path']).read_text().splitlines()]
        for row in rows:
            row['target'] = 'DIFFERENT-PRIVATE-ANSWER'
        self.fixture.refs['cohort'] = self.fixture.write('cohort.jsonl', list(reversed(rows)))
        second = Path(self.temp.name) / 'second'
        build_plan(self.fixture.refs, '20261019', second)
        self.assertEqual((first / 'sample-users.jsonl').read_bytes(), (second / 'sample-users.jsonl').read_bytes())
        self.assertEqual((first / 'root-references.jsonl').read_bytes(), (second / 'root-references.jsonl').read_bytes())
        with self.assertRaisesRegex(ValueError, 'plan_output_exists'):
            build_plan(self.fixture.refs, '20261019', first)

    def test_independent_plan_check_rejects_a_resealed_duplicate_task(self):
        from experiment_runner import build_plan
        root = Path(self.temp.name) / 'plan'
        build_plan(self.fixture.refs, '20261019', root)
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py'
        command = [sys.executable, '-B', str(checker), 'plan', str(root)]
        passed = subprocess.run(command, cwd=PROJECT, capture_output=True)
        self.assertEqual(passed.returncode, 0, passed.stdout.decode() + passed.stderr.decode())
        tasks = [json.loads(line) for line in (root / 'tasks.jsonl').read_text().splitlines()]
        tasks[-1] = tasks[0]
        raw = b''.join(wire(row) + b'\n' for row in tasks)
        (root / 'tasks.jsonl').write_bytes(raw)
        plan = json.loads((root / 'plan.json').read_bytes())
        plan['components']['tasks.jsonl'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        plan.pop('plan_id')
        plan['plan_id'] = hashlib.sha256(wire(plan)).hexdigest()
        (root / 'plan.json').write_bytes(wire(plan))
        failed = subprocess.run(command, cwd=PROJECT, capture_output=True)
        self.assertEqual(failed.returncode, 2)

    def test_independent_check_does_not_accept_a_different_views_snapshot(self):
        from experiment_runner import build_plan
        root = Path(self.temp.name) / 'plan'
        build_plan(self.fixture.refs, '20261019', root)
        scenes = [json.loads(line) for line in (root / 'scenes.jsonl').read_text().splitlines()]
        scenes[2]['snapshot'], scenes[2]['snapshot_id'] = scenes[3]['snapshot'], scenes[3]['snapshot_id']
        raw = b''.join(wire(row) + b'\n' for row in scenes)
        (root / 'scenes.jsonl').write_bytes(raw)
        plan = json.loads((root / 'plan.json').read_bytes())
        plan['components']['scenes.jsonl'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        plan.pop('plan_id')
        plan['plan_id'] = hashlib.sha256(wire(plan)).hexdigest()
        (root / 'plan.json').write_bytes(wire(plan))
        checker = PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py'
        checked = subprocess.run([sys.executable, '-B', str(checker), 'plan', str(root)], cwd=PROJECT, capture_output=True)
        self.assertEqual(checked.returncode, 2, checked.stdout.decode())


class GuardBoundary(unittest.TestCase):
    def test_offline_package_blocks_network_before_connect(self):
        with socket.socket() as connection:
            with self.assertRaisesRegex(OSError, 'on_demand_network_forbidden'):
                connection.connect(('127.0.0.1', 9))


if __name__ == '__main__':
    unittest.main()
