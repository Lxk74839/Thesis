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
CONTROL = ROOT / '.scratch/ticket12-budget-20261018/storage-repair-package-20261019.json'
CONTROL_SHA = '4eb74906d427cbf0822379ad4b30a84827853412683df62a948730f2e882b2a0'
DISK = CONTROL.with_name('storage-repair-disk-writes-20261019.jsonl')
CONTROL_OPEN = open


def storage_package():
    raw = CONTROL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONTROL_SHA:
        raise SystemExit('storage_package_binding_changed')
    package = json.loads(raw)
    confirmation = package['human_confirmation']
    if hashlib.sha256((ROOT / confirmation['path']).read_bytes()).hexdigest() != confirmation['sha256']:
        raise SystemExit('storage_confirmation_changed')
    return package


def storage_overhead_bytes(package):
    # Only small control/audit/source paths and Git metadata; never the original catalog.
    total = sum(p.stat().st_size for p in CONTROL.parent.rglob('*') if p.is_file())
    total += sum((ROOT / name).stat().st_size for name in ('t0_catalog.py', 'tests/test_t0_catalog.py'))
    commands = 0
    for domain in ('offline', 't0'):
        audit = (ROOT / package[domain]['ledger']).parent
        total += sum(p.stat().st_size for p in audit.glob('storage_repair_*.txt'))
        pinned = next(p for p in package['protected_before'] if p['path'] == package[domain]['ledger'])
        total += (audit / 'resource-ledger.jsonl').stat().st_size - pinned['bytes']
        commands += sum('storage_repair_' in line for line in (audit / 'resource-ledger.jsonl').read_text().splitlines())
    return total + (commands + 1) * 16384  # Conservative reserve for Conda launcher temporaries.


def charge_git_outputs(package):
    """Git packs are data writes, not the small audit closeout reserve."""
    rows = [json.loads(row) for row in DISK.read_text().splitlines()] if DISK.exists() else []
    seen = {row['git_output'] for row in rows if 'git_output' in row}
    additions = []
    if not seen:
        # Conservatively retain all earlier overhead observations, including loose
        # Git objects removed by automatic repacking before this first snapshot.
        prior = sum(row.get('other_disk_upper_bound_after', 0) for domain in ('offline', 't0')
                    for row in map(json.loads, (ROOT / package[domain]['ledger']).read_text().splitlines())
                    if row.get('label', '').startswith('storage_repair_'))
        additions.append({'bytes': prior, 'kind': 'data', 'git_output': 'prior_upper_bound'})
    since = (ROOT / package['human_confirmation']['path']).stat().st_mtime_ns
    for path in (ROOT / '.git/objects').rglob('*'):
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and path.stat().st_mtime_ns >= since and name not in seen:
            additions.append({'bytes': path.stat().st_size, 'kind': 'data', 'git_output': name})
    charged = sum(row['bytes'] for row in rows if row.get('kind', 'data') == 'data')
    _limit = package['disk']['data_bytes']
    with CONTROL_OPEN(DISK, 'a', encoding='utf-8') as stream:
        for row in additions:
            stream.write(json.dumps(row) + '\n')
            charged += row['bytes']
    if charged > _limit:
        raise SystemExit('storage_package_data_closeout_required')


def storage_child(arguments):
    """Charge every attempted data write, including overwrites and failed tests."""
    import builtins
    import io
    import runpy
    sys.path.insert(0, str(ROOT))
    package = storage_package()
    original = io.open
    roots = tuple(ROOT / path for path in package['output_roots'])

    class File:
        def __init__(self, stream, path):
            self.stream, self.path = stream, path

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, value):
            length = len(value.encode(self.stream.encoding or 'utf-8')) if isinstance(value, str) else len(value)
            kind = 'closeout' if self.path.suffix == '.json' else 'data'
            charge_git_outputs(package)
            rows = [json.loads(row) for row in DISK.read_text().splitlines()] if DISK.exists() else []
            charged = sum(row['bytes'] for row in rows if row.get('kind', 'data') == kind)
            limit = 4 * 1024**2 if kind == 'closeout' else package['disk']['data_bytes']
            if charged + length > limit:
                raise OSError('storage_package_disk_limit')
            with original(DISK, 'a', encoding='utf-8') as counter:
                counter.write(json.dumps({'bytes': length, 'kind': kind}) + '\n')
            return self.stream.write(value)

        def writelines(self, values):
            for value in values:
                self.write(value)

    def opened(file, mode='r', *args, **kwargs):
        if not isinstance(file, (str, bytes, os.PathLike)) or not any(c in mode for c in 'wax+'):
            return original(file, mode, *args, **kwargs)
        path = Path(file).absolute()
        if '..' in path.parts or not any(path.is_relative_to(root) for root in roots):
            raise OSError('storage_package_write_outside_outputs')
        for parent in (path, *path.parents):
            if parent.exists() and (parent.is_symlink() or parent.is_junction()):
                raise OSError('storage_package_reparse_write')
            if parent == ROOT:
                break
        return File(original(file, mode, *args, **kwargs), path)

    io.open = builtins.open = opened
    if arguments[:1] == ['-m']:
        sys.argv = arguments[1:]
        runpy.run_module(arguments[1], run_name='__main__', alter_sys=True)
    else:
        sys.argv = arguments
        runpy.run_path(arguments[0], run_name='__main__')


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
    global AUDIT
    assert Path(sys.prefix).resolve() == ROOT / '.conda/envs/Thesis'
    assert sys.version_info[:3] == (3, 13, 16)
    arguments = sys.argv[1:]
    if arguments[:1] == ['--storage-child']:
        return storage_child(arguments[1:])
    domain = 'offline'
    if arguments[:1] == ['--resource-domain']:
        if len(arguments) < 4 or arguments[1] not in ('offline', 't0'):
            raise SystemExit('invalid_resource_domain')
        domain, arguments = arguments[1], arguments[2:]
    if domain == 't0':
        AUDIT = ROOT / 'data/recommendation-runtime-audit/ticket12-t0'
    AUDIT.mkdir(parents=True, exist_ok=True)
    ledger = AUDIT / 'resource-ledger.jsonl'
    inflight = AUDIT / 'resource-inflight.json'
    if inflight.exists():
        raise SystemExit('runtime_resource_usage_unresolved_no_new_work')
    used = sum(json.loads(row)['seconds'] for row in ledger.read_text().splitlines()) if ledger.exists() else 0
    label = arguments[0]
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in label):
        raise SystemExit('invalid_check_label')
    limit, package = LIMIT, None
    allowance = LIMIT - used
    if label.startswith('storage_repair_'):
        package = storage_package()
        settings = package[domain]
        pinned = next(p for p in package['protected_before'] if p['path'] == settings['ledger'])
        if hashlib.sha256(ledger.read_bytes()[:pinned['bytes']]).hexdigest() != pinned['sha256']:
            raise SystemExit('historical_ledger_changed')
        if domain == 't0':
            extension = AUDIT / 'resource-limit-extension-20261019.json'
            if hashlib.sha256(extension.read_bytes()).hexdigest() != 'c6b4eac9c73bda0deb51422d2c0419f5d3fa348577ee5a8359cd1851025a8b18':
                raise SystemExit('T0_extension_binding_changed')
        limit = settings['limit_seconds']
        allowance = min(limit - used, settings['package_seconds'] - (used - settings['baseline_seconds']))
        if allowance <= (15 if domain == 'offline' else 10):
            raise SystemExit('storage_package_closeout_required')
        charge_git_outputs(package)
        if storage_overhead_bytes(package) > 3 * 1024**2:
            raise SystemExit('storage_package_audit_closeout_required')
    if time.perf_counter() - START >= allowance:
        raise SystemExit('runtime_compute_limit_exhausted')
    source_paths = tuple(p for p in ('recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
                    'tests/test_batched_recommendation.py', 'provider_openai.py', 'token_counting.py',
                    'tests/provider_fixtures.py', 'tests/test_provider_openai.py', 'tests/test_token_counting.py',
                    't0_catalog.py', 'tests/test_t0_catalog.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/run_check.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/diagnose_t0_costs.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py')
                    if (ROOT / p).exists())
    source_sha256 = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    output = AUDIT / (label + '.txt')
    with inflight.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'label': label, 'guard_pid': os.getpid(), 'started_at_unix': time.time(),
                   'seconds': None, 'known_cumulative_seconds': used,
                   'unsettled_allowance_seconds': allowance}, stream, sort_keys=True)
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
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', THESIS_BATCH_CHECK_LABEL=label,
                   THESIS_RESOURCE_DOMAIN=domain, THESIS_RESOURCE_LEDGER=str(ledger),
                   THESIS_RESOURCE_DEADLINE_UNIX=str(time.time() + allowance - (time.perf_counter() - START)))
        if package:
            env['THESIS_STORAGE_PACKAGE'] = str(CONTROL)
        with output.open('xb') as stream:
            command = [str(Path(__file__)), '--storage-child', *arguments[1:]] if package else arguments[1:]
            child = subprocess.Popen([sys.executable, '-B', *command], cwd=ROOT,
                                     stdout=stream, stderr=subprocess.STDOUT, env=env)
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
                child.terminate()
                child.wait()
                raise ctypes.WinError(ctypes.get_last_error())
            while child.poll() is None:
                if package:
                    charge_git_outputs(package)
                if (time.perf_counter() - START >= allowance or output.stat().st_size > 1024**2
                        or package and storage_overhead_bytes(package) > 4 * 1024**2):
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
               'guard_reserve_bytes': RESERVE, 'limit_bytes': 4 * 1024**3, 'limit_seconds': limit,
               'accounting': 'guard_start_to_child_completion_wall_time_including_failures',
               'guard': 'Windows_Job_tree_limit_plus_64MiB_guard_reserve', 'source_sha256': source_sha256,
               'source_changed_during_check': [p for p, sha in source_sha256.items()
                   if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha]}
        if package:
            row['package_seconds_after'] = used + seconds - package[domain]['baseline_seconds']
            row['package_limit_seconds'] = package[domain]['package_seconds']
            row['charged_data_bytes_after'] = sum(json.loads(line)['bytes'] for line in DISK.read_text().splitlines()) if DISK.exists() else 0
            row['other_disk_upper_bound_after'] = storage_overhead_bytes(package)
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
