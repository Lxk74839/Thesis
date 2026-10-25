"""Observe the already running worker's exit time and code; do not control or restart it."""
import ctypes
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
kernel.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
handle = kernel.OpenProcess(0x101000, False, 30372)
if not handle:
    raise SystemExit('verified_worker_no_longer_available')
try:
    while kernel.WaitForSingleObject(handle, 30000) == 258:
        pass
    ended = time.time()
    code = ctypes.c_ulong()
    if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
        raise ctypes.WinError(ctypes.get_last_error())
    record = {'ended_epoch': ended, 'exit_code': code.value, 'worker_pid': 30372,
        'timing_basis': 'Windows process handle signalled; local wall clock',
        'entry_point': 'compact_experiment.py run --confirm', 'automatic_retry': False}
    stop = HERE / 'supervisor-stop.json'
    if stop.exists():
        record['supervisor_stop'] = json.loads(stop.read_bytes())
    (HERE / 'run-terminal.json').write_text(json.dumps(record), encoding='utf-8')
    print(json.dumps(record), flush=True)
finally:
    kernel.CloseHandle(handle)
