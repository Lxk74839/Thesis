"""Retain the final Spec blocker at S1/S2, without modifying production code."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / '.scratch/data-preparation/verification'


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw(value) + b'\n')


def run(arguments, name):
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True)
    with (EVIDENCE / name).open('xb') as stream:
        stream.write(result.stdout + result.stderr)
    return result


def main():
    if Path(sys.prefix).resolve() != (ROOT / '.conda/envs/Thesis').resolve():
        raise SystemExit('Thesis environment required')
    work = Path(tempfile.mkdtemp(prefix='ticket10-final-blocker-', dir=ROOT / '.tmp'))
    inputs, output, audit = work / 'inputs', work / 'generated', work / 'audit'
    parent = {'parent_asin': 'DEMO-P001', 'crop': 'rice', 'status': 'included', 'metadata': {}}
    catalog_path = inputs / 'catalog.jsonl'
    put(catalog_path, parent)
    catalog_record = inputs / 'catalog-record.json'
    put(catalog_record, {'stage': 'catalog', 'status': 'catalog_complete', 'scope_version': 'grain-A-1.1.15',
        'counts': {'included': 1}, 'catalog_path': catalog_path.relative_to(ROOT).as_posix(),
        'catalog_sha256': sha(catalog_path.read_bytes())})
    config = json.loads((ROOT / 'config/sim-normal-1.0.0.json').read_bytes())
    config['catalog_binding'].update(record_path=catalog_record.relative_to(ROOT).as_posix(),
        record_sha256=sha(catalog_record.read_bytes()), component_sha256=sha(catalog_path.read_bytes()), expected_parent_count=1)
    config_path = inputs / 'config.json'
    put(config_path, config)
    generated = run(['prepare_data.py', '--stage', 'sim_normal', '--catalog-record', str(catalog_record),
        '--sim-config', str(config_path), '--output-root', str(output)], 'ticket10-remaining-blocker-s1.txt')
    if generated.returncode:
        raise SystemExit('Fixture generation failed')
    record = json.loads(generated.stdout)
    record_path = output / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
    snapshot_path = output / record['components']['snapshot.json']['path']
    snapshot = json.loads(snapshot_path.read_bytes())
    record['components']['policy.json']['records'] = True
    snapshot['components']['policy.json']['records'] = True
    del snapshot['snapshot_id']
    snapshot['snapshot_id'] = 'n_' + sha(b'Thesis-SIM-1:snapshot\0' + raw(snapshot))
    # Only the controlled fixture's envelopes are changed; raw business originals remain untouched.
    snapshot_path.write_bytes(raw(snapshot) + b'\n')
    record['snapshot_id'] = snapshot['snapshot_id']
    record['components']['snapshot.json'].update(sha256=sha(snapshot_path.read_bytes()), bytes=snapshot_path.stat().st_size)
    record_path.write_bytes(raw(record) + b'\n')
    checked = run(['.scratch/data-preparation/diagnostics/verify_sim10.py', '--record', str(record_path),
                   '--audit-root', str(audit)], 'ticket10-remaining-blocker-s2.txt')
    check = json.loads((audit / 'check.json').read_bytes())
    proof = {'status': 'confirmed_blocker' if checked.returncode == 0 and check['status'] == 'passed' else 'not_reproduced',
        'candidate_sha': '2d3953b6223c33b694a26cbc7d86618d72bd8f0f',
        'contract': 'ticket10 confirmation sections 2.4 / 5.3 / A3: records must be integer, never boolean',
        'fixture_parents': 1, 'fixture_root': work.relative_to(ROOT).as_posix(),
        'mutation': {'record_and_snapshot_policy_records': True}, 'expected_s2_exit': 2,
        'actual_s2_exit': checked.returncode, 'actual_check_status': check['status'],
        'check_path': (audit / 'check.json').relative_to(ROOT).as_posix(), 'check_sha256': sha((audit / 'check.json').read_bytes()),
        'record_path': record_path.relative_to(ROOT).as_posix(), 'record_sha256': sha(record_path.read_bytes()),
        'snapshot_sha256': sha(snapshot_path.read_bytes()), 'production_modified': False,
        'runtime': {'conda_prefix': sys.prefix, 'at_utc': datetime.now(timezone.utc).isoformat()}}
    put(EVIDENCE / 'ticket10-remaining-blocker-proof.json', proof)
    print(json.dumps({'status': proof['status'], 'actual_s2_exit': checked.returncode,
                      'actual_check_status': check['status'], 'fixture_root': proof['fixture_root']}))
    return 0 if proof['status'] == 'confirmed_blocker' else 2


if __name__ == '__main__':
    raise SystemExit(main())
