"""Independent formal coordinator and durable, at-most-once task/send ledger."""
import json
import os
from pathlib import Path
import time
from collections import Counter

from evidence_access import PROJECT, digest, encoded
from formal_runtime import CONFIG, OUTPUT, PLAN, PLAN_ID, PACKAGE, AUTHORIZATION, load_config, reference


def require_authorization(cfg, path=PACKAGE / 'authorization.json'):
    if not Path(path).is_file():
        raise OSError('formal_start_confirmation_required')
    grant = json.loads(Path(path).read_bytes())
    if (cfg['status'] != 'frozen_pending_confirmation' or grant.get('status') != 'authorized'
            or grant.get('configuration_id') != cfg['configuration_id']
            or grant.get('plan_id') != PLAN_ID or grant.get('authorization_id') != AUTHORIZATION
            or not grant.get('human_confirmation')):
        raise OSError('formal_start_confirmation_required')
    ready = json.loads((PACKAGE / 'ready.json').read_bytes())
    if (ready['configuration_id'] != cfg['configuration_id'] or ready['code_identity'] != cfg['code_identity']
            or any(ready.get(k) != 'PASS' for k in ('standards', 'spec', 'tests'))):
        raise OSError('formal_candidate_not_reviewed')
    return grant


def authorize(confirmation):
    cfg = load_config()
    if confirmation != '确认启动15.100用户全场景正式实验':
        raise ValueError('formal_confirmation_text')
    row = {'status': 'authorized', 'authorization_id': AUTHORIZATION, 'plan_id': PLAN_ID,
        'configuration_id': cfg['configuration_id'], 'human_confirmation': confirmation,
        'utc_ms': int(time.time() * 1000), 'scope': 'all_original_tasks_all_batches_one_attempt'}
    # Review is required before a grant is recorded, as well as before execution.
    ready = json.loads((PACKAGE / 'ready.json').read_bytes())
    if (cfg['status'] != 'frozen_pending_confirmation' or ready['configuration_id'] != cfg['configuration_id']
            or ready['code_identity'] != cfg['code_identity']
            or any(ready.get(k) != 'PASS' for k in ('standards', 'spec', 'tests'))):
        raise OSError('formal_candidate_not_reviewed')
    store(PACKAGE / 'authorization.json', row)
    return row


def store(path, value):
    """Exclusive durable record. Existing observations are never overwritten."""
    with Path(path).open('xb') as stream:
        stream.write(encoded(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


class RunLedger:
    def __init__(self, root, cfg, tasks):
        self.root, self.cfg = Path(root), cfg
        self.tasks = {t['task_key']: t for t in tasks}
        if (len(self.tasks) != len(tasks) or sum(t['uses_model'] for t in tasks) * cfg['run_model_calls'] > cfg['generate_limit']):
            raise ValueError('formal_generation_allocation')

    def directory(self, key):
        if key not in self.tasks or '/' in key or '\\' in key or key in ('.', '..'):
            raise ValueError('unknown_formal_task')
        return self.root / 'runs' / ('T15-' + key)

    def claim_task(self, key):
        target = self.directory(key)
        if target.exists():
            raise FileExistsError('task_already_claimed')
        target.mkdir(parents=True, exist_ok=False)
        row = {'task_key': key, 'plan_id': PLAN_ID, 'configuration_id': self.cfg['configuration_id'],
            'run_id': 'T15-' + key, 'started': True, 'terminal': 'running',
            'utc_ms': int(time.time() * 1000)}
        store(target / 'task.intent.json', row)
        return row

    def claim_request(self, key, body):
        target = self.directory(key)
        intent = json.loads((target / 'task.intent.json').read_bytes())
        cap = body.get('max_output_tokens')
        rows = list(target.glob('send-*.json'))
        if (intent['configuration_id'] != self.cfg['configuration_id'] or (target / 'result.json').exists()
                or not self.tasks[key]['uses_model'] or len(rows) >= self.cfg['run_model_calls']
                or body.get('model') != 'gpt-6-luna' or type(cap) is not int or not 0 < cap <= 8192
                or body.get('text', {}).get('format', {}).get('name') == 'rsm_final_submit' and cap > 1500):
            raise OSError('formal_generation_limit')
        from fourrouter_probe import _request_bytes
        raw = _request_bytes(body, 2 * 1024**2)
        row = {'task_key': key, 'configuration_id': self.cfg['configuration_id'], 'sequence': len(rows) + 1,
            'utc_ms': int(time.time() * 1000), 'body_sha256': digest(encoded(body)),
            'actual_POST_bytes': len(raw), 'actual_POST_sha256': digest(raw), 'output_cap': cap,
            'state': 'send_intent_not_refundable'}
        store(target / ('send-%04d.json' % row['sequence']), row)
        return row

    def finish_task(self, key, observed):
        target = self.directory(key)
        allowed = ('released', 'valid_empty', 'failed_model', 'failed_protocol', 'failed_source',
            'blocked_evidence', 'incomplete_budget', 'incomplete_count', 'incomplete_deadline', 'unresolved_attempt')
        if observed['terminal'] not in allowed:
            raise ValueError('formal_terminal')
        row = observed | {'task_key': key, 'plan_id': PLAN_ID, 'run_id': 'T15-' + key,
            'configuration_id': self.cfg['configuration_id'], 'started': True,
            'generations_reserved': len(list(target.glob('send-*.json'))), 'cost': None}
        store(target / 'result.json', row)
        return row

    def recover_interrupted(self):
        for key in self.tasks:
            target = self.directory(key)
            if target.exists() and not (target / 'result.json').exists():
                intent = target / 'task.intent.json'
                if intent.exists():
                    record = json.loads(intent.read_bytes())
                    if record['configuration_id'] != self.cfg['configuration_id'] or record['task_key'] != key:
                        raise ValueError('formal_intent_binding')
                else:
                    session = json.loads((self.root / 'session.json').read_bytes())
                    if session['configuration_id'] != self.cfg['configuration_id']:
                        raise ValueError('formal_intent_binding')
                self.finish_task(key, {'terminal': 'unresolved_attempt', 'reason': 'interrupted_no_resend',
                    'usage': None, 'runtime_seconds': None})

    def pending(self):
        return [key for key in self.tasks if not self.directory(key).exists()]

    def status(self):
        terminals, generations, seconds, reserved_bytes = Counter(), 0, 0, 0
        for key in self.tasks:
            target = self.directory(key)
            if not target.exists():
                continue
            sends = sorted(target.glob('send-*.json'))
            if len(sends) > self.cfg['run_model_calls'] or sends and not self.tasks[key]['uses_model']:
                raise ValueError('formal_send_ledger_limit')
            for sequence, path in enumerate(sends, 1):
                row = json.loads(path.read_bytes())
                if (row['task_key'] != key or row['configuration_id'] != self.cfg['configuration_id']
                        or row['sequence'] != sequence):
                    raise ValueError('formal_send_ledger_binding')
                generations += 1
            result = target / 'result.json'
            if result.exists():
                row = json.loads(result.read_bytes())
                if row['task_key'] != key or row['configuration_id'] != self.cfg['configuration_id']:
                    raise ValueError('formal_result_binding')
                terminals[row['terminal']] += 1
            else:
                terminals['running'] += 1
            resource = target / 'process.json'
            if resource.exists():
                receipt = json.loads(resource.read_bytes())
                seconds += receipt['charged_seconds']
                reserved_bytes += receipt['retained_bytes']
            else:
                seconds += self.cfg.get('run_watchdog_seconds', 1800)
                reserved_bytes += self.cfg.get('run_storage_limit_bytes', 128 * 1024**2)
        if generations > self.cfg['generate_limit']:
            raise ValueError('formal_global_generation_limit')
        return {'tasks': len(self.tasks), 'pending': len(self.pending()), 'terminals': dict(terminals),
            'generations_reserved': generations, 'charged_active_seconds': seconds,
            'storage_accounted_bytes': reserved_bytes, 'pricing': None, 'cost': None}


def ledger_for(cfg):
    from experiment_runner import _task_plan
    _, manifest, rows = _task_plan(PLAN)
    if manifest['plan_id'] != PLAN_ID or manifest['counts'] != {
            'users': 100, 'development_overlap': 0, 'scenarios': 18, 'bindings': 1800, 'tasks': 5000, 'model_tasks': 3400}:
        raise ValueError('formal_plan_counts')
    return RunLedger(OUTPUT, cfg, rows['tasks.jsonl'])


def worker(key):
    from formal_runtime import prepare_task
    from p1_runtime import build_runtime
    from p1_storage import P1StorageGuard
    cfg = load_config()
    require_authorization(cfg)
    ledger = ledger_for(cfg)
    target = ledger.directory(key)
    intent = json.loads((target / 'task.intent.json').read_bytes())
    if intent['configuration_id'] != cfg['configuration_id'] or (target / 'result.json').exists():
        raise OSError('formal_worker_intent')
    store(target / 'worker.claim.json', {'configuration_id': cfg['configuration_id'], 'task_key': key})
    with P1StorageGuard(target, cfg['run_storage_limit_bytes'] - 2 * 1024**2, formal=True) as guard:
        prepared = prepare_task(key)
        method = prepared['assembly']['binding']['method']
        if method != 'R':
            guard.authorize_formal(cfg['configuration_id'])
            guard.claim_S_request = lambda body: ledger.claim_request(key, body)
        run = build_runtime(prepared['assembly'], prepared['configuration'], method,
            counter=None, output_root=OUTPUT / 'runs', storage_guard=guard)
        observed = run.run()
        row = {k: observed.get(k) for k in ('terminal', 'reason', 'delivered', 'G', 'cursor', 'stop_reason',
            'acquired_ref', 'publication_path', 'audit_path')}
        for name, path in (('audit_ref', row['audit_path']), ('publication_ref', row['publication_path']),
                ('budget_ref', target / 'budget.jsonl')):
            if path and Path(path).exists():
                row[name] = reference(path)
        row.update(method=method, model_calls=len(run.state['messages']),
            usage=observed['budget']['usage'], release_scope=observed['release_scope'],
            guard_denied=guard.attempts, guard_allowed=guard.allowed, count_api=0, other_api=0)
        sent = [m['response'].get('provider_requests_sent') for m in run.state['messages']]
        row.update(provider_requests_sent=sum(sent) if all(v is not None for v in sent) else None,
            provider_requests_known_subtotal=sum(v for v in sent if v is not None))
        ledger.finish_task(key, row)
    return 0


def process_task(ledger, key):
    import sys
    from formal_process import run_process
    cfg = ledger.cfg
    target = ledger.directory(key)
    ledger.claim_task(key)
    try:
        receipt = run_process([sys.executable, '-B', str(PROJECT / 'formal_experiment.py'), '_worker', key],
            target / 'worker.stdout', cwd=PROJECT, seconds=cfg['run_watchdog_seconds'],
            memory_bytes=cfg['run_memory_limit_bytes'])
    except (OSError, ValueError):
        receipt = {'exit_code': 2, 'stop_reason': 'process_guard_failed', 'charged_seconds': cfg['run_watchdog_seconds'],
            'measured_seconds': None, 'job_peak_commit_bytes': None, 'job_write_transfer_bytes': None}
    if not (target / 'result.json').exists():
        ledger.finish_task(key, {'terminal': 'unresolved_attempt', 'reason': receipt['stop_reason'] or 'worker_interrupted',
            'usage': None, 'runtime_seconds': receipt['measured_seconds']})
    receipt['retained_bytes'] = sum(p.stat().st_size for p in target.rglob('*') if p.is_file()) + 4096
    store(target / 'process.json', receipt)
    return receipt


def run_batches():
    import msvcrt
    import shutil
    from concurrent.futures import ThreadPoolExecutor
    cfg = load_config()
    require_authorization(cfg)
    if cfg['concurrency'] != 2 or cfg['batch_size'] != 50 or cfg['retry'] != 0:
        raise ValueError('formal_scheduling_configuration')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / 'coordinator.lock').open('a+b') as lock:
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            session = OUTPUT / 'session.json'
            if session.exists():
                if json.loads(session.read_bytes()) != {'configuration_id': cfg['configuration_id'], 'plan_id': PLAN_ID}:
                    raise ValueError('formal_session_binding')
            else:
                store(session, {'configuration_id': cfg['configuration_id'], 'plan_id': PLAN_ID})
            ledger = ledger_for(cfg)
            ledger.recover_interrupted()
            keys = list(ledger.tasks)
            with ThreadPoolExecutor(max_workers=cfg['concurrency']) as pool:
                state = ledger.status()
                for offset in range(0, len(keys), cfg['batch_size']):
                    original_batch = keys[offset:offset + cfg['batch_size']]
                    pending = set(ledger.pending())
                    todo = [key for key in original_batch if key in pending]
                    if not todo:
                        continue
                    used = max(state['storage_accounted_bytes'], sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()))
                    for start in range(0, len(todo), cfg['concurrency']):
                        group = todo[start:start + cfg['concurrency']]
                        if (OUTPUT / 'STOP').exists():
                            return {'stopped': 'operator_STOP', **ledger.status()}
                        if state['charged_active_seconds'] + len(group) * cfg['run_watchdog_seconds'] > cfg['active_seconds_limit']:
                            return {'stopped': 'active_time_limit', **ledger.status()}
                        needed = len(group) * cfg['run_storage_limit_bytes'] + cfg['control_reserve_bytes']
                        if (used + needed > cfg['shared_storage_limit_bytes']
                                or shutil.disk_usage(OUTPUT).free < needed + cfg['minimum_free_bytes']):
                            return {'stopped': 'storage_limit', **ledger.status()}
                        futures = [pool.submit(process_task, ledger, key) for key in group]
                        for future in futures:
                            receipt = future.result()
                            used += receipt['retained_bytes']
                            state['charged_active_seconds'] += receipt['charged_seconds']
                    record = {'batch': offset // cfg['batch_size'] + 1, 'original_task_keys': original_batch,
                        'configuration_id': cfg['configuration_id'], **ledger.status()}
                    path = OUTPUT / ('batch-%03d.json' % record['batch'])
                    if not path.exists():
                        store(path, record)
                    print(json.dumps({'batch': record['batch'], 'pending': record['pending'],
                        'generations_reserved': record['generations_reserved'], 'terminals': record['terminals']}), flush=True)
                    state = ledger.status()
            return {'stopped': 'all_original_tasks_terminal', **ledger.status()}
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main(argv=None):
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('status', 'prepare', 'authorize', 'run', 'evaluate', '_worker'))
    parser.add_argument('value', nargs='?')
    args = parser.parse_args(argv)
    try:
        if Path(sys.prefix).resolve() != PROJECT / '.conda/envs/Thesis':
            raise OSError('Thesis_conda_required')
        if args.command == '_worker':
            if sys.stdin.buffer.readline() != b'GO\n':
                raise OSError('formal_parent_required')
            return worker(args.value)
        if args.command == 'authorize':
            result = authorize(args.value)
        elif args.command == 'run':
            result = run_batches()
            if result['stopped'] == 'all_original_tasks_terminal':
                from formal_evaluation import evaluate
                result['evaluation'] = evaluate()
        elif args.command == 'evaluate':
            from formal_evaluation import evaluate
            result = evaluate()
        elif args.command == 'prepare':
            from formal_runtime import prepare_task
            ready = prepare_task(args.value)
            result = {'task_key': args.value, 'plan_id': ready['assembly']['plan_id'],
                'method': ready['assembly']['binding']['method'], 'started': False, 'supplier_calls': 0}
        else:
            cfg = load_config()
            result = {'configuration_id': cfg['configuration_id'], 'authorized': (PACKAGE / 'authorization.json').exists(),
                **ledger_for(cfg).status()}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Only local fixed codes. Never persist provider or credential exception prose.
        print(json.dumps({'status': 'stopped', 'error_type': type(exc).__name__,
            'code': str(exc) if str(exc).startswith(('formal_', 'Thesis_')) else 'formal_entry_failed'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
