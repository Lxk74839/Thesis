"""Hash-only upstream protection. No source data values leave this local audit."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/quality-fusion-audit/20261016'


def fingerprint(path):
    with path.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': value}


def main():
    start = time.perf_counter()
    manifest = AUDIT / 'upstream-before.json'
    if sys.argv[1] == 'before':
        paths = [p for name in ('data','manuscript','research','records','config') for p in (ROOT/name).rglob('*') if p.is_file()]
        paths = [p for p in paths if not p.is_relative_to(AUDIT)]
        evidence = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in paths}
        with manifest.open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, sort_keys=True)
        print(json.dumps({'status':'upstream_snapshot_saved','files':len(evidence),'bytes':sum(v['bytes'] for v in evidence.values()),'seconds':time.perf_counter()-start}))
    else:
        evidence = json.loads(manifest.read_bytes())
        changed = [name for name, value in evidence.items() if not (ROOT/name).is_file() or fingerprint(ROOT/name) != value]
        result = {'status':'passed' if not changed else 'failed','checked_files':len(evidence),
                  'changed':changed,'seconds':time.perf_counter()-start}
        with (AUDIT/'upstream-after.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, sort_keys=True)
        print(json.dumps(result))
        if changed:
            raise SystemExit(2)


if __name__ == '__main__':
    main()
