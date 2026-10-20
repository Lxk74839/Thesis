"""Real Windows worker, invalid PUBLIC endpoint: no connection or real credential."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from evidence_access import PROJECT
from fourrouter_probe import send_response
from p1_engineering import AUTHORIZATION
from p1_storage import P1StorageGuard


class SWorker(unittest.TestCase):
    def test_authorized_sender_starts_real_worker_with_offline_endpoint(self):
        parent = PROJECT / '.tmp/recommendation-runtime/s-worker-tests'
        parent.mkdir(parents=True, exist_ok=True)
        outcomes = []
        def actual_worker(*args, **kwargs):
            result = subprocess.run(*args, **kwargs)
            outcomes.append(result.returncode)
            return result
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            with P1StorageGuard(Path(tmp), 64 * 1024**2) as guard:
                guard.authorize_S(AUTHORIZATION)
                guard.sender_active = True
                reply = send_response('PUBLIC-invalid-endpoint', {}, 'PUBLIC-unused-auth', 2,
                    process_run=actual_worker)
                guard.sender_active = False
                self.assertEqual(outcomes, [0])
                self.assertEqual(guard.allowed['response_workers'], 1)
                self.assertIsNone(reply['http_status'])
                self.assertEqual(guard.allowed['credentials'], 0)
                self.assertEqual(guard.attempts, {'network': 0, 'credentials': 0, 'evaluation': 0})


if __name__ == '__main__':
    unittest.main()
