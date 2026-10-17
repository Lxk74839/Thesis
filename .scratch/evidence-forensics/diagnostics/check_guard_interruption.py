"""Controlled crash of a nested guard; the outer real guard accounts its entire tree."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(tempfile.mkdtemp(prefix='evidence-guard-crash-', dir=ROOT / '.tmp'))
GUARD = ROOT / '.scratch/evidence-forensics/diagnostics/run_check.py'
# Only the system audit-directory seam is substituted. The actual guard code runs.
WRAPPER = """
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('controlled_guard', sys.argv[1])
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.AUDIT = pathlib.Path(sys.argv[2])
sys.argv = [str(guard.__file__), *sys.argv[3:]]
raise SystemExit(guard.main())
"""
signal = DIRECTORY / 'child-started'
unexpected = DIRECTORY / 'unexpected-second-child'
child_code = "from pathlib import Path; import time; Path(%r).write_text('started'); time.sleep(30)" % str(signal)
command = [sys.executable, '-B', '-c', WRAPPER, str(GUARD), str(DIRECTORY)]
first = subprocess.Popen([*command, 'interrupted', '-c', child_code], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    deadline = time.monotonic() + 5
    while not signal.exists() and first.poll() is None and time.monotonic() < deadline:
        time.sleep(.01)
    assert signal.exists(), 'controlled child did not start'
finally:
    first.kill()
    first.communicate(timeout=5)
second = subprocess.run([*command, 'after-crash', '-c',
    "from pathlib import Path; Path(%r).write_text('unexpected')" % str(unexpected)],
    cwd=ROOT, capture_output=True, text=True, timeout=5)
result = {'nested_audit_directory': DIRECTORY.relative_to(ROOT).as_posix(),
    'first_guard_forcibly_terminated': first.returncode != 0,
    'second_guard_exit': second.returncode, 'second_guard_output': second.stdout + second.stderr,
    'second_child_started': unexpected.exists(),
    'unresolved_reservation_preserved': (DIRECTORY / 'resource-inflight.json').exists(),
    'accounting': 'nested crash is fully included in the outer global guard Job and wall time'}
print(json.dumps(result, sort_keys=True), flush=True)
assert second.returncode != 0 and not unexpected.exists(), 'stale ledger admitted work after interruption'
assert result['unresolved_reservation_preserved'], 'unknown usage was discarded'
