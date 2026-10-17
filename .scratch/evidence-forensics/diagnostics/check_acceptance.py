"""Independent artifact checks; no production imports, private answers, or new facts in A."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/evidence-forensics-audit/20261016'
BASE = 'ac49059ffa1f61545033b84f688eee4be58d75be'
candidate, probe_name, guard_label = sys.argv[1:]


def fingerprint(path):
    with path.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': value}


def load(path):
    return json.loads(path.read_bytes())


def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=ROOT)


assert git('merge-base', BASE, candidate).decode().strip() == BASE
for name, size, sha in (
    ('spec.md', 30868, 'c3bda58c6450d434dcc7033dd051571543aea7737c5eaa17e021d411a800fb95'),
    ('confirmation.md', 3121, 'b0aa6e88eb184857e3d07749bc06643c580522dbbc9158137828bfd293b529eb')):
    item = fingerprint(ROOT / '.scratch/evidence-forensics' / name)
    assert (item['bytes'], item['sha256']) == (size, sha)
allowed = {'evidence_access.py', 'evidence_verification.py', 'tests/evidence_fixtures.py',
           'tests/test_evidence_access.py', 'tests/test_evidence_verification.py'}
for line in git('diff', '--name-status', BASE).decode().splitlines():
    status, path = line.split('\t')
    assert status == 'A' and (path in allowed or path.startswith('.scratch/evidence-forensics/'))
for path in git('ls-files', '--others', '--exclude-standard').decode().splitlines():
    assert path in allowed or path.startswith('.scratch/evidence-forensics/')
protected = load(AUDIT / 'upstream-after.json')
assert protected == {'status': 'passed', 'files': 1819, 'changed': []}
reviews = []
for axis in ('standards', 'spec'):
    path = ROOT / '.scratch/evidence-forensics/verification' / (axis + '-r2.md')
    text = path.read_text(encoding='utf-8')
    assert BASE in text and candidate in text and 'Blocking: 0' in text
    reviews.append({'axis': axis, 'report': fingerprint(path), 'blocking': 0})
tests = AUDIT / '87-final-public-and-impact-regression.txt'
assert 'Ran 43 tests' in tests.read_text(encoding='utf-8') and '\nOK\n' in tests.read_text(encoding='utf-8')
guard_check = (AUDIT / '70-guard-interruption-green.txt').read_text(encoding='utf-8')
assert '"second_child_started": false' in guard_check and '"unresolved_reservation_preserved": true' in guard_check
probe = load(AUDIT / probe_name / 'probe-summary.json')
assert probe['status'] == 'passed' and probe['execution']['candidate_commit'] == candidate
assert [row['label_admin_only'] for row in probe['sources']] == ['V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2']
assert len({(row['root'], row['candidate']) for row in probe['sources']}) == 1
for item in probe['execution']['files']:
    assert fingerprint(ROOT / item['path']) == item
    committed = git('show', candidate + ':' + item['path'])
    assert hashlib.sha256(committed).hexdigest() == item['sha256']
fact_names = {'snapshot.json', 'policy.json', 'registrations.jsonl', 'batches.jsonl', 'events.jsonl',
              'materials.jsonl', 'actions.jsonl', 'change-actions.jsonl'}
sources = []
for row in probe['sources']:
    assert row['independent']['byte_offsets_and_sha256'] == row['independent']['receipt_conservation'] == 'passed'
    reference = row['actual_A']
    assert fingerprint(ROOT / reference['path']) == reference
    audit = load(ROOT / reference['path'])
    assert audit['probe_execution'] == probe['execution'] and not audit['unsettled_reservations']
    assert audit['usage']['logical_tools'] == 67 and audit['usage']['physical_tools'] == 2
    assert audit['usage']['candidates'] == 1 and audit['usage']['retries'] == 0
    receipts = {entry['receipt_id']: entry for entry in audit['receipts']}
    assert len(receipts) == len(audit['receipts'])
    for dimension in ('logical_tools', 'physical_tools'):
        assert sum(entry['usage_delta'][dimension] for entry in receipts.values()) == audit['usage'][dimension]
    for receipt in receipts.values():
        assert not receipt['late'] and receipt['usage_exact'] and not receipt['reservation']['unresolved']
        for dimension, amount in receipt['reservation']['held'].items():
            assert amount == receipt['reservation']['settled'][dimension] + receipt['reservation']['released'][dimension]
    pack = audit['acquired']['candidates'][row['candidate']]
    assert len(pack['registrations']) == len(pack['originals']) == 15
    registered = {entry['evidence_ref'] for entry in pack['registrations']}
    assert set(pack['originals']) <= registered
    for item in pack['originals'].values():
        assert item['receipt_id'] in receipts and item['status'] == 'ok'
        assert item['sha256'] == hashlib.sha256(item['raw_utf8'].encode()).hexdigest()
    for item in row['assessment']['accepted']:
        original = pack['originals'][item['evidence_ref']]
        assert item['receipt_id'] == original['receipt_id'] and item['source'] == original['source']
    assert all(Path(origin['component_path']).name in fact_names for origin in audit['provenance'].values())
    sources.append({'label_admin_only': row['label_admin_only'], 'actual_A': reference,
                    'independent_provenance_and_metering': 'passed'})
ledger = [json.loads(line) for line in (AUDIT / 'resource-ledger.jsonl').read_text().splitlines()]
assert sum(row['seconds'] for row in ledger) < 1800
assert max(row['job_peak_commit_bytes'] + row['guard_reserve_bytes'] for row in ledger) <= 4 * 1024**3
pending = load(AUDIT / 'resource-inflight.json')
assert pending['label'] == guard_label and pending['guard_pid'] == os.getppid()
result = {'status': 'passed', 'base': BASE, 'candidate': candidate, 'reviews': reviews,
    'tests': {'count': 43, 'evidence': fingerprint(tests)}, 'source_checks': sources,
    'protection': fingerprint(AUDIT / 'upstream-after.json'),
    'resource_checkpoint_before_this_check': {'runs': len(ledger), 'seconds': sum(row['seconds'] for row in ledger)},
    'current_guard_settlement': 'pending outer guard completion; final delivery binds the completed ledger',
    'no_producer_imports_or_private_answers': True}
with (AUDIT / 'acceptance-check.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, sort_keys=True)
    stream.write('\n')
print(json.dumps({'status': 'passed', 'sources': len(sources), 'tests': 43,
                  'resource_checkpoint_seconds': result['resource_checkpoint_before_this_check']['seconds']}))
