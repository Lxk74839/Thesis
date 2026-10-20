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
PILOT_CONTROL = CONTROL.with_name('recovery-pilot-package-20261019.json')
PILOT_SHA = '6da3c084bc2b1b298994f692db13d9b885dbd97cf180904e7a31cfefcb61c93b'
SETTLED = False
ON_DEMAND = ROOT / '.scratch/ticket12-budget-20261018/on-demand-package-20261019.json'
ON_DEMAND_SHA = '2c785971e00379bd51fbc15a3be0b14cc346f14b5dfb65ab7bd847aad92eaee3'
EVALUATION = ROOT / '.scratch/test100-evaluation-20261020/package.json'
EVALUATION_SHA = '2045d544823affdc935e963f6f39ce731b81cd5906e1e281ffcd6e7a1280fa67'


def on_demand_package(evaluation=False):
    raw = (EVALUATION if evaluation else ON_DEMAND).read_bytes()
    if hashlib.sha256(raw).hexdigest() != (EVALUATION_SHA if evaluation else ON_DEMAND_SHA):
        raise SystemExit('on_demand_package_changed')
    package = json.loads(raw)
    if (package['schema_version'] != ('test100-evaluation-package-0.1.0' if evaluation else 'test100-offline-package-0.1.0')
            or package['approved'] is not True or package['api_limits'] != {'generate': 0, 'count': 0, 'other': 0}):
        raise SystemExit('invalid_on_demand_package')
    for name in ('human_confirmation', 'draft'):
        ref = package[name]
        if hashlib.sha256((ROOT / ref['path']).read_bytes()).hexdigest() != ref['sha256']:
            raise SystemExit('on_demand_confirmation_changed')
    return package


def pilot_package():
    raw = PILOT_CONTROL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PILOT_SHA:
        raise SystemExit('pilot_package_binding_changed')
    package = json.loads(raw)
    ref = package['human_confirmation']
    if hashlib.sha256((ROOT / ref['path']).read_bytes()).hexdigest() != ref['sha256']:
        raise SystemExit('pilot_confirmation_changed')
    return package


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
    prefix = package.get('label_prefix', 'storage_repair_')
    for domain in ('offline', 't0'):
        audit = (ROOT / package[domain]['ledger']).parent
        total += sum(p.stat().st_size for p in audit.glob(prefix + '*.txt'))
        pinned = next(p for p in package['protected_before'] if p['path'] == package[domain]['ledger'])
        total += (audit / 'resource-ledger.jsonl').stat().st_size - pinned['bytes']
        commands += sum(prefix in line for line in (audit / 'resource-ledger.jsonl').read_text().splitlines())
    return total + (commands + 1) * 16384  # Conservative reserve for Conda launcher temporaries.


def charge_git_outputs(package):
    """Git packs are data writes, not the small audit closeout reserve."""
    rows = [json.loads(row) for row in DISK.read_text().splitlines()] if DISK.exists() else []
    pilot = 'disk_ledger' in package
    seen = {(row['git_output'], row.get('mtime_ns') if pilot else None) for row in rows if 'git_output' in row}
    additions = []
    if not seen:
        # Conservatively retain all earlier overhead observations, including loose
        # Git objects removed by automatic repacking before this first snapshot.
        prior = sum(row.get('other_disk_upper_bound_after', 0) for domain in ('offline', 't0')
                    for row in map(json.loads, (ROOT / package[domain]['ledger']).read_text().splitlines())
                    if row.get('label', '').startswith(package.get('label_prefix', 'storage_repair_')))
        additions.append({'bytes': prior, 'kind': 'data', 'git_output': 'prior_upper_bound'})
    since = (ROOT / package['human_confirmation']['path']).stat().st_mtime_ns
    for path in (ROOT / '.git/objects').rglob('*'):
        name = path.relative_to(ROOT).as_posix()
        if path.is_file() and path.stat().st_mtime_ns >= since:
            stamp = path.stat().st_mtime_ns if pilot else None
            if (name, stamp) not in seen:
                additions.append({'bytes': path.stat().st_size, 'kind': 'data', 'git_output': name, 'mtime_ns': stamp})
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
    global DISK
    pilot = bool(os.environ.get('THESIS_RECOVERY_PILOT_PACKAGE'))
    evaluation = bool(os.environ.get('THESIS_EVALUATION_PACKAGE'))
    demand = evaluation or bool(os.environ.get('THESIS_ON_DEMAND_PACKAGE'))
    package = on_demand_package(evaluation) if demand else pilot_package() if pilot else storage_package()
    if pilot or demand:
        DISK = ROOT / package['disk_ledger']
    original = io.open
    roots = tuple(ROOT / path for path in package['output_roots'])
    prior = [json.loads(row) for row in DISK.read_text().splitlines()] if DISK.exists() else []
    charged = {kind: sum(r['bytes'] for r in prior if r.get('kind', 'data') == kind) for kind in ('data', 'closeout')}
    if demand:
        charged['data'] += sum(r['bytes'] for r in prior if r.get('kind') == 'native_and_git_precharge')
    by_area = {i: sum(r['bytes'] for r in prior if r.get('area') == i) for i in range(len(roots))}

    def write_path(file):
        path = Path(file).absolute()
        if '..' in path.parts or not any(path.is_relative_to(root) for root in roots):
            raise OSError('storage_package_write_outside_outputs')
        for parent in (path, *path.parents):
            if parent.exists() and (parent.is_symlink() or parent.is_junction()):
                raise OSError('storage_package_reparse_write')
            if parent == ROOT:
                break
        return path

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
            kind = ('closeout' if 'closeout' in os.environ['THESIS_BATCH_CHECK_LABEL'] else 'data') if demand else (
                ('closeout' if self.path.name in ('checkpoint.json', 'run.json') else 'data') if pilot else (
                'closeout' if self.path.suffix == '.json' else 'data'))
            if not pilot and not demand:
                charge_git_outputs(package)
                rows = [json.loads(row) for row in DISK.read_text().splitlines()] if DISK.exists() else []
                charged[kind] = sum(row['bytes'] for row in rows if row.get('kind', 'data') == kind)
            limit = ((package['disk']['closeout_reserve'] if kind == 'closeout' else
                      package['disk']['total_bytes'] - package['disk']['closeout_reserve']) if demand else
                     (256 * 1024**2 if pilot else 4 * 1024**2) if kind == 'closeout' else package['disk']['data_bytes'])
            if charged[kind] + length > limit:
                raise OSError('storage_package_disk_limit')
            area = next(i for i, root in enumerate(roots) if self.path.is_relative_to(root))
            if pilot and by_area[area] + length > package[
                    'public_bytes' if area == 0 else 'pilot_bytes']:
                raise OSError('pilot_area_disk_limit')
            with original(DISK, 'a', encoding='utf-8') as counter:
                counter.write(json.dumps({'bytes': length, 'kind': kind, 'area': area}) + '\n')
            charged[kind] += length
            by_area[area] += length
            return self.stream.write(value)

        def writelines(self, values):
            for value in values:
                self.write(value)

    def opened(file, mode='r', *args, **kwargs):
        if not isinstance(file, (str, bytes, os.PathLike)):
            return original(file, mode, *args, **kwargs)
        path = Path(file).absolute()
        writing = any(c in mode for c in 'wax+')
        if evaluation and not writing and path.is_relative_to(ROOT / 'data'):
            raise OSError('evaluation_real_data_read_forbidden')
        if demand and not writing and (path.is_relative_to(ROOT / 'data/ticket12-t0') or path.name == 'id-key.bin'):
            raise OSError('on_demand_old_recovery_or_identity_read_forbidden')
        if pilot and not writing:
            legacy = ROOT / 'data/ticket12-t0/catalog-0.1.0'
            if path.is_relative_to(legacy) and path.relative_to(legacy).as_posix() not in (
                    'catalog.json', 'coverage.json', 'source-index.json', 'roots.jsonl', 'requests.jsonl', 'run.json'):
                raise OSError('pilot_old_body_read_forbidden')
            if path == ROOT / package['development_sources']['identity_key']['path']:
                if (os.environ.get('THESIS_RECOVERY_STAGE') != 'G0' or arguments[:2] != [
                        '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py', 'snapshot']):
                    raise OSError('pilot_identity_read_not_authorized')
                # An interrupted or failed first read cannot silently be repeated.
                claim = roots[1] / 'identity-key-read-claim.json'
                with opened(claim, 'x', encoding='utf-8') as stream:
                    stream.write(json.dumps({'label': os.environ['THESIS_BATCH_CHECK_LABEL'], 'package_sha256': PILOT_SHA}) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            if path.is_relative_to(ROOT / 'data') and any(part.lower() in (
                    'evaluation', 'eval', 'gold', 'reference', 'uq', 'test-performance') for part in path.parts):
                raise OSError('pilot_evaluation_read_forbidden')
        if not writing:
            return original(file, mode, *args, **kwargs)
        if pilot and path == ROOT / package['attempt_ledger'] and mode in ('a', 'ab'):
            return original(file, mode, *args, **kwargs)
        write_path(path)
        return File(original(file, mode, *args, **kwargs), path)

    io.open = builtins.open = opened
    if pilot or demand:
        mkdir, replace, rename, unlink, rmdir = os.mkdir, os.replace, os.rename, os.unlink, os.rmdir
        def directory(file, *args, **kwargs):
            write_path(file)
            return mkdir(file, *args, **kwargs)
        def move(operation, source, target, *args, **kwargs):
            write_path(source)
            write_path(target)
            return operation(source, target, *args, **kwargs)
        def remove(operation, file, *args, **kwargs):
            write_path(file)
            return operation(file, *args, **kwargs)
        os.mkdir = directory
        os.replace = lambda source, target, *a, **k: move(replace, source, target, *a, **k)
        os.rename = lambda source, target, *a, **k: move(rename, source, target, *a, **k)
        os.unlink = lambda file, *a, **k: remove(unlink, file, *a, **k)
        os.rmdir = lambda file, *a, **k: remove(rmdir, file, *a, **k)
        def audit(event, arguments):
            if event in ('socket.connect', 'socket.sendto'):
                raise OSError('on_demand_network_forbidden' if demand else 'pilot_network_forbidden')
        sys.addaudithook(audit)
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


class Accounting(ctypes.Structure):
    _fields_ = [('times', ctypes.c_longlong * 4), ('counts', wintypes.DWORD * 4), ('io', IO)]


def source_digest(name):
    try:
        return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    except OSError:
        return None


def process_io():
    counters = IO()
    if not ctypes.windll.kernel32.GetProcessIoCounters(wintypes.HANDLE(-1), ctypes.byref(counters)):
        raise ctypes.WinError()
    return counters


def main():
    global AUDIT, DISK, SETTLED
    guard_before = process_io()
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
    if domain == 't0' and arguments[0].startswith(('ondemand_', 'eval100_')):
        raise SystemExit('on_demand_T0_not_authorized')
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
    limit, package, pilot, stage = LIMIT, None, label.startswith('recovery_pilot_'), None
    evaluation = label.startswith('eval100_')
    demand = evaluation or label.startswith('ondemand_')
    allowance = LIMIT - used
    if demand:
        if domain != 'offline':
            raise SystemExit('on_demand_T0_not_authorized')
        package = on_demand_package(evaluation)
        DISK = ROOT / package['disk_ledger']
        settings = package['offline']
        if hashlib.sha256(ledger.read_bytes()[:settings['bytes']]).hexdigest() != settings['sha256']:
            raise SystemExit('historical_ledger_changed')
        allowance = min(allowance, settings['package_seconds'] - (used - settings['baseline_seconds']))
        if 'closeout' not in label:
            allowance -= settings.get('reserve_seconds', 15)
        if allowance <= 0:
            raise SystemExit('on_demand_time_limit')
        writes = sum(json.loads(line)['bytes'] for line in DISK.read_text().splitlines())
        if writes >= package['disk']['total_bytes'] - (0 if 'closeout' in label else package['disk']['closeout_reserve']):
            raise SystemExit('on_demand_disk_limit')
    if label.startswith('storage_repair_') or pilot:
        package = pilot_package() if pilot else storage_package()
        if pilot:
            DISK = ROOT / package['disk_ledger']
        settings = package[domain]
        pinned = next(p for p in package['protected_before'] if p['path'] == settings['ledger'])
        if hashlib.sha256(ledger.read_bytes()[:pinned['bytes']]).hexdigest() != pinned['sha256']:
            raise SystemExit('historical_ledger_changed')
        if domain == 't0':
            extension = AUDIT / ('resource-limit-extension-recovery-pilot-20261019.json' if pilot else 'resource-limit-extension-20261019.json')
            expected = 'aa4c3b12f3533675f6fab6909114d66b18b013260fa29eef181adb425da2fe50' if pilot else 'c6b4eac9c73bda0deb51422d2c0419f5d3fa348577ee5a8359cd1851025a8b18'
            if hashlib.sha256(extension.read_bytes()).hexdigest() != expected:
                raise SystemExit('T0_extension_binding_changed')
        limit = settings['limit_seconds']
        allowance = min(limit - used, settings['package_seconds'] - (used - settings['baseline_seconds']))
        if pilot:
            allowance -= settings['reserve_seconds']
            if domain == 't0':
                stage = label.split('_')[2]
                if stage not in package['approved_stages']:
                    raise SystemExit('pilot_stage_not_authorized')
                stage_used = sum(r['seconds'] for r in map(json.loads, ledger.read_text().splitlines())
                                 if r.get('recovery_stage') == stage)
                allowance = min(allowance, package['t0_stages'][stage] - stage_used)
        if allowance <= (0 if pilot else 15 if domain == 'offline' else 10):
            raise SystemExit('storage_package_closeout_required')
        charge_git_outputs(package)
        if storage_overhead_bytes(package) > (240 if pilot else 3) * 1024**2:
            raise SystemExit('storage_package_audit_closeout_required')
    if time.perf_counter() - START >= allowance:
        raise SystemExit('runtime_compute_limit_exhausted')
    source_paths = tuple(p for p in ('recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
                    'tests/test_batched_recommendation.py', 'provider_openai.py', 'token_counting.py',
                    'tests/provider_fixtures.py', 'tests/test_provider_openai.py', 'tests/test_token_counting.py',
                    't0_catalog.py', 'tests/test_t0_catalog.py', 'joint_access.py', 'joint_tasks.py',
                    'evidence_verification.py', 'quality_fusion.py', 'sim_normal.py', 'sim_scenarios.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/run_check.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/diagnose_t0_costs.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py',
                    'experiment_runner.py', 'tests/test_experiment_runner.py', 'tests/test_on_demand_runtime.py',
                    '.scratch/ticket12-budget-20261018/diagnostics/check_on_demand_delivery.py')
                    if (ROOT / p).exists())
    if evaluation:
        source_paths += tuple(p for p in ('experiment_evaluation.py', 'tests/test_experiment_evaluation.py') if (ROOT / p).exists())
    source_sha256 = {p: source_digest(p) for p in source_paths}
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
    changed_while_running, next_source_check = [], time.perf_counter()
    try:
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', THESIS_BATCH_CHECK_LABEL=label,
                   THESIS_RESOURCE_DOMAIN=domain, THESIS_RESOURCE_LEDGER=str(ledger),
                   THESIS_RESOURCE_DEADLINE_UNIX=str(time.time() + allowance - (time.perf_counter() - START)))
        if package:
            env['THESIS_EVALUATION_PACKAGE' if evaluation else 'THESIS_ON_DEMAND_PACKAGE' if demand else 'THESIS_RECOVERY_PILOT_PACKAGE' if pilot else 'THESIS_STORAGE_PACKAGE'] = str(EVALUATION if evaluation else ON_DEMAND if demand else PILOT_CONTROL if pilot else CONTROL)
            if pilot:
                env['THESIS_RECOVERY_STAGE'] = stage or 'PUBLIC'
        with output.open('xb') as stream:
            command = [str(Path(__file__)), '--storage-child', *arguments[1:]] if package else arguments[1:]
            child = subprocess.Popen([sys.executable, '-B', *command], cwd=ROOT,
                                     stdout=stream, stderr=subprocess.STDOUT, env=env)
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
                child.terminate()
                child.wait()
                raise ctypes.WinError(ctypes.get_last_error())
            while child.poll() is None:
                if (pilot or demand) and time.perf_counter() >= next_source_check:
                    changed_while_running = [p for p, sha in source_sha256.items() if source_digest(p) != sha]
                    next_source_check = time.perf_counter() + .25
                    if changed_while_running:
                        kernel.TerminateJobObject(job, 3)
                        break
                if package and not pilot and not demand:
                    charge_git_outputs(package)
                if (time.perf_counter() - START >= allowance or output.stat().st_size > 1024**2
                        or package and not demand and storage_overhead_bytes(package) > (256 if pilot else 4) * 1024**2):
                    kernel.TerminateJobObject(job, 3)
                    break
                time.sleep(.025)
            code = child.wait()
    finally:
        kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
        accounting = Accounting()
        if not kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(job)
        guard_after = process_io()
        seconds = time.perf_counter() - START
        row = {'label': label, 'seconds': seconds, 'cumulative_seconds': used + seconds,
               'exit_code': code, 'job_peak_commit_bytes': info.job_peak,
               'guard_reserve_bytes': RESERVE, 'limit_bytes': 4 * 1024**3, 'limit_seconds': limit,
               'accounting': 'guard_start_to_child_completion_wall_time_including_failures',
               'guard': 'Windows_Job_tree_limit_plus_64MiB_guard_reserve', 'source_sha256': source_sha256,
               'job_read_transfer_bytes': accounting.io.read_bytes, 'job_write_transfer_bytes': accounting.io.write_bytes,
               'guard_read_transfer_bytes': guard_after.read_bytes - guard_before.read_bytes,
               'guard_write_transfer_bytes': guard_after.write_bytes - guard_before.write_bytes,
               'source_changed_during_check': sorted(set(changed_while_running) | {p for p, sha in source_sha256.items()
                   if source_digest(p) != sha})}
        if package:
            row['package_seconds_after'] = used + seconds - package[domain]['baseline_seconds']
            row['package_limit_seconds'] = package[domain]['package_seconds']
            row['charged_data_bytes_after'] = sum(json.loads(line)['bytes'] for line in DISK.read_text().splitlines()) if DISK.exists() else 0
            row['other_disk_upper_bound_after'] = 0 if demand else storage_overhead_bytes(package)
            if demand:
                row['scope'] = package['scope']
            if pilot:
                row['recovery_stage'] = stage or 'PUBLIC'
        with ledger.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        inflight.unlink()
        SETTLED = True
    if output.exists():
        print(output.read_text(encoding='utf-8'), end='')
    print(json.dumps(row, sort_keys=True))
    return code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except BaseException as exc:
        if (not SETTLED and sys.argv[1:2] != ['--storage-child']
                and any(arg.startswith(('recovery_pilot_', 'ondemand_', 'eval100_')) for arg in sys.argv[1:])):
            label = next(arg for arg in sys.argv[1:] if arg.startswith(('recovery_pilot_', 'ondemand_', 'eval100_')))
            ledger = AUDIT / 'resource-ledger.jsonl'
            if str(exc) != 'runtime_resource_usage_unresolved_no_new_work':
                used = sum(json.loads(raw)['seconds'] for raw in ledger.read_text().splitlines())
                seconds = time.perf_counter() - START
                row = {'label': label, 'seconds': seconds, 'cumulative_seconds': used + seconds,
                    'exit_code': 2, 'pre_child_failure': str(exc), 'recovery_stage': label.split('_')[2]
                        if '--resource-domain' in sys.argv else 'PUBLIC', 'job_peak_commit_bytes': 0,
                    'accounting': 'guard_start_to_pre_child_rejection_including_failure', 'source_changed_during_check': []}
                with ledger.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row, sort_keys=True) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                print(json.dumps(row, sort_keys=True))
        raise
