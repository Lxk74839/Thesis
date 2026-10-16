"""Ticket13 audit runner: Thesis Python, Windows job memory cap, shared time ledger."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/joint-audit/joint-task-package-0.1.0'


class Basic(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_work', ctypes.c_size_t), ('max_work', ctypes.c_size_t),
                ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]


class IO(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class Extended(ctypes.Structure):
    _fields_ = [('basic', Basic), ('io', IO), ('process_limit', ctypes.c_size_t),
                ('job_limit', ctypes.c_size_t), ('process_peak', ctypes.c_size_t), ('job_peak', ctypes.c_size_t)]


def main():
    AUDIT.mkdir(parents=True, exist_ok=True)
    ledger = AUDIT / 'resource-ledger.jsonl'
    used = sum(json.loads(line)['seconds'] for line in ledger.read_text().splitlines()) if ledger.exists() else 0
    label = sys.argv[1]
    if used >= 1800:
        raise RuntimeError('ticket13_total_compute_limit_exhausted')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
    kernel.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    info = Extended()
    info.basic.flags = 0x200 | 0x2000  # job memory limit; kill remaining children on close
    info.job_limit = 4 * 1024**3 - 64 * 1024**2
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    start = time.perf_counter()
    path = AUDIT / (label + '.txt')
    with path.open('xb') as output:
        process = subprocess.Popen([sys.executable] + sys.argv[2:], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle))):
            process.terminate()
            raise ctypes.WinError(ctypes.get_last_error())
        while process.poll() is None:
            if time.perf_counter() - start + used > 1800:
                kernel.TerminateJobObject(job, 3)
                break
            time.sleep(.05)
        code = process.wait()
    seconds = time.perf_counter() - start
    kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
    kernel.CloseHandle(job)
    result = {'label': label, 'seconds': seconds, 'cumulative_seconds': used + seconds,
              'exit_code': code, 'job_peak_commit_bytes': info.job_peak,
              'memory_limit_bytes': 4 * 1024**3, 'guard_reserve_bytes': 64 * 1024**2, 'guard': 'Windows_job_tree_memory_and_1800s_ledger'}
    with ledger.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(result, sort_keys=True) + '\n')
    print(path.read_text(encoding='utf-8'), end='')
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
