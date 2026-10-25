"""Stop the authorized worker on repeated interface failures or shared hard limits."""
import ctypes
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data/recommendation-runtime-audit/personalized-compact-0.1.0'
PID = 30372  # Verified Thesis interpreter running compact_experiment.py run --confirm.
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
handle = kernel.OpenProcess(0x1000, False, PID)
if not handle:
    raise SystemExit('worker_already_exited')
reason = None
try:
    while True:
        exit_code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != 259:
            break
        intents = []
        for p in (OUTPUT / 'calls').glob('*.intent.json'):
            row = json.loads(p.read_bytes())
            result_path = p.with_name(p.name.replace('.intent.json', '.result.json'))
            observed = json.loads(result_path.read_bytes()) if result_path.exists() else {}
            intents.append((row['started'], observed.get('status'), observed.get('error')))
        intents.sort()
        finished = [row for row in intents if row[1] is not None]
        if len(finished) >= 2 and not any(row[1] == 'ok' for row in finished):
            reason = 'first_two_profile_calls_failed_without_any_success'
        elif len(finished) >= 3 and all(row[1] == 'failed' for row in finished[-3:]):
            reason = 'three_consecutive_profile_transport_or_protocol_failures'
        started = json.loads((OUTPUT / 'started.json').read_bytes())
        if time.time() >= started['deadline']:
            reason = 'shared_24_hour_deadline'
        if sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()) >= 10 * 1024**3:
            reason = 'shared_10GiB_storage_limit'
        if reason:
            subprocess.run(['taskkill', '/PID', str(PID), '/T', '/F'], capture_output=True, check=False)
            record = {'terminal': 'stopped', 'reason': reason, 'utc_epoch': time.time(),
                'generation_intents': len(intents), 'finished': len(finished),
                'failed': sum(row[1] == 'failed' for row in finished),
                'last_errors': [row[2] for row in finished[-3:]], 'worker_pid': PID}
            Path(__file__).with_name('supervisor-stop.json').write_text(json.dumps(record), encoding='utf-8')
            print(json.dumps(record), flush=True)
            break
        time.sleep(.5)
finally:
    kernel.CloseHandle(handle)
if not reason:
    print(json.dumps({'terminal': 'worker_exited', 'supervisor_stop': False}), flush=True)
