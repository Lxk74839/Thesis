"""Hash-only protection: never parses private answers or regenerates source data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/evidence-forensics-audit/20261016'


def fingerprint(file):
    with file.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': file.stat().st_size, 'sha256': digest}


mode = sys.argv[1]
before = AUDIT / 'upstream-before.json'
if mode == 'before':
    paths = {ROOT / p for p in subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', 'ac49059'], cwd=ROOT, text=True).splitlines()}
    paths.update(p for directory in ('data', 'sources', 'manuscript', 'research')
                 for p in (ROOT / directory).rglob('*') if p.is_file() and not p.is_relative_to(AUDIT))
    result = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in sorted(paths)}
    with before.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True)
    print(json.dumps({'status': 'protected', 'files': len(result), 'bytes': sum(v['bytes'] for v in result.values())}))
else:
    expected = json.loads(before.read_bytes())
    changed = [p for p, value in expected.items() if not (ROOT / p).is_file() or fingerprint(ROOT / p) != value]
    result = {'status': 'passed' if not changed else 'failed', 'files': len(expected), 'changed': changed}
    with (AUDIT / ('upstream-' + mode + '.json')).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True)
    print(json.dumps(result))
    if changed:
        raise SystemExit(2)
