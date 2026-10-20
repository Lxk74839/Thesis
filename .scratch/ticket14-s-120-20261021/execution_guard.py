"""Two S attempts share 1800 seconds including termination and closeout."""
import time
START = time.perf_counter()
import ctypes
from ctypes import wintypes
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
if Path(sys.prefix).resolve() != ROOT / '.conda/envs/Thesis':
    raise SystemExit('Thesis_environment_required')
spec = importlib.util.spec_from_file_location('existing_job_guard', ROOT / '.scratch/ticket12-budget-20261018/diagnostics/run_check.py')
existing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(existing)
ledger = PACKAGE / sys.argv[2] / 'execution-resources.jsonl'
from run_once import ensure_first_execution, p1, SHARED
from p1_engineering import LONG_AUTHORIZATIONS
from control import requests, execution_used
attempt = sys.argv[2]
if attempt not in ('A1', 'A2'):
    raise SystemExit('invalid_attempt')
CONTROL = PACKAGE / attempt
RUN_ID = 'P1-D1-V00-S-' + LONG_AUTHORIZATIONS[int(attempt[-1]) - 1]
if attempt == 'A2':
    first = json.loads((PACKAGE / 'A1/execution-result.json').read_bytes())
    last = first['responses'][-1]
    ready = json.loads((PACKAGE / 'A2-ready.json').read_bytes())
    if (first['terminal'] != 'failed_model' or last.get('http_status') != 200
            or last.get('returned_model') != 'gpt-6-luna' or last.get('deadline_diagnostic')
            or (last.get('protocol_diagnostic') or {}).get('stage') not in ('output_item', 'tool_call', 'json_decode', 'role_schema')
            or ready.get('candidate') != sys.argv[1] or ready.get('standards') != 'PASS' or ready.get('spec') != 'PASS'):
        raise SystemExit('second_attempt_not_eligible')
used = execution_used(PACKAGE)
remaining = 1800 - used
rows = requests(SHARED / 'requests.jsonl')
if remaining < 165 or len(rows) > 10 or sum(r['output_cap'] for r in rows) > 98304 - 9692:
    raise SystemExit('cumulative_S_balance_insufficient')
CONTROL.mkdir(exist_ok=True)
cfg = json.loads((ROOT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
cfg['authorization_id'] = LONG_AUTHORIZATIONS[int(attempt[-1]) - 1]
cfg['model_binding']['engineering_authorization'] = cfg['authorization_id']
cfg['limits']['S'].update(model_calls=12-len(rows), request_output_tokens=98304-sum(r['output_cap'] for r in rows),
    elapsed_ms=min(1780000, int((remaining-20)*1000)))
cfg['final_reserve']['S']['elapsed_ms'] = 145000
with (CONTROL / 's.config.json').open('x', encoding='utf-8') as stream:
    json.dump(cfg, stream, indent=2)
ensure_first_execution(CONTROL, p1.OUTPUT / RUN_ID / 'attempt.json')
offline = json.loads((ROOT / 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl').read_text().splitlines()[-1])['cumulative_seconds']
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateJobObjectW.restype = wintypes.HANDLE
kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
kernel.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
job = kernel.CreateJobObjectW(None, None)
info = existing.Extended()
info.basic.flags = 0x200 | 0x2000
info.job_limit = 4 * 1024**3 - existing.RESERVE
code = 2
try:
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    with (CONTROL / 'execution.stdout').open('xb') as output:
        child = subprocess.Popen([sys.executable, '-B', str(PACKAGE / 'run_once.py'), sys.argv[1], attempt],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT)
        if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
            child.terminate()
            child.wait()
            raise ctypes.WinError(ctypes.get_last_error())
        child.stdin.write(b'GO\n')
        child.stdin.close()
        while child.poll() is None:
            if time.perf_counter() - START >= remaining - 10 or output.tell() > 1024**2:
                kernel.TerminateJobObject(job, 124)
                break
            time.sleep(.025)
        code = child.wait(timeout=5)
finally:
    kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
    accounting = existing.Accounting()
    kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
    kernel.CloseHandle(job)
    elapsed = time.perf_counter() - START
    row = {'scope': 'new_S_120_shared_execution_only', 'seconds': elapsed, 'limit_seconds': remaining, 'cumulative_execution_seconds': used + elapsed, 'cumulative_execution_limit_seconds': 1800,
        'offline_seconds_linked': offline, 'combined_seconds': offline + elapsed, 'exit_code': code,
        'job_peak_commit_bytes': info.job_peak, 'memory_limit_bytes': 4 * 1024**3,
        'job_read_transfer_bytes': accounting.io.read_bytes, 'job_write_transfer_bytes': accounting.io.write_bytes,
        'historical_spending_not_reclassified': True}
    with ledger.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(row) + '\n')
    print(json.dumps(row))
raise SystemExit(code)
