"""Hash existing materials without parsing private inputs or evaluation results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261018-batch'
BASE = 'ac4874c7218ea1a795ddf992a9c23d133766a293'
EDITABLE = {'recommendation_runner.py', 'evidence_access.py', 'model_adapter.py'}


def fingerprint(path):
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


mode = sys.argv[1]
before = AUDIT / 'protected-before.json'
if mode == 'before':
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    paths = {ROOT / name for name in tracked if name not in EDITABLE}
    paths.update(p for folder in ('reports', 'manuscript', 'research')
                 for p in (ROOT / folder).rglob('*') if p.is_file())
    values = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in sorted(paths)}
    with before.open('x', encoding='utf-8') as stream:
        json.dump(values, stream, sort_keys=True, ensure_ascii=False)
    print(json.dumps({'files': len(values), 'bytes': sum(v['bytes'] for v in values.values())}))
else:
    values = json.loads(before.read_bytes())
    changed = [name for name, value in values.items()
               if not (ROOT / name).is_file() or fingerprint(ROOT / name) != value]
    result = {'status': 'failed' if changed else 'passed', 'files': len(values), 'changed': changed}
    with (AUDIT / ('protected-' + mode + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True)
    print(json.dumps(result))
    if changed:
        raise SystemExit(2)
