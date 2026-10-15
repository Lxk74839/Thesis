"""Archive one complete regression run without overwriting earlier evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
assert re.fullmatch('[a-z0-9-]+', args.label)
assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
stem = ROOT / '.scratch/data-preparation/verification' / ('ticket11-regression-' + args.label)
assert not stem.with_suffix('.json').exists() and not stem.with_suffix('.txt').exists()
started = time.monotonic()
result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=ROOT,
                        capture_output=True, text=True, encoding='utf-8')
output = result.stdout + result.stderr
stem.with_suffix('.txt').write_text(output, encoding='utf-8', newline='')
count = re.search(r'Ran (\d+) tests? in', output)
report = {'status': 'passed' if result.returncode == 0 and count else 'failed',
          'tests': int(count[1]) if count else None, 'exit_code': result.returncode,
          'wall_seconds': round(time.monotonic() - started, 3), 'at_utc': datetime.now(timezone.utc).isoformat(),
          'python': sys.version, 'conda_prefix': sys.prefix,
          'git_head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'sources': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
              ('prepare_data.py', 'sim_scenarios.py', 'sim_normal.py', 'tests/test_sim_scenarios.py',
               '.scratch/data-preparation/diagnostics/verify_sim11.py',
               '.scratch/data-preparation/verification/ticket11_delivery_checks.py')},
          'log_sha256': hashlib.sha256(stem.with_suffix('.txt').read_bytes()).hexdigest()}
stem.with_suffix('.json').write_bytes(json.dumps(report, sort_keys=True, indent=2).encode() + b'\n')
print(json.dumps(report))
if result.returncode:
    print(output[-12000:])
sys.exit(result.returncode)
