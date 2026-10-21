"""Explicit S attempts share 1800 seconds including termination and closeout."""
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
if attempt not in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6'):
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
if attempt == 'A3':
    ready = json.loads((PACKAGE / 'A3-ready.json').read_bytes())
    if (ready.get('candidate') != sys.argv[1] or ready.get('authorization_id') != LONG_AUTHORIZATIONS[2]
            or any(ready.get(axis) != 'PASS' for axis in ('standards', 'spec', 'PUBLIC_complete_S', 'D1_preflight'))):
        raise SystemExit('A3_not_ready')
used = execution_used(PACKAGE)
remaining = 1800 - used
if attempt == 'A4':
    ready = json.loads((PACKAGE / 'A4-ready.json').read_bytes())
    public = json.loads((ROOT / '.scratch/ticket14-s-a4-20261021/PUBLIC/execution-result.json').read_bytes())
    if (ready.get('candidate') != sys.argv[1] or ready.get('authorization_id') != LONG_AUTHORIZATIONS[3]
            or any(ready.get(axis) != 'PASS' for axis in ('standards', 'spec', 'PUBLIC_complete_S', 'D1_preflight'))
            or public.get('status') != 'passed' or public.get('candidate') != sys.argv[1]):
        raise SystemExit('A4_not_ready')
    remaining = min(remaining, 1753.612)
if attempt == 'A3':
    remaining = min(remaining, 1769.082)
if attempt in ('A5', 'A6'):
    ready = json.loads((PACKAGE / (attempt + '-ready.json')).read_bytes())
    if (ready.get('candidate') != sys.argv[1] or ready.get('authorization_id') != LONG_AUTHORIZATIONS[int(attempt[-1]) - 1]
            or any(ready.get(axis) != 'PASS' for axis in ('standards', 'spec', 'D1_preflight', 'send_chain', 'limits_regression'))
            or attempt == 'A6' and ready.get('dispatch_checkpoint') != 'PASS'
            or type(ready.get('execution_write_limit_bytes')) is not int
            or ready['execution_write_limit_bytes'] < 72 * 1024**2):
        raise SystemExit(attempt + '_not_ready')
    remaining = min(remaining, 1663.8197406 if attempt == 'A6' else 1709.869625500054)
rows = requests(SHARED / 'requests.jsonl')
call_limit, cap_limit = (20, 157148) if attempt == 'A6' else (17, 132572) if attempt == 'A5' else (12, 98304)
if remaining < 165 or len(rows) > call_limit - 2 or sum(r['output_cap'] for r in rows) > cap_limit - 9692:
    raise SystemExit('cumulative_S_balance_insufficient')
CONTROL.mkdir(exist_ok=True)
cfg = json.loads((ROOT / '.scratch/ticket14-s-deadline-20261020/s.config.json').read_bytes())
cfg['authorization_id'] = LONG_AUTHORIZATIONS[int(attempt[-1]) - 1]
cfg['model_binding']['engineering_authorization'] = cfg['authorization_id']
cfg['limits']['S'].update(model_calls=call_limit-len(rows), request_output_tokens=cap_limit-sum(r['output_cap'] for r in rows),
    elapsed_ms=min(1780000, int((remaining-20)*1000)))
if attempt == 'A3':
    cfg['limits']['S']['model_calls'] = min(cfg['limits']['S']['model_calls'], 10)
    cfg['limits']['S']['request_output_tokens'] = min(cfg['limits']['S']['request_output_tokens'], 81920)
if attempt == 'A4':
    cfg['limits']['S']['model_calls'] = min(cfg['limits']['S']['model_calls'], 9)
    cfg['limits']['S']['request_output_tokens'] = min(cfg['limits']['S']['request_output_tokens'], 73728)
if attempt in ('A5', 'A6'):
    cfg['limits']['S']['model_calls'] = min(cfg['limits']['S']['model_calls'], 12)
    cfg['limits']['S']['request_output_tokens'] = min(cfg['limits']['S']['request_output_tokens'], 91612)
    cfg['storage_limit_bytes'] = 128 * 1024**2
    cfg['run_storage_limit_bytes'] = 64 * 1024**2
cfg['final_reserve']['S']['elapsed_ms'] = 145000
ensure_first_execution(CONTROL, p1.OUTPUT / RUN_ID / 'attempt.json')
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
            accounting = existing.Accounting()
            kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
            if (time.perf_counter() - START >= remaining - 10 or output.tell() > 1024**2
                    or attempt in ('A5', 'A6') and accounting.io.write_bytes > ready['execution_write_limit_bytes']):
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
