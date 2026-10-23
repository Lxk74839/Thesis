"""Task16 independent control. Production stays blocked until the algorithm is sealed."""
import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import importlib.util
import json
import os
import msvcrt
from pathlib import Path
import sys
import threading
import time
import uuid

PROJECT = Path(__file__).resolve().parent
DEFAULT_SESSION = PROJECT / 'data/recommendation-runtime-audit/macrec-agri-dev-task16'
TEMP = PROJECT / '.tmp/task16-execution'
LOCK = threading.RLock()
SIZES = {}
ATTEMPTS = {}
REQUEST_LOCKS = {}
BUDGET_SHA = '24d87b89be7d74bcc28d324d6ead5461a1ce563a69adad65706270206cbaa30b'
STORAGE_SHA = '2165a0dad3ccd35dc2065bc4f86970ff2d1e20c5feb030af79140e9cf4121d6c'
PHASES = [('offline', 0), ('parameters', 32), ('features-v00', 288), ('v00-main', 1184),
    ('evaluate-v00', 0), ('q1', 1184), ('q2', 1184), ('semantic', 592),
    ('confidence', 592), ('quality', 1184), ('feedback', 592), ('auxiliary', 112), ('evaluate-final', 0)]
BUDGET_STOPS = {'task16_original_deadline_expired', 'task16_dispatch_deadline', 'task16_call_limit',
    'task16_phase_limit', 'task16_unit_limit', 'task16_storage_limit', 'task16_insufficient_remaining_time',
    'watchdog', 'stdout_limit'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_once(path, value):
    raw = encoded(value)
    with LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError('task16_artifact_changed')
            return
        pending = path.with_name(path.name + '.' + uuid.uuid4().hex + '.pending')
        with pending.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(pending, path)
        for root, entry in SIZES.items():
            if path.is_relative_to(root):
                entry[1] += len(raw)


def replace_json(path, value):
    with LOCK:
        previous = path.stat().st_size if path.exists() else 0
        pending = path.with_name(path.name + '.' + uuid.uuid4().hex + '.pending')
        write_once(pending, value)
        os.replace(pending, path)
        for root, entry in SIZES.items():
            if path.is_relative_to(root):
                entry[1] -= previous


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def instant(value):
    return float(value) if isinstance(value, (int, float)) else datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def session_path(value):
    path = Path(value).absolute()
    if path.resolve() != path:
        raise ValueError('task16_session_reparse_or_parent')
    if path != DEFAULT_SESSION and not path.is_relative_to(TEMP):
        raise ValueError('task16_session_scope')
    return path


def budget_at(directory):
    if directory == DEFAULT_SESSION and sha((directory / 'budget.json').read_bytes()) != BUDGET_SHA:
        raise ValueError('task16_original_budget_changed')
    return read(directory / 'budget.json')


def tree_bytes(path):
    if not path.exists():
        return 0
    return path.stat().st_size if path.is_file() else sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def new_bytes(directory, *, force=False):
    entry = SIZES.get(directory)
    if force or entry is None or time.monotonic() - entry[0] > 30:
        paths = [directory]
        if directory == DEFAULT_SESSION:
            paths += [PROJECT / '.scratch/macrec-algorithm-20261023',
                PROJECT / '.scratch/task16-execution-v2-20261023', TEMP,
                PROJECT / 'task16_control.py', PROJECT / 'tests/test_task16_control.py', PROJECT / 'tests/test_macrec.py',
                PROJECT / 'research/MACRec原文与源码固定核查_20261023.md',
                *(PROJECT / p for p in ('macrec_experiment.py', 'macrec_recommendation.py', 'macrec_evaluation.py'))]
        shared = 0
        if directory == DEFAULT_SESSION:
            raw = (directory / 'storage-baseline.json').read_bytes()
            if sha(raw) != STORAGE_SHA:
                raise ValueError('task16_storage_baseline_changed')
            baseline = json.loads(raw)['files']
            for scope in (PROJECT / '.git', PROJECT / '.tmp'):
                for path in scope.rglob('*'):
                    if path.is_file() and not path.is_relative_to(TEMP):
                        shared += max(0, path.stat().st_size - baseline.get(path.relative_to(PROJECT).as_posix(), 0))
        entry = [time.monotonic(), sum(tree_bytes(p) for p in paths) + shared]
        SIZES[directory] = entry
    return entry[1]


def request_rows(directory):
    index = directory / 'request-index'
    calls = list((directory / 'calls').glob('*.json'))
    if not index.exists() and (calls or (directory / 'run-binding.json').exists()):
        raise ValueError('task16_call_record_missing')
    rows = {p.stem: read(p) for p in index.glob('*.json')}
    active = worker_active(directory)
    if any(p.name.split('.')[0] not in rows and not (active and p.name.endswith('.request.json')) for p in calls):
        raise ValueError('task16_call_record_missing')
    for key, row in rows.items():
        intent = directory / 'calls' / (key + '.intent.json')
        if not intent.exists():
            if active:
                continue
            raise ValueError('task16_call_record_missing')
        if read(intent) != row:
            raise ValueError('task16_call_record_changed')
        request = intent.with_name(key + '.request.json')
        if not request.exists() or sha(request.read_bytes()) != row['request_sha256']:
            raise ValueError('task16_call_record_missing')
    return list(rows.values())


def call_counts(directory):
    counts = dict.fromkeys(('attempts', 'successful', 'failed', 'unresolved'), 0)
    usage = dict.fromkeys(('input_tokens', 'output_tokens', 'unknown_requests', 'cached_input_tokens',
        'cache_unknown_requests'), 0)
    latency = 0
    for intent_row in request_rows(directory):
        intent = directory / 'calls' / (intent_row['request_id'] + '.intent.json')
        counts['attempts'] += 1
        terminal = intent.with_name(intent.name.replace('.intent.json', '.terminal.json'))
        row = read(terminal) if terminal.exists() else {'status': 'unresolved'}
        if 'response_sha256' in row:
            response = intent.with_name(intent.name.replace('.intent.json', '.response.json'))
            if sha(response.read_bytes()) != row['response_sha256']:
                raise ValueError('task16_response_changed')
        state = row['status']
        counts[{'ok': 'successful', 'failed': 'failed', 'unresolved': 'unresolved'}[state]] += 1
        tokens = row.get('usage') or {}
        if all(type(tokens.get(k)) is int and tokens[k] >= 0 for k in ('input_tokens', 'output_tokens')):
            for key in ('input_tokens', 'output_tokens'):
                usage[key] += tokens[key]
        else:
            usage['unknown_requests'] += 1
        cached = (tokens.get('input_tokens_details') or {}).get('cached_tokens')
        if type(cached) is int and cached >= 0:
            usage['cached_input_tokens'] += cached
        else:
            usage['cache_unknown_requests'] += 1
        if 'completed' in row:
            latency += max(0, row['completed'] - intent_row['started'])
    return counts, usage, latency


def stop_requested(directory):
    worker = directory / 'worker.json'
    return worker.exists() and (directory / 'commands' /
        (read(worker)['generation'] + '.stop.json')).exists()


def persist_halt(directory, reason, *, generation=None):
    state = ('partial_budget' if reason in BUDGET_STOPS else 'paused' if reason == 'task16_stop_requested'
        else 'stopped' if reason.startswith('worker_exit_') else 'partial_control')
    worker = read(directory / 'worker.json') if (directory / 'worker.json').exists() else {}
    generation = generation or worker['generation']
    replace_json(directory / 'halts' / (generation + '.json'), {'status': state,
        'reason': reason, 'at': time.time(), 'generation': generation})


@contextmanager
def storage_guard(directory):
    ceiling = budget_at(directory)['max_new_bytes']
    if new_bytes(directory, force=True) >= ceiling:
        raise ValueError('task16_storage_limit')
    done = threading.Event()

    def monitor():
        while not done.wait(1):
            with LOCK:
                if new_bytes(directory, force=True) >= ceiling:
                    persist_halt(directory, 'task16_storage_limit')
                    os._exit(126)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join()
        if new_bytes(directory, force=True) >= ceiling:
            raise ValueError('task16_storage_limit')


def request_stop(directory):
    if not worker_active(directory):
        return status(directory)
    worker = read(directory / 'worker.json')
    path = directory / 'commands' / (worker['generation'] + '.stop.json')
    if not path.exists():
        write_once(path, {'generation': worker['generation'], 'requested': time.time()})
    return {'status': 'stop_requested', 'generation': worker['generation']}


@contextmanager
def activity(directory, category):
    path = directory / 'activity' / (uuid.uuid4().hex + '.json')
    row = {'category': category, 'start': time.time(), 'end': None,
        'generation': read(directory / 'worker.json')['generation']}
    row['heartbeat'] = row['start']
    replace_json(path, row)
    done = threading.Event()

    def heartbeat():
        while not done.wait(1):
            row['heartbeat'] = time.time()
            replace_json(path, row)

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join()
        row['end'] = time.time()
        replace_json(path, row)


def development(directory, *, end=False):
    paths = list((directory / 'activity').glob('development-*.json'))
    open_paths = [p for p in paths if read(p)['end'] is None]
    if end:
        if not open_paths and paths:
            return status(directory)
        path = open_paths[0] if open_paths else directory / 'activity/development-initial.json'
        row = read(path) if path.exists() else {'category': 'development',
            'start': instant(budget_at(directory).get('activity_start_utc', budget_at(directory)['started_at_utc']))}
        replace_json(path, row | {'end': time.time()})
    elif not open_paths:
        path = directory / 'activity' / ('development-' + uuid.uuid4().hex + '.json')
        start = time.time() if paths else instant(budget_at(directory).get(
            'activity_start_utc', budget_at(directory)['started_at_utc']))
        replace_json(path, {'category': 'development', 'start': start, 'end': None})
    return status(directory)


def timing(directory, budget, active):
    now = time.time()
    start = instant(budget['started_at_utc'])
    intervals = {'development': [], 'model': [], 'evaluation': []}
    worker = read(directory / 'worker.json') if (directory / 'worker.json').exists() else {}
    for path in (directory / 'activity').glob('*.json'):
        row = read(path)
        end = row.get('end')
        if end is None:
            current = row['category'] == 'development' or (active and row.get('generation') == worker.get('generation'))
            end = now if current else row['heartbeat']
        intervals[row['category']].append((max(start, row['start']), min(now, end)))

    def union(rows):
        result, prior = 0, start
        for left, right in sorted(rows):
            result += max(0, right - max(left, prior))
            prior = max(prior, right)
        return result

    durations = {key + '_seconds': union(rows) for key, rows in intervals.items()}
    total = max(0, now - start)
    occupied = union([row for rows in intervals.values() for row in rows])
    return durations | {'waiting_seconds': max(0, total - occupied),
        'overlap_seconds': sum(durations.values()) - occupied, 'total_seconds': total}


def worker_active(directory):
    path = directory / 'worker.lock'
    if not path.exists():
        return False
    with path.open('r+b') as stream:
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    return False


@contextmanager
def coordinator(directory, generation):
    with (directory / 'worker.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise ValueError('task16_worker_already_active') from None
        replace_json(directory / 'worker.json', {'pid': os.getpid(), 'generation': generation,
            'started': time.time()})
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def verified_ref(ref):
    path = (PROJECT / ref['path']).absolute()
    if '..' in path.parts or '.secrets' in path.parts or not path.is_relative_to(PROJECT):
        raise ValueError('task16_reference_scope')
    if path.resolve() != path or sha(path.read_bytes()) != ref['sha256']:
        raise ValueError('task16_reference_changed')
    return path


def ready_plan(directory):
    plan_path, seal_path = directory / 'run-plan.json', directory / 'review-seal.json'
    if not plan_path.exists() or not seal_path.exists():
        return None
    plan, seal = read(plan_path), read(seal_path)
    if (plan['schema'] != 'task16-run-plan/1' or seal['plan_sha256'] != sha(plan_path.read_bytes())
            or {r['axis'] for r in seal['reviews']} != {'standards', 'spec'}
            or any(r['result'] != 'PASS' for r in seal['reviews'])):
        raise ValueError('task16_review_seal_invalid')
    worker = verified_ref(plan['worker'])
    code = [verified_ref(ref) for ref in seal['code']]
    for ref in [*seal['reviews'], *plan.get('sources', [])]:
        verified_ref(ref)
    if PROJECT / 'task16_control.py' not in code:
        raise ValueError('task16_controller_unreviewed')
    if plan['kind'] == 'offline_fixture':
        if not directory.is_relative_to(TEMP) or not worker.is_relative_to(TEMP):
            raise ValueError('task16_fixture_scope')
    elif plan['kind'] == 'live':
        required_code = [PROJECT / p for p in ('task16_control.py', 'formal_process.py',
            '.scratch/task16-execution-v2-20261023/run-task16.ps1', 'macrec_experiment.py')]
        required_sources = {'panel', 'candidates', 'recall', 'evidence', 'model', 'algorithm_spec',
            'upstream_lock', 'evaluation_contract'}
        if (directory != DEFAULT_SESSION or worker != PROJECT / 'macrec_experiment.py'
                or plan.get('panel_users') != 16 or not seal.get('spec_confirmed')
                or [(s['id'], s['max_calls']) for s in plan['stages']] != PHASES
                or any(p not in code for p in required_code)
                or not required_sources.issubset({r.get('role') for r in plan.get('sources', [])})
                or [len(s['units']) for s in plan['stages']] != [1, 32, 16, 32, 1, 32, 32, 16, 16, 32, 16, 32, 1]
                or any(not s['units'] or sum(u['limit'] for u in s['units']) > s['max_calls']
                    or any(u['phase'] != s['id'] or u['limit'] < 0 for u in s['units']) for s in plan['stages'])):
            raise ValueError('task16_live_plan_incomplete')
    else:
        raise ValueError('task16_unknown_plan_kind')
    return plan


def unit_path(directory, unit):
    key = sha(encoded(unit))
    return directory / 'units' / (key + '.json')


def observed_unit(directory, unit, plan_sha):
    artifact = unit_path(directory, unit)
    if not artifact.exists():
        return None
    row = read(artifact)
    checksum = row.pop('checksum_sha256', None)
    if checksum != sha(encoded(row)):
        raise ValueError('task16_unit_changed_or_unsealed')
    if row['plan_sha256'] != plan_sha or row['unit_sha256'] != sha(encoded(unit)):
        raise ValueError('task16_unit_binding_changed')
    return row


def progress(directory, plan):
    if plan is None:
        return {'completed_units': 0, 'unresolved_units': 0, 'planned_units': 0,
            'remaining_units': 0, 'unstarted_units': 0, 'stages': []}
    plan_sha = sha((directory / 'run-plan.json').read_bytes())
    stages = []
    for stage in plan['stages']:
        rows = [observed_unit(directory, u, plan_sha) for u in stage['units']]
        completed = sum(r is not None and r['status'] != 'unresolved' for r in rows)
        unknown = sum(r is not None and r['status'] == 'unresolved' for r in rows)
        stages.append({'id': stage['id'], 'completed': completed, 'unresolved': unknown,
            'planned': len(rows), 'remaining': len(rows) - completed, 'unstarted': len(rows) - completed - unknown})
    return {'completed_units': sum(s['completed'] for s in stages),
        'unresolved_units': sum(s['unresolved'] for s in stages),
        'planned_units': sum(s['planned'] for s in stages),
        'remaining_units': sum(s['remaining'] for s in stages),
        'unstarted_units': sum(s['unstarted'] for s in stages), 'stages': stages}


class Session:
    """The request seam: durable intent, immutable response and content reuse."""
    def __init__(self, directory, *, namespace, phase, unit, limit, clock=time.time):
        self.directory = session_path(directory)
        if not self.directory.is_relative_to(TEMP):
            if ready_plan(self.directory) is None or not (self.directory / 'authorization.json').exists():
                raise ValueError('task16_live_not_ready')
            if not worker_active(self.directory) or read(self.directory / 'worker.json')['pid'] != os.getpid():
                raise ValueError('task16_request_requires_owning_worker')
        self.namespace, self.phase, self.unit = namespace, phase, unit
        self.limit, self.clock = limit, clock
        self.budget = budget_at(self.directory)
        with LOCK:
            if self.directory not in ATTEMPTS:
                ATTEMPTS[self.directory] = request_rows(self.directory)
        plan = ready_plan(self.directory)
        self.phase_limit = next((s['max_calls'] for s in plan['stages'] if s['id'] == phase), None) if plan else None

    def invoke(self, request, send, *, dependencies):
        request_id = sha(encoded({'namespace': self.namespace, 'dependencies': dependencies, 'request': request}))
        with LOCK:
            request_lock = REQUEST_LOCKS.setdefault((self.directory, request_id), threading.Lock())
        with request_lock:
            return self._invoke(request_id, request, send, dependencies)

    def _invoke(self, request_id, request, send, dependencies):
        if len(encoded(request)) > 128 * 1024:
            raise ValueError('task16_request_size')
        self.budget = budget_at(self.directory)
        base = self.directory / 'calls' / request_id
        intent = base.with_suffix('.intent.json')
        terminal = base.with_suffix('.terminal.json')
        response = base.with_suffix('.response.json')
        with LOCK:
            if terminal.exists():
                prior = read(terminal)
                if prior['status'] != 'ok':
                    raise ValueError('task16_' + prior['status'] + '_not_resent')
                if sha(response.read_bytes()) != prior['response_sha256']:
                    raise ValueError('task16_response_changed')
                return read(response)
            if intent.exists():
                raise ValueError('task16_unresolved_not_resent')
            if stop_requested(self.directory):
                raise ValueError('task16_stop_requested')
            if self.clock() >= instant(self.budget['dispatch_deadline_utc']):
                raise ValueError('task16_dispatch_deadline')
            attempts = ATTEMPTS[self.directory]
            if len(attempts) >= self.budget['max_calls']:
                raise ValueError('task16_call_limit')
            phase_attempts = [a for a in attempts if a['phase'] == self.phase]
            if self.phase_limit is not None and len(phase_attempts) >= self.phase_limit:
                raise ValueError('task16_phase_limit')
            if sum(a['unit'] == self.unit for a in phase_attempts) >= self.limit:
                raise ValueError('task16_unit_limit')
            if new_bytes(self.directory) + 32 * 1024**2 + 464 * 1024 > self.budget['max_new_bytes']:
                raise ValueError('task16_storage_limit')
            write_once(base.with_suffix('.request.json'), request)
            row = {'request_id': request_id, 'namespace': self.namespace,
                'phase': self.phase, 'unit': self.unit, 'started': self.clock(),
                'request_sha256': sha(encoded(request)), 'dependencies_sha256': sha(encoded(dependencies))}
            write_once(self.directory / 'request-index' / (request_id + '.json'), row)
            attempts.append(row)
            write_once(intent, row)
        try:
            reply = send(request)
        except Exception as exc:
            with LOCK:
                write_once(terminal, {'status': 'unresolved', 'usage': None,
                    'reason': type(exc).__name__, 'completed': self.clock()})
            raise ValueError('task16_unresolved') from None
        with LOCK:
            if len(encoded(reply)) > 256 * 1024:
                write_once(terminal, {'status': 'failed', 'usage': reply.get('usage') if isinstance(reply, dict) else None,
                    'reason': 'reply_size', 'completed': self.clock()})
                raise ValueError('task16_failed_reply_size')
            write_once(response, reply)
            succeeded = isinstance(reply, dict) and reply.get('status') == 'completed'
            write_once(terminal, {'status': 'ok' if succeeded else 'failed',
                'response_sha256': sha(response.read_bytes()),
                'usage': reply.get('usage') if isinstance(reply, dict) else None, 'completed': self.clock()})
        if not succeeded:
            raise ValueError('task16_failed_response')
        return reply


def status(directory):
    budget = budget_at(directory)
    plan = ready_plan(directory)
    completed = progress(directory, plan)
    state = 'not_ready' if plan is None else ('complete' if completed['completed_units'] == completed['planned_units']
        else 'blocked_unresolved' if completed['unresolved_units'] else 'ready')
    active = worker_active(directory)
    if active and state != 'complete':
        state = 'running'
    elif state == 'ready' and stop_requested(directory):
        state = 'paused'
    counts, usage, latency = call_counts(directory)
    used_bytes = new_bytes(directory, force=True)
    worker = read(directory / 'worker.json') if (directory / 'worker.json').exists() else {}
    halt_path = directory / 'halts' / (worker.get('generation', 'none') + '.json')
    halt = read(halt_path) if halt_path.exists() else {}
    if plan and not active and (state != 'complete' or used_bytes >= budget['max_new_bytes'] or halt.get('reason')):
        reason = ('task16_original_deadline_expired' if time.time() >= instant(budget['deadline_utc'])
            else 'task16_storage_limit' if used_bytes >= budget['max_new_bytes'] else halt.get('reason'))
        if reason:
            state = 'partial_budget' if reason in BUDGET_STOPS else halt.get('status', state)
    else:
        reason = None
    measured = timing(directory, budget, active)
    measured['request_latency_sum_seconds'] = latency
    cost = {'known_token_subtotal_CNY': (usage['input_tokens'] * budget['input_CNY_per_M'] +
        usage['output_tokens'] * budget['output_CNY_per_M']) / 1e6,
        'fully_known': False, 'cache_CNY_per_M': budget.get('cache_CNY_per_M'),
        'extra_multiplier': budget.get('extra_multiplier'), 'fixed_surcharge_CNY': None}
    return {'status': state, 'ready_for_execution': plan is not None,
        'ready_for_live': plan is not None and plan['kind'] == 'live', 'worker_active': active,
        'mode': plan['kind'] if plan else 'development_only',
        'stop_reason': reason,
        'reason': 'algorithm_and_review_seal_required' if plan is None else None, 'progress': completed,
        'calls': counts, 'usage': usage, 'cost': cost, 'deadline_utc': budget['deadline_utc'],
        'elapsed_seconds': max(0, time.time() - instant(budget['started_at_utc'])),
        'new_bytes': used_bytes, 'timing': measured}


def execute_plan(directory, *, confirm_live=False):
    plan = ready_plan(directory)
    if plan is None:
        raise ValueError('task16_live_not_ready')
    budget = budget_at(directory)
    if time.time() >= instant(budget['deadline_utc']):
        raise ValueError('task16_original_deadline_expired')
    plan_sha = sha((directory / 'run-plan.json').read_bytes())
    seal_sha = sha((directory / 'review-seal.json').read_bytes())
    (directory / 'request-index').mkdir(exist_ok=True)
    write_once(directory / 'run-binding.json', {'plan_sha256': plan_sha, 'seal_sha256': seal_sha,
        'budget_sha256': sha((directory / 'budget.json').read_bytes())})
    if plan['kind'] == 'live':
        if not confirm_live and not (directory / 'authorization.json').exists():
            raise ValueError('task16_confirm_live_required')
        write_once(directory / 'authorization.json', {'plan_sha256': plan_sha,
            'seal_sha256': seal_sha, 'explicit_start': True})
    else:
        def fixture_guard(event, args):
            if event.startswith('socket.') or event == 'subprocess.Popen':
                raise PermissionError('task16_fixture_network_and_children_denied')
        sys.addaudithook(fixture_guard)
    spec = importlib.util.spec_from_file_location('task16_execution_worker', verified_ref(plan['worker']))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, 'validate_plan'):
        module.validate_plan(plan)
    for stage in plan['stages']:
        with activity(directory, stage['category']):
            execute_stage(directory, plan, stage, module, plan_sha, budget)
        if any(s['id'] == stage['id'] and s['unresolved'] for s in progress(directory, plan)['stages']):
            break
    return status(directory)


def execute_stage(directory, plan, stage, module, plan_sha, budget):
    groups = {}
    for unit in stage['units']:
        groups.setdefault(unit['root_id'], []).append(unit)

    def execute_root(units):
        for unit in units:
            if observed_unit(directory, unit, plan_sha) is not None:
                continue
            if stop_requested(directory):
                raise ValueError('task16_stop_requested')
            if time.time() >= instant(budget['deadline_utc']):
                raise ValueError('task16_original_deadline_expired')
            session = Session(directory, namespace=plan['namespace'], phase=stage['id'],
                unit=unit['id'], limit=unit['limit'])
            try:
                output = module.execute_unit(unit, session)
                state = output['status']
                if state not in ('ok', 'failed_model', 'failed_protocol'):
                    raise ValueError('task16_invalid_unit_terminal')
            except ValueError as exc:
                if str(exc).startswith('task16_unresolved'):
                    state, output = 'unresolved', None
                elif str(exc).startswith('task16_failed'):
                    state, output = 'failed_model', None
                else:
                    raise
            if len(encoded(output)) > 64 * 1024:
                state, output = 'failed_protocol', {'reason': 'unit_output_size'}
            artifact = unit_path(directory, unit)
            row = {'plan_sha256': plan_sha, 'unit_sha256': sha(encoded(unit)),
                'status': state, 'output': output}
            write_once(artifact, row | {'checksum_sha256': sha(encoded(row))})

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execute_root, units) for units in groups.values()]
        for future in futures:
            future.result()


def run_worker(directory, *, generation, confirm_live=False):
    if ready_plan(directory) is None:
        raise ValueError('task16_live_not_ready')
    with coordinator(directory, generation):
        try:
            with storage_guard(directory):
                execute_plan(directory, confirm_live=confirm_live)
        except ValueError as exc:
            reason = str(exc)
            persist_halt(directory, reason)
            if reason != 'task16_stop_requested' and reason not in BUDGET_STOPS:
                raise
    return status(directory)


def supervise(directory, *, confirm_live=False):
    if ready_plan(directory) is None:
        raise ValueError('task16_live_not_ready')
    request_rows(directory)
    remaining = instant(budget_at(directory)['deadline_utc']) - time.time()
    if remaining <= 0:
        raise ValueError('task16_original_deadline_expired')
    from formal_process import run_process
    generation = uuid.uuid4().hex
    log = directory / 'logs' / (generation + '.worker.stdout')
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(PROJECT / 'task16_control.py'), 'worker', '--session', str(directory),
        '--generation', generation]
    if confirm_live:
        command.append('--confirm-live')
    measured = run_process(command, log, cwd=PROJECT, seconds=remaining, memory_bytes=4 * 1024**3)
    write_once(directory / 'supervisions' / (log.stem + '.json'), measured | {'generation': generation})
    result = status(directory)
    current_worker = read(directory / 'worker.json') if (directory / 'worker.json').exists() else {}
    if (measured['exit_code'] and current_worker.get('generation') == generation
            and not result['worker_active'] and not result['status'].startswith('partial')):
        reason = measured['stop_reason'] or 'worker_exit_' + str(measured['exit_code'])
        persist_halt(directory, reason, generation=generation)
        result = status(directory)
    result['supervisor'] = measured
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'start', 'resume', 'worker', 'stop',
        'development-begin', 'development-end'])
    parser.add_argument('--session', default=str(DEFAULT_SESSION))
    parser.add_argument('--confirm-live', action='store_true')
    parser.add_argument('--generation')
    args = parser.parse_args()
    try:
        if Path(sys.prefix).resolve() != PROJECT / '.conda/envs/Thesis':
            raise ValueError('task16_requires_Thesis_conda')
        directory = session_path(args.session)
        if args.action == 'status':
            result = status(directory)
        elif args.action == 'stop':
            result = request_stop(directory)
        elif args.action.startswith('development-'):
            result = development(directory, end=args.action == 'development-end')
        elif args.action == 'worker':
            if sys.stdin.readline().strip() != 'GO':
                raise ValueError('task16_worker_requires_supervisor')
            if args.generation is None or uuid.UUID(args.generation).hex != args.generation:
                raise ValueError('task16_worker_requires_generation')
            result = run_worker(directory, generation=args.generation, confirm_live=args.confirm_live)
        else:
            result = supervise(directory, confirm_live=args.confirm_live)
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'status': 'rejected', 'reason': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
