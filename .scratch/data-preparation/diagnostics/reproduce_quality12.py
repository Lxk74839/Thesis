"""Empty-directory public CLI reproduction and byte-preserving same-root reuse."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'data/quality-fusion-audit/20261016'
RECORD=Path('records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    record_raw=(ROOT/RECORD).read_bytes();record=json.loads(record_raw)
    expected={info['path']:(ROOT/info['path']).read_bytes() for info in record['components'].values()}
    expected[RECORD.as_posix()]=record_raw
    stats={p:(ROOT/p).stat().st_mtime_ns for p in expected}
    fresh=Path(tempfile.mkdtemp(prefix='quality12-reproduction-',dir=ROOT/'.tmp'))
    if list(fresh.iterdir()):raise ValueError('not_empty')
    guard=ROOT/'.scratch/data-preparation/diagnostics/guard_quality12_prepare.py'
    commands=[('fresh',fresh),('reuse',ROOT)]
    for label,output in commands:
        result=subprocess.run([sys.executable,str(guard),'--output-root',str(output),'--label',label],
                              cwd=ROOT,capture_output=True)
        with (AUDIT/('reproduce-'+label+'.txt')).open('xb') as stream:stream.write(result.stdout+result.stderr)
        if result.returncode:raise ValueError(label+'_CLI_failed')
        if any((output/p).read_bytes()!=raw for p,raw in expected.items()):raise ValueError(label+'_byte_mismatch')
    if any((ROOT/p).stat().st_mtime_ns!=ns for p,ns in stats.items()):raise ValueError('reuse_wrote_existing_file')
    destination=ROOT/'data/sim-quality/grain-A-1.1.15/sim-quality-fusion-0.1.0'
    actual={p.relative_to(ROOT).as_posix() for p in destination.rglob('*') if p.is_file()}
    if actual!=set(expected)-{RECORD.as_posix()}:raise ValueError('unexpected_component_files')
    if (ROOT/RECORD).read_bytes()!=record_raw:raise ValueError('prepared_record_changed')
    summary={'status':'passed','fresh_directory':fresh.relative_to(ROOT).as_posix(),
        'component_files':len(record['components']),'total_files_including_prepared':len(expected),
        'verified_bytes':sum(map(len,expected.values())),'prepared_sha256':sha(record_raw),
        'reuse_bytes_and_mtime_unchanged':True,'empty_initial_directory':True,'model_API_calls':0}
    with (AUDIT/'reproduction-summary.json').open('xb') as stream:stream.write(json.dumps(summary,sort_keys=True).encode()+b'\n')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
