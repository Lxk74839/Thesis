"""Thesis-only Windows Job guard; all runtime Python runs share this ledger."""
import time

START = time.perf_counter()

import ctypes
from ctypes import wintypes
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261018-batch'
LIMIT = 1800
RESERVE = 64 * 1024**2


class Basic(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_work', ctypes.c_size_t), ('max_work', ctypes.c_size_t),
                ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]


class IO(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]


class Extended(ctypes.Structure):
    _fields_ = [('basic', Basic), ('io', IO), ('process_limit', ctypes.c_size_t),
                ('job_limit', ctypes.c_size_t), ('process_peak', ctypes.c_size_t), ('job_peak', ctypes.c_size_t)]


def main():
    assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
    assert sys.version_info[:3] == (3, 13, 16)
    AUDIT.mkdir(parents=True, exist_ok=True)
    ledger = AUDIT / 'resource-ledger.jsonl'
    inflight = AUDIT / 'resource-inflight.json'
    if inflight.exists():
        raise SystemExit('runtime_resource_usage_unresolved_no_new_work')
    used = sum(json.loads(row)['seconds'] for row in ledger.read_text().splitlines()) if ledger.exists() else 0
    if used + time.perf_counter() - START >= LIMIT:
        raise SystemExit('runtime_compute_limit_exhausted')
    label = sys.argv[1]
    source_paths = ('recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
                    'tests/test_batched_recommendation.py')
    source_sha256 = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    output = AUDIT / (label + '.txt')
    with inflight.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'label': label, 'guard_pid': os.getpid(), 'started_at_unix': time.time(),
                   'seconds': None, 'known_cumulative_seconds': used,
                   'unsettled_allowance_seconds': LIMIT - used}, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
    kernel.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    job = kernel.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x200 | 0x2000
    info.job_limit = 4 * 1024**3 - RESERVE
    code = 2
    try:
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', THESIS_BATCH_CHECK_LABEL=label)
        with output.open('xb') as stream:
            child = subprocess.Popen([sys.executable, '-B', *sys.argv[2:]], cwd=ROOT,
                                     stdout=stream, stderr=subprocess.STDOUT, env=env)
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
                child.terminate()
                child.wait()
                raise ctypes.WinError(ctypes.get_last_error())
            while child.poll() is None:
                if used + time.perf_counter() - START >= LIMIT:
                    kernel.TerminateJobObject(job, 3)
                    break
                time.sleep(.025)
            code = child.wait()
    finally:
        kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
        kernel.CloseHandle(job)
        seconds = time.perf_counter() - START
        row = {'label': label, 'seconds': seconds, 'cumulative_seconds': used + seconds,
               'exit_code': code, 'job_peak_commit_bytes': info.job_peak,
               'guard_reserve_bytes': RESERVE, 'limit_bytes': 4 * 1024**3, 'limit_seconds': LIMIT,
               'accounting': 'guard_start_to_child_completion_wall_time_including_failures',
               'guard': 'Windows_Job_tree_limit_plus_64MiB_guard_reserve', 'source_sha256': source_sha256,
               'source_changed_during_check': [p for p, sha in source_sha256.items()
                   if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha]}
        with ledger.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        inflight.unlink()
    if output.exists():
        print(output.read_text(encoding='utf-8'), end='')
    print(json.dumps(row, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
