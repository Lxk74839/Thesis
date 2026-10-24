"""Record an as-of resource ledger from the stopped controller; no dispatch."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
PROJECT = AUDIT.parents[2]
OUTPUT = PROJECT/'data/recommendation-runtime-audit/macrec-agri-dev-task16'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


state, start = read(AUDIT/'closing-status.json'), read(AUDIT/'pre-start-status.json')
budget = read(OUTPUT/'budget.json')
summary = read(AUDIT/'result-summary.json')
assert state['status']=='paused' and not state['worker_active']
assert state['calls']['attempts']==89 and summary['audited_unknown_send']==1
assert not any(read(p).get('end') is None for p in (OUTPUT/'activity').glob('development-*.json'))
epoch = datetime.fromisoformat(budget['started_at_utc']).timestamp()+state['timing']['total_seconds']
at = datetime.fromtimestamp(epoch,timezone.utc)
ledger = {'as_of_utc':at.isoformat(),'as_of_JST':at.astimezone(timezone(timedelta(hours=9))).isoformat(),
    'status':'paused_protocol_gap_and_uncertain_send','worker_active':False,
    'budget_sha256':hashlib.sha256((OUTPUT/'budget.json').read_bytes()).hexdigest(),
    'original_started_at_utc':budget['started_at_utc'],
    'original_dispatch_deadline_utc':budget['dispatch_deadline_utc'],
    'original_total_deadline_utc':budget['deadline_utc'],
    'dispatch_seconds_remaining':datetime.fromisoformat(budget['dispatch_deadline_utc']).timestamp()-epoch,
    'total_seconds_remaining':datetime.fromisoformat(budget['deadline_utc']).timestamp()-epoch,
    'cumulative_physical_call_limit':1504,'cumulative_physical_attempts':state['calls']['attempts'],
    'this_version_physical_attempts':state['calls']['attempts']-start['calls']['attempts'],
    'recorded_control_counts':state['calls'],'audited_unresolved_send_requests':1,
    'unknown_send_do_not_resend':read(OUTPUT/'protocol-bindings/macrec-agri-v2/uncertain-send-audit.json'),
    'usage_cumulative':state['usage'],'known_usage_this_version':summary['known_usage_this_version'],
    'cost':summary['cost'],'timing_cumulative_seconds':state['timing'],
    'timing_since_pre_start_seconds':{k:state['timing'][k]-start['timing'][k] for k in state['timing']},
    'v2_supervision':read(OUTPUT/'supervisions/ce2255596b524880b2bc36ce6aa1e775.worker.json'),
    'new_bytes_cumulative':state['new_bytes'],'new_GiB_cumulative':state['new_bytes']/1024**3,
    'growth_bytes_since_pre_start':state['new_bytes']-start['new_bytes'],
    'max_new_bytes':budget['max_new_bytes'],'space_snapshot_note':'controller includes original scoped artifacts and shared .git/.tmp growth; files written after as_of are outside this snapshot',
    'development_intervals_closed':True,'waiting_excluded_from_total':False,
    'algorithm_main_completed':False,'later_experiments_executed':False}
(AUDIT/'closing-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(ledger,ensure_ascii=False))
