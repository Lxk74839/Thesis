"""Record actual approved-seam RED/GREEN runs in the active Thesis runtime."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('cycle', type=int)
parser.add_argument('phase', choices=['red', 'green'])
parser.add_argument('test')
args = parser.parse_args()
assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
result = subprocess.run([sys.executable, '-m', 'unittest', args.test], cwd=ROOT,
                        capture_output=True, text=True, encoding='utf-8')
log = ROOT / '.scratch/data-preparation/verification' / f'ticket11-{args.cycle:02d}-{args.phase}.txt'
log.write_text(result.stdout + result.stderr, encoding='utf-8', newline='')
entry = {'cycle': args.cycle, 'phase': args.phase, 'test': args.test, 'exit_code': result.returncode,
         'log': log.relative_to(ROOT).as_posix(), 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
         'at_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version, 'prefix': sys.prefix,
         'sources': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                     for name in ('prepare_data.py', 'sim_scenarios.py', 'tests/test_sim_scenarios.py',
                                  '.scratch/data-preparation/diagnostics/verify_sim11.py') if (ROOT / name).exists()}}
with (log.parent / 'ticket11-tdd-history.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
    stream.write(json.dumps(entry, sort_keys=True) + '\n')
print(result.stdout + result.stderr)
print(json.dumps({'cycle': args.cycle, 'phase': args.phase, 'actual_exit_code': result.returncode}))
sys.exit(0 if (result.returncode != 0 if args.phase == 'red' else result.returncode == 0) else 1)
