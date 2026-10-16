"""Research-only byte/resource guards; no recommendation or quality logic."""
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
START = time.perf_counter()
READS = {}
PRIOR_SECONDS = 0.0


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    value = digest(raw)
    if expected is not None and value != expected:
        raise ValueError('input_digest_mismatch:' + path.name)
    READS[path.relative_to(ROOT).as_posix()] = {'sha256': value, 'bytes': len(raw)}
    return raw


def load(path, expected=None):
    return json.loads(read(path, expected))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value) + b'\n')


def guard(allowed_reads, output):
    allowed = {Path(p).resolve() for p in allowed_reads}
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('output_outside_project')

    def audit(event, args):
        if event.startswith(('socket.', 'subprocess.')) or event == 'os.system':
            raise RuntimeError('network_or_child_process_forbidden')
        if event != 'open' or isinstance(args[0], int):
            return
        path = Path(args[0]).resolve()
        mode = args[1] or ''
        flags = args[2] or 0
        writing = any(c in mode for c in 'wax+') or bool(flags & (1 | 2 | 64 | 512 | 1024))
        if writing and not path.is_relative_to(output):
            raise PermissionError('write_outside_diagnostic_output:' + path.name)
        if not writing and path not in allowed and not path.is_relative_to(output):
            raise PermissionError('read_outside_stage_allowlist:' + path.name)
    sys.addaudithook(audit)


class Memory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
        (key, ctypes.c_size_t) for key in ('peak', 'working', 'pp', 'p', 'np', 'n', 'page', 'peak_page', 'private')]


def resources():
    counters = Memory()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = (ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_ulong)
    if not query(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise RuntimeError('memory_measurement_failed')
    elapsed = time.perf_counter() - START
    if elapsed + PRIOR_SECONDS > 1800 or max(counters.peak, counters.peak_page) > 4 * 1024**3:
        raise RuntimeError('diagnostic_resource_limit')
    return {'elapsed_seconds': elapsed, 'peak_working_set_bytes': counters.peak,
            'peak_private_commit_bytes': counters.peak_page,
            'cumulative_compute_seconds': elapsed + PRIOR_SECONDS,
            'guard': 'checkpoint_time_and_windows_peak_memory'}


def verify_inputs():
    for path, binding in list(READS.items()):
        if digest((ROOT/path).read_bytes()) != binding['sha256']:
            raise RuntimeError('input_changed:' + path)


def summary(values):
    values = sorted(values)
    n = len(values)
    if not n:
        return {'n': 0}
    import math
    return {'n': n, 'min': values[0], 'median': (values[(n-1)//2] + values[n//2])/2,
            'mean': math.fsum(values)/n, 'p95': values[math.ceil(n*.95)-1], 'max': values[-1]}
