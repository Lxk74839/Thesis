"""Only temporary PUBLIC markers; no credentials, data, subprocess or network."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class SReceipt(unittest.TestCase):
    def load_runner(self):
        spec = importlib.util.spec_from_file_location('PUBLIC_s_once',
            ROOT / '.scratch/ticket14-s-engineering-20261020/run_once.py')
        module = importlib.util.module_from_spec(spec)
        with patch('sys.stdin', io.TextIOWrapper(io.BytesIO(b'GO\n'))):
            spec.loader.exec_module(module)
        return module

    def test_startup_keeps_old_record_and_writes_only_real_execution_receipt(self):
        runner = self.load_runner()
        parent = ROOT / '.tmp/recommendation-runtime/s-receipt-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            package = Path(tmp)
            old = package / 'result.json'
            original = b'{"terminal":"not_started","PUBLIC":true}\n'
            old.write_bytes(original)
            with patch.object(runner, 'PACKAGE', package), patch.object(runner.p1, 'OUTPUT', package / 'PUBLIC-output'), \
                    patch('sys.argv', ['PUBLIC', '0' * 40]), patch('builtins.print'), \
                    patch.object(runner.p1, 'execute_p1', return_value={'terminal': 'not_started', 'started': False}) as execute:
                self.assertEqual(runner.main(), 2)
            execute.assert_called_once()
            self.assertTrue((package / 'execution-result.json').exists())
            self.assertEqual(old.read_bytes(), original)

    def test_old_not_started_does_not_block_first_execution_and_markers_prevent_replay(self):
        runner = self.load_runner()
        parent = ROOT / '.tmp/recommendation-runtime/s-receipt-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            package = Path(tmp)
            old = package / 'result.json'
            original = b'{"terminal":"not_started","PUBLIC":true}\n'
            old.write_bytes(original)
            attempt = package / 'PUBLIC-run/attempt.json'
            receipt = runner.ensure_first_execution(package, attempt)
            self.assertEqual(receipt.name, 'execution-result.json')
            self.assertEqual(old.read_bytes(), original)
            for marker in (package / 'execution-claim.json', receipt,
                    package / 'execution-resources.jsonl', attempt):
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text('PUBLIC-consumed', encoding='utf-8')
                with self.subTest(marker=marker.name), self.assertRaises(FileExistsError):
                    runner.ensure_first_execution(package, attempt)
                marker.unlink()
                self.assertEqual(old.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
