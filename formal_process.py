"""Windows Job containment shared by formal task workers and their HTTP children."""
import ctypes
from ctypes import wintypes
import subprocess
import time


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


class Accounting(ctypes.Structure):
    _fields_ = [('times', ctypes.c_longlong * 4), ('counts', wintypes.DWORD * 4), ('io', IO)]


def run_process(command, stdout_path, *, cwd, seconds, memory_bytes):
    """Hold the worker at stdin until descendants are covered by kill-on-close."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
    kernel.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise OSError('formal_job_create')
    limits, accounting = Extended(), Accounting()
    limits.basic.flags, limits.job_limit = 0x200 | 0x2000, memory_bytes
    started, reason, child = time.monotonic(), None, None
    try:
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise OSError('formal_job_limits')
        with stdout_path.open('xb') as output:
            child = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=output,
                stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
                child.terminate()
                child.wait(timeout=5)
                raise OSError('formal_job_assignment')
            child.stdin.write(b'GO\n')
            child.stdin.close()
            while child.poll() is None:
                if time.monotonic() - started >= seconds or output.tell() > 1024**2:
                    reason = 'watchdog' if time.monotonic() - started >= seconds else 'stdout_limit'
                    kernel.TerminateJobObject(job, 124)
                    break
                time.sleep(.1)
            code = child.wait(timeout=5)
    finally:
        kernel.QueryInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits), None)
        kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
        kernel.CloseHandle(job)
    return {'exit_code': code, 'stop_reason': reason, 'charged_seconds': time.monotonic() - started,
        'measured_seconds': time.monotonic() - started, 'job_peak_commit_bytes': limits.job_peak,
        'job_write_transfer_bytes': accounting.io.write_bytes}
