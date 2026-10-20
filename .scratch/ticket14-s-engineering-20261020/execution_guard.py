"""New separately authorized 360s execution domain; old offline ledger stays linked."""
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
ledger = PACKAGE / 'execution-resources.jsonl'
if ledger.exists() or (PACKAGE / 'execution-claim.json').exists():
    raise SystemExit('S_execution_domain_already_consumed')
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
    with (PACKAGE / 'execution.stdout').open('xb') as output:
        child = subprocess.Popen([sys.executable, '-B', str(PACKAGE / 'run_once.py'), sys.argv[1]],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT)
        if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
            child.terminate()
            child.wait()
            raise ctypes.WinError(ctypes.get_last_error())
        child.stdin.write(b'GO\n')
        child.stdin.close()
        while child.poll() is None:
            if time.perf_counter() - START >= 360 or output.tell() > 1024**2:
                kernel.TerminateJobObject(job, 124)
                break
            time.sleep(.025)
        code = child.wait()
finally:
    kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
    accounting = existing.Accounting()
    kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
    kernel.CloseHandle(job)
    elapsed = time.perf_counter() - START
    row = {'scope': 'new_S_execution_only', 'seconds': elapsed, 'limit_seconds': 360,
        'offline_seconds_linked': offline, 'combined_seconds': offline + elapsed, 'exit_code': code,
        'job_peak_commit_bytes': info.job_peak, 'memory_limit_bytes': 4 * 1024**3,
        'job_read_transfer_bytes': accounting.io.read_bytes, 'job_write_transfer_bytes': accounting.io.write_bytes,
        'historical_spending_not_reclassified': True}
    with ledger.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(row) + '\n')
    print(json.dumps(row))
raise SystemExit(code)
