"""Launch the authorized independent entry and record wall time; never retries."""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
assert not (HERE / 'evaluation-terminal.json').exists()
started = time.time()
with (HERE / 'evaluation.stdout').open('wb') as stream:
    result = subprocess.run([sys.executable, '-B', '-u', str(ROOT / 'compact_evaluation.py')],
                            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False)
record = {'started_epoch': started, 'ended_epoch': time.time(), 'exit_code': result.returncode,
          'entry_point': 'compact_evaluation.py', 'automatic_retry': False}
(HERE / 'evaluation-terminal.json').write_text(json.dumps(record), encoding='utf-8')
print(json.dumps(record), flush=True)
raise SystemExit(result.returncode)
