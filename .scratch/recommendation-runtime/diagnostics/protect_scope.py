"""Hash-only protection; no parsing of private research/evaluation content."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261017'
BASE = '6ac5c2cddde6973b9743e3e17f5c264840f42854'


def fingerprint(path):
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


mode = sys.argv[1]
before = AUDIT / 'upstream-before.json'
if mode == 'before':
    paths = {ROOT / name for name in subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()}
    paths.update(p for folder in ('data', 'sources', 'manuscript', 'research')
                 for p in (ROOT / folder).rglob('*') if p.is_file() and not p.is_relative_to(AUDIT))
    paths.update(ROOT / '.scratch/recommendation-runtime' / p for p in ('spec.md', 'confirmation.md'))
    paths.discard(ROOT / 'evidence_access.py')
    values = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in sorted(paths)}
    with before.open('x', encoding='utf-8') as stream:
        json.dump(values, stream, sort_keys=True, ensure_ascii=False)
    baseline = subprocess.check_output(['git', 'show', BASE + ':evidence_access.py'], cwd=ROOT)
    (AUDIT / 'evidence-access-baseline.py').write_bytes(baseline)
    print(json.dumps({'status': 'protected', 'files': len(values), 'bytes': sum(v['bytes'] for v in values.values())}))
else:
    values = json.loads(before.read_bytes())
    changed = [name for name, value in values.items() if not (ROOT / name).is_file() or fingerprint(ROOT / name) != value]
    result = {'status': 'passed' if not changed else 'failed', 'files': len(values), 'changed': changed}
    with (AUDIT / ('upstream-' + mode + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True)
    print(json.dumps(result))
    if changed:
        raise SystemExit(2)
