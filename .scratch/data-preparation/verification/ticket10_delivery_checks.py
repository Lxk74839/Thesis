"""Internal evidence harness: all generation remains at prepare_data.py's S1 seam."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[3]
EVIDENCE = PROJECT / '.scratch/data-preparation/verification'
RECORD = PROJECT / 'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
REFERENCE = PROJECT / 'data/sim-reference/grain-A-1.1.15/sim-normal-1.0.0/r1-reference-1.0.0/reference-r1.jsonl'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def info(path):
    return {'path': path.relative_to(PROJECT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def execute(arguments, log):
    command = [sys.executable, *arguments]
    result = subprocess.run(command, cwd=PROJECT, capture_output=True)
    with log.open('xb') as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('external_command_failed:' + log.name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['regression', 'reproduction', 'protection'], required=True)
    args = parser.parse_args()
    if Path(sys.prefix).resolve() != (PROJECT / '.conda/envs/Thesis').resolve():
        raise SystemExit('Thesis environment required')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    result = {'phase': args.phase, 'status': 'failed', 'git_head_sha': head,
              'program': info(Path(__file__)), 'runtime': {'conda_prefix': sys.prefix,
              'python_version': platform.python_version(), 'at_utc': datetime.now(timezone.utc).isoformat()}}
    suffix = head[:8]
    report = EVIDENCE / f'ticket10-{args.phase}-{suffix}.json'
    try:
        if args.phase == 'regression':
            log = EVIDENCE / f'ticket10-regression-{suffix}.txt'
            run = execute(['-m', 'unittest', 'discover', '-s', 'tests', '-v'], log)
            output = (run.stdout + run.stderr).decode('utf-8')
            import re
            count = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
            if not count or not output.rstrip().endswith('OK'):
                raise ValueError('regression_result_missing')
            result.update(tests=int(count[1]), seconds=float(count[2]), log=info(log),
                          command=[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        elif args.phase == 'reproduction':
            before_record = RECORD.read_bytes()
            record = json.loads(before_record)
            fresh = Path(tempfile.mkdtemp(prefix='ticket10-fresh-', dir=PROJECT / '.tmp'))
            common = ['prepare_data.py', '--stage', 'sim_normal', '--catalog-record', 'records/catalog/grain-A-1.1.15.json',
                      '--sim-config', 'config/sim-normal-1.0.0.json', '--output-root']
            generated = execute([*common, str(fresh)], EVIDENCE / 'ticket10-reproduction-cli.txt')
            new_record = json.loads(generated.stdout)
            audit_root = fresh / 'private-reference'
            fresh_record = fresh / RECORD.relative_to(PROJECT)
            execute(['.scratch/data-preparation/diagnostics/verify_sim10.py', '--record', str(fresh_record), '--audit-root', str(audit_root)],
                    EVIDENCE / 'ticket10-reproduction-audit.txt')
            compared = {}
            for name, component in record['components'].items():
                original_path = PROJECT / component['path']
                new_path = fresh / component['path']
                same = original_path.read_bytes() == new_path.read_bytes()
                compared[name] = {'sha256': sha(original_path), 'reproduction_sha256': sha(new_path), 'equal': same,
                                  'bytes': original_path.stat().st_size}
                if not same:
                    raise ValueError('reproduction_component:' + name)
            if record['snapshot_id'] != new_record['snapshot_id'] or REFERENCE.read_bytes() != (audit_root / 'reference-r1.jsonl').read_bytes():
                raise ValueError('reproduction_reference_or_snapshot')
            reused = execute([*common, '.'], EVIDENCE / 'ticket10-reuse-cli.txt')
            if json.loads(reused.stdout) != record or RECORD.read_bytes() != before_record:
                raise ValueError('reuse_record_changed')
            result.update(fresh_root=fresh.relative_to(PROJECT).as_posix(), components=compared,
                          snapshot_id=record['snapshot_id'], reference_sha256=sha(REFERENCE),
                          reproduced_reference_sha256=sha(audit_root / 'reference-r1.jsonl'),
                          fresh_check=info(audit_root / 'check.json'), generation_record=info(RECORD),
                          reused_record_bytes_unchanged=True, counts=record['counts'])
        else:
            before_path = EVIDENCE / 'ticket10-protection-before.json'
            before = json.loads(before_path.read_bytes())
            changed, unchanged, authorized = [], 0, []
            for name, expected in before['files'].items():
                path = Path(name)
                if path.exists() and sha(path) == expected['sha256'] and path.stat().st_size == expected['bytes']:
                    unchanged += 1
                elif path == PROJECT / '.gitattributes':
                    old = subprocess.check_output(['git', 'show', 'd277137:.gitattributes'], cwd=PROJECT).decode('utf-8').splitlines()
                    current = path.read_text(encoding='utf-8').splitlines()
                    if current[:len(old)] != old or not current[len(old)].startswith('# Ticket 10 new sources'):
                        changed.append(name)
                    else:
                        authorized.append({'path': '.gitattributes', 'before_sha256': expected['sha256'],
                                           'after_sha256': sha(path), 'reason': 'append byte attributes for new ticket10 files only'})
                else:
                    changed.append(name)
            if changed:
                result['changed_protected_files'] = changed
                raise ValueError('upstream_protection_failed')
            result.update(before_manifest=info(before_path), protected_files=len(before['files']),
                          byte_unchanged_files=unchanged, authorized_archival_changes=authorized, changed_protected_files=[])
            followup_path = EVIDENCE / 'ticket10-integer-protection-before.json'
            followup = json.loads(followup_path.read_bytes())
            followup_changed = [name for name, expected in followup['files'].items()
                                if not Path(name).is_file() or sha(Path(name)) != expected['sha256']
                                or Path(name).stat().st_size != expected['bytes']]
            result.update(followup_before_manifest=info(followup_path),
                          followup_protected_files=len(followup['files']), followup_changed_files=followup_changed)
            if followup_changed:
                raise ValueError('followup_history_protection_failed')
        result['status'] = 'passed'
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result['error'] = str(exc)
    save(report, result)
    print(json.dumps({'phase': args.phase, 'status': result['status'], 'report': report.relative_to(PROJECT).as_posix()}))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
