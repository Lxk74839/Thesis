"""Reuse the accepted Windows Job guard with a separate ticket14 resource ledger."""
import hashlib
import json
import subprocess
import sys
import run_joint13_check as guard

guard.AUDIT = guard.ROOT / '.scratch/data-preparation/verification/ticket14-20261016'

if __name__ == '__main__':
    code = guard.main()
    if code == 0 and sys.argv[1] == '06-final-protection':
        rows = [json.loads(line) for line in (guard.AUDIT / 'resource-ledger.jsonl').read_text().splitlines()]
        artifacts = []
        paths = list(guard.AUDIT.iterdir())
        paths += list((guard.ROOT / '.scratch/data-preparation/diagnostics').glob('ticket14_*.py'))
        paths += [guard.ROOT / '.scratch/data-preparation/diagnostics/run_ticket14_check.py',
                  guard.ROOT / '.scratch/data-preparation/ticket14-full-data-acceptance-and-sufficiency-20261016.md']
        for path in sorted(paths):
            if path.is_file() and path.name != 'final-delivery-evidence.json':
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                artifacts.append({'path': path.relative_to(guard.ROOT).as_posix(),
                                  'bytes': path.stat().st_size, 'sha256': digest})
        result = {'baseline': '3c565eb9fd5e4240bbcc214111655ca394a0a3a8',
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=guard.ROOT, text=True).strip(),
            'status': 'data_integrity_association_isolation_passed',
            'n8': 1111, 'nQ': 1283, 'planning_required': 975, 'sample_sufficiency': 'not_determined',
            'actual_precision': 'not_determined', 'formal_package_status': 'not_released',
            'resources': {'runs': len(rows), 'cumulative_seconds': sum(r['seconds'] for r in rows),
              'job_peak_commit_bytes': max(r['job_peak_commit_bytes'] for r in rows),
              'guard_reserve_bytes': 64 * 1024**2, 'limit_seconds': 1800, 'limit_bytes': 4 * 1024**3,
              'nonzero_exits': sum(r['exit_code'] != 0 for r in rows),
              'guard': 'accepted_Windows_Job_guard_with_ticket14_separate_ledger',
              'accounting': 'child_process_tree_wall_seconds_including_failed_attempts; parent_bookkeeping_64MiB_reserve'},
            'artifacts': artifacts, 'self_digest': 'excluded_to_avoid_self_reference'}
        with (guard.AUDIT / 'final-delivery-evidence.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write('\n')
        print(json.dumps({'final_resources': result['resources'], 'bound_delivery_artifacts': len(artifacts)}))
    raise SystemExit(code)
