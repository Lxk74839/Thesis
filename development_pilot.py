"""Task14's frozen D1 development session; no formal experiment authority."""
import hashlib
import json
import os
from pathlib import Path
import time
import copy

from evidence_access import PROJECT

AUTHORIZATION = 'T14-DEVELOPMENT-CLOSEOUT-20261021'
PACKAGE = PROJECT / '.scratch/ticket14-closeout-20261021'
OUTPUT = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/p1'
CONTROL = OUTPUT / AUTHORIZATION
METADATA_RESERVE = 2 * 1024**2


def storage_headroom(root, limit=1024**3, reserve=METADATA_RESERVE):
    """Reserve bounded parent stdout/control/error files outside the child's write wrappers."""
    used = sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
    if used + reserve > limit:
        raise OSError('development_control_storage_balance')
    return limit - reserve


def model_binding():
    from fourrouter_probe import PUBLIC_CONFIG, _public_binding
    return _public_binding(PUBLIC_CONFIG) | {'execution_kind': 'fourrouter_responses',
        'project_id': 'Thesis-task14-development', 'provenance': '4router',
        'execution_authorized': True, 'development_authorization': AUTHORIZATION,
        'max_request_bytes': 2 * 1024**2, 'max_output_tokens': 8192,
        'pricing': None, 'context_token_limit': None, 'api_budget_microusd': None}


def budget_tables(calls=24):
    from p1_engineering import SEngineeringBudget
    limits = dict.fromkeys(SEngineeringBudget.resources, 100000)
    limits.update(model_calls=calls, request_output_tokens=(calls - 1) * 8192 + 1500,
        candidates=1494, retries=0, elapsed_ms=1780000)
    reserve = dict.fromkeys(SEngineeringBudget.resources, 0)
    reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=145000, logical_tools=64)
    return limits, reserve


def claim_request(path, body, run_id, *, diagnostic=False):
    """Durable send intent, never refunded after failed or uncertain transmission."""
    path = Path(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    cap = body.get('max_output_tokens')
    if (body.get('model') != 'gpt-6-luna' or type(cap) is not int or not 0 < cap <= 8192
            or body.get('text', {}).get('format', {}).get('name') == 'rsm_final_submit' and cap > 1500
            or len(rows) >= 160 or diagnostic and sum(r.get('diagnostic') is True for r in rows) >= 6):
        raise OSError('development_generation_limit')
    from fourrouter_probe import _request_bytes
    raw = _request_bytes(body, 2 * 1024**2)
    row = {'run_id': run_id, 'sequence': len(rows) + 1, 'output_cap': cap,
        'diagnostic': diagnostic, 'utc_ms': int(time.time() * 1000),
        'body_sha256': hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest(),
        'actual_POST_bytes': len(raw), 'actual_POST_sha256': hashlib.sha256(raw).hexdigest()}
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return row


def authorized(binding):
    return binding.get('development_authorization') == AUTHORIZATION


def task_allowed(binding):
    from experiment_runner import _task_plan
    from p1_runtime import PILOT, PILOT_ID, PLAN_ID, D1
    if not authorized(binding) or binding.get('authorization_id') != AUTHORIZATION:
        return False
    _, manifest, rows = _task_plan(PILOT)
    task = next((t for t in rows['tasks.jsonl'] if t['task_key'] == binding.get('task_key')), None)
    if task is None or manifest['pilot_id'] != PILOT_ID or manifest['parent_plan_id'] != PLAN_ID:
        return False
    relation = next(r for r in rows['user-scenarios.jsonl'] if r['binding_id'] == task['binding_id'])
    scene = next(s for s in rows['scenes.jsonl'] if s['view_id'] == relation['view_id'])
    return (task['method'] == binding.get('method') and relation['root_task_id'] == binding.get('root_task_id') == D1
        and binding.get('pilot_id') == PILOT_ID
        and (scene['label'], task['method']) in {('V00', 'S'), ('V00', 'M'), ('V01', 'M'),
            ('V05', 'M'), ('V06', 'M'), ('Q1', 'M'), ('Q2', 'M')}
        and binding.get('run_id', '').startswith('T14-D1-' + scene['label'] + '-' + task['method'] + '-'))


def prepare_task(label, method, run_id):
    """Resolve a frozen pilot member before creating an attempt or reading credentials."""
    from experiment_runner import _task_plan, assemble_task
    from p1_runtime import PILOT, PILOT_ID, PLAN_ID, frozen_snapshot_error
    _, manifest, rows = _task_plan(PILOT)
    scene = next((s for s in rows['scenes.jsonl'] if s['label'] == label), None)
    if scene is None or manifest['pilot_id'] != PILOT_ID or manifest['parent_plan_id'] != PLAN_ID:
        raise ValueError('development_plan_identity')
    links = {r['binding_id'] for r in rows['user-scenarios.jsonl'] if r['view_id'] == scene['view_id']}
    task = next((t for t in rows['tasks.jsonl'] if t['method'] == method and t['binding_id'] in links), None)
    probe = {'task_key': task['task_key'] if task else None, 'method': method, 'run_id': run_id,
        'authorization_id': AUTHORIZATION, 'development_authorization': AUTHORIZATION,
        'pilot_id': PILOT_ID, 'root_task_id': '015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e'}
    if not task_allowed(probe):
        raise ValueError('development_task_not_authorized')
    assembly = assemble_task(PILOT, task['task_key'], execution_record={'run_id': run_id})
    assembly['binding'].update({k: v for k, v in probe.items() if k not in ('task_key', 'method', 'run_id', 'root_task_id')})
    if scene['arm'] == 'quality':
        from quality_fusion import RULES
        from evidence_access import digest, encoded
        b = assembly['binding']
        b['prefix_limit'] = json.loads((PACKAGE / 'config.json').read_bytes())['quality_prefix_limit']
        b['fusion'] = {'schema_version': 'fusion-binding-0.1.0', 'task_id': b['root_task_id'],
            **{k: copy.deepcopy(b[k]) for k in ('C', 'C_sha256', 'H_sha256', 'base_scores',
                'base_score_sha256', 'snapshot_id', 'verify_at_ms', 'principal_id', 'K')},
            'base_score_version': assembly['root']['score_version'], 'contract_sha256': digest(encoded(RULES)),
            'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
            'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
    error = frozen_snapshot_error(assembly['binding'], assembly['snapshot_ref'])
    if error:
        raise ValueError(error)
    limits, reserve = budget_tables()
    cfg = {'authorization_id': AUTHORIZATION, 'model_binding': model_binding() | {'wire_schema_subset': True},
        'limits': {method: limits}, 'final_reserve': {method: reserve}}
    return {'terminal': 'ready', 'started': False, 'assembly': assembly, 'configuration': cfg}


def preflight_task(label, method):
    """Full frozen assembly and production preflight, without a real execution claim."""
    import tempfile
    from p1_runtime import build_runtime
    from p1_storage import P1StorageGuard
    run_id = 'T14-D1-' + label + '-' + method + '-nonexecuting'
    parent = PROJECT / '.tmp/recommendation-runtime'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp, P1StorageGuard(tmp, 1024**3, development=True):
        prepared = prepare_task(label, method, run_id)
        runtime = build_runtime(prepared['assembly'], prepared['configuration'], method,
            counter=None, output_root=Path(tmp))
        runtime._preflight()
        logical = runtime._composed('需求解析', 'analysis', '需求解析')
        wire = runtime.model.prepare(logical)
        context = logical['messages'][-1]['content']['runtime']
        binding = runtime.binding
        if (context['candidate_base_scores'] != dict(zip(binding['C'], binding['base_scores']))
                or context['candidate_batches'] != dict(zip(binding['C'], binding['batches']))
                or context['history'] != json.loads(runtime.initial_messages[0]['content'])['H']
                or wire['status'] != 'prepared' or wire.get('missing')):
            raise ValueError('development_full_input_projection')
        return {'label': label, 'method': method, 'task_key': binding['task_key'], 'terminal': 'ready',
            'started': False, 'candidate_count': len(binding['C']), 'C_sha256': binding['C_sha256'],
            'H_sha256': binding['H_sha256'], 'request_bytes': wire['wire_bytes'], 'model_calls': 0,
            'count_api': 0, 'other_api': 0}


def execute_task(command, run_id):
    from p1_runtime import build_runtime, PILOT_ID
    from p1_storage import P1StorageGuard
    from evidence_access import digest
    _, label, method = command.split('-')
    target = OUTPUT / run_id
    if target.exists():
        raise FileExistsError('development_attempt_already_exists')
    path = CONTROL / 'requests.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    calls = min(24, 160 - len(rows))
    if calls < 2:
        raise OSError('development_generation_balance')
    guard = P1StorageGuard(OUTPUT, storage_headroom(OUTPUT), run_root=target,
        run_limit_bytes=128 * 1024**2 - METADATA_RESERVE, development=True)
    with guard:
        prepared = prepare_task(label, method, run_id)
        cfg = prepared['configuration']
        cfg['limits'][method], cfg['final_reserve'][method] = budget_tables(calls)
        guard.authorize_development(AUTHORIZATION)
        guard.claim_S_request = lambda body: claim_request(CONTROL / 'requests.jsonl', body, run_id)
        target.mkdir(exist_ok=False)
        (target / 'attempt.json').write_text(json.dumps({'run_id': run_id, 'task_key': prepared['assembly']['task_key'],
            'authorization_id': AUTHORIZATION, 'purpose': 'development_task', 'label': label, 'method': method}))
        ready = json.loads((PACKAGE / 'ready.json').read_bytes())
        prepared['assembly']['binding']['implementation_candidate'] = ready['candidate']
        runtime = build_runtime(prepared['assembly'], cfg, method, counter=None, storage_guard=guard)
        observed = runtime.run()
        record = {k: observed.get(k) for k in ('run_id', 'terminal', 'reason', 'delivered', 'G', 'cursor',
            'stop_reason', 'acquired_ref', 'publication_path', 'audit_path', 'dispatch_checkpoint')}
        record.update(task_key=runtime.binding['task_key'], plan_id=PILOT_ID, started=True, label=label,
            method=method, candidate_count=len(runtime.binding['C']),
            acquired_candidate_count=len(runtime.evidence.audit_view()['acquired']['candidates']),
            verified_count=len(runtime.state['assessments']), model_calls=len(runtime.state['messages']),
            responses=[{'role': m['role'], 'output_kind': m['request']['output_kind'],
                'status': m['response']['status'], 'usage': m['response']['usage'],
                'raw_response': m['response'].get('raw_response'),
                'protocol_diagnostic': m['response'].get('protocol_diagnostic')} for m in runtime.state['messages']],
            budget_usage=observed['budget']['usage'], metering_status='unknown/incomplete', cost=None,
            engineering_limits_settled=observed['budget'].get('engineering_limits_settled'),
            guard_allowed=guard.allowed, guard_denied=guard.attempts,
            storage_charged_bytes=guard.charged_bytes, run_storage_charged_bytes=guard.run_charged_bytes,
            count_api=0, other_api=0)
        for name, path in (('audit_ref', record['audit_path']), ('publication_ref', record['publication_path']),
                ('budget_ref', target / 'budget.jsonl')):
            if path:
                raw = Path(path).read_bytes()
                record[name] = {'path': Path(path).relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}
        (target / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('run_id', 'terminal', 'reason', 'model_calls', 'acquired_candidate_count', 'verified_count', 'publication_path')}))
    return 0 if record['terminal'] in ('released', 'valid_empty') else 2


def invoke_once(adapter, logical):
    """Diagnostic uses the production prepare/reserve/invoke chain, no tool execution."""
    from p1_engineering import reservation_deadline
    prepared = adapter.prepare(logical)
    if prepared['status'] != 'prepared' or prepared.get('missing'):
        raise ValueError('diagnostic_prepare_failed')
    budget = adapter.root_budget
    reservation = budget.reserve({'kind': 'model', 'request_id': logical['request_id'],
        'prepared_id': prepared['prepared_id'], 'wire_sha256': prepared['wire_sha256'], 'count_receipt_id': None},
        {'model_calls': 1, 'request_output_tokens': logical['max_output_tokens'], 'elapsed_ms': 135000},
        phase='work', retry_of=None)
    if reservation['status'] != 'reserved':
        raise ValueError('diagnostic_reservation_failed')
    request = logical | {'schema_version': 'rsm-model-request-0.3.0', 'input_token_upper_bound': None,
        'prepared_id': prepared['prepared_id'], 'count_receipt_id': None,
        'reservation_id': reservation['reservation_id'],
        'deadline_ms': int(reservation_deadline(budget, reservation['reservation_id']))}
    response = adapter.invoke(request)
    budget.settle(reservation['reservation_id'], {'status': response['status'],
        'usage': response['usage'] | {'model_calls': int(response['attempted'])}})
    return response, prepared['wire_bytes'], prepared['wire_sha256']


def diagnostic_request(mode, run_id):
    from p1_runtime import PILOT, TASK_KEYS, assemble_task
    from provider_openai import object_schema
    from evidence_access import EvidenceSession
    if mode.startswith('full'):
        path = OUTPUT / 'P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A7/audit.json'
        original = json.loads(path.read_bytes())['messages'][3]['request']
        logical = {k: copy.deepcopy(v) for k, v in original.items() if k not in (
            'prepared_id', 'count_receipt_id', 'input_token_upper_bound', 'deadline_ms', 'reservation_id')}
        binding = assemble_task(PILOT, TASK_KEYS['S'], execution_record={'run_id': run_id})['binding']
        binding.update(authorization_id=AUTHORIZATION, development_authorization=AUTHORIZATION,
            project_id='Thesis-task14-development', pilot_id='6353afe1bf05e4eadd56216d64bb5d29181798e29c6edf9468f9d537e10c1af1')
    else:
        binding = {'run_id': run_id, 'root_task_id': 'PUBLIC-ROOT', 'method': 'S',
            'fixture': 'public_runtime_adapter', 'project_id': 'Thesis-task14-development',
            'development_authorization': AUTHORIZATION}
        logical = {'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': 'fourrouter_responses',
            'role': '单智能体', 'reply_to': None, 'model_id': 'gpt-6-luna', 'output_kind': 'acquire',
            'tools': EvidenceSession.tool_schemas(batch=True) + [{'name': 'candidate_page',
                'version': 'joint-page-0.1.0', 'input_schema': object_schema({
                    'order': {'type': 'string', 'enum': ['parent', 'base']}, 'cursor': {'type': ['string', 'null']}})}],
            'output_schema': object_schema({'kind': {'type': 'string', 'enum': ['acquire']},
                'data': object_schema({'done': {'type': 'boolean', 'enum': [True]},
                    'plan_sha256': {'type': 'string'}, 'processed': {'type': 'array', 'items': {'type': 'string'}}})}),
            'messages': [{'role': 'system', 'content': 'PUBLIC fictional diagnostic. Call acquire_batch once. '
                'Use schema_version acquisition-batch-0.1.0, start_candidate PUBLIC-A, candidate_limit 1, '
                'claim_ids ["c1","c2"], max_list_pages 32, max_read_batches 32, stop_policy first_10_qualified. '
                'Do not return a completion before the tool result.'},
                {'role': 'user', 'content': 'PUBLIC-A is a fictional grain candidate. Obtain its evidence using the tool.'}]}
    logical.update(schema_version='rsm-model-prepare-0.1.0', run_id=run_id,
        request_id=run_id + ':1', attempt_id=run_id + ':1', session_id=run_id + ':single', max_output_tokens=512)
    if mode.endswith('no_tools'):
        logical['tools'] = []
    if mode.endswith('batch_only'):
        logical['tools'] = [t for t in logical['tools'] if t['name'] == 'acquire_batch']
    return logical, binding


def diagnose(mode, run_id):
    from p1_storage import P1StorageGuard
    from p1_engineering import SEngineeringBudget
    from model_adapter import ModelAdapter
    from provider_fourrouter import make_sender
    logical, binding = diagnostic_request(mode, run_id)
    target = OUTPUT / run_id
    limits, reserve = budget_tables()
    guard = P1StorageGuard(OUTPUT, storage_headroom(OUTPUT), run_root=target,
        run_limit_bytes=128 * 1024**2 - METADATA_RESERVE, development=True)
    with guard:
        guard.authorize_development(AUTHORIZATION)
        CONTROL.mkdir(exist_ok=True)
        target.mkdir(exist_ok=False)
        (target / 'execution-claim.json').write_text(json.dumps({'run_id': run_id, 'purpose': 'diagnostic', 'mode': mode}))
        budget = SEngineeringBudget(binding, limits, reserve,
            clock=lambda: time.monotonic() * 1000, journal_path=target / 'budget.jsonl')
        guard.claim_S_request = lambda body: claim_request(CONTROL / 'requests.jsonl', body, run_id, diagnostic=True)
        capability = model_binding() | {'wire_schema_subset': mode.endswith('supported')}
        adapter = ModelAdapter(make_sender(clock=budget.clock, max_request_bytes=2 * 1024**2,
            http_timeout_seconds=120, storage_guard=guard), capability_binding=capability, root_budget=budget)
        response, size, wire_hash = invoke_once(adapter, logical)
        record = {'run_id': run_id, 'purpose': 'diagnostic', 'mode': mode, 'request_body_bytes': size,
            'wire_sha256': wire_hash, 'status': response['status'], 'message': response.get('message'),
            'usage': response['usage'], 'raw_response': response.get('raw_response'),
            'protocol_diagnostic': response.get('protocol_diagnostic'),
            'count_api': 0, 'other_api': 0, 'cost': None, 'guard_allowed': guard.allowed,
            'guard_denied': guard.attempts, 'storage_charged_bytes': guard.charged_bytes}
        (target / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'run_id': run_id, 'status': record['status'], 'http_status':
        (record['raw_response'] or {}).get('http_status'), 'request_bytes': size}))
    return 0 if response['status'] == 'ok' else 2


def run_guarded(command, run_id):
    """Reuse the existing Windows Job structures; this pilot alone owns the session lock."""
    import ctypes
    from ctypes import wintypes
    import importlib.util
    import subprocess
    import sys
    if Path(sys.prefix).resolve() != PROJECT / '.conda/envs/Thesis':
        raise ValueError('Thesis_environment_required')
    cfg = json.loads((PACKAGE / 'config.json').read_bytes())
    if (cfg['authorization_id'] != AUTHORIZATION or cfg['generate_limit'] != 160
            or not 0 < cfg['run_watchdog_seconds'] <= 1800
            or not 0 < cfg['new_write_limit_bytes'] <= 2 * 1024**3
            or cfg['local_write_upper_bytes'] < 128 * 1024**2):
        raise ValueError('development_configuration_mismatch')
    if command.startswith('run-'):
        ready = json.loads((PACKAGE / 'ready.json').read_bytes())
        sources = ['development_pilot.py', 'p1_engineering.py', 'p1_runtime.py', 'p1_storage.py',
            'provider_fourrouter.py', 'recommendation_runner.py', 'experiment_runner.py',
            str(PACKAGE.relative_to(PROJECT) / 'config.json')]
        if (any(ready.get(axis) != 'PASS' for axis in ('standards', 'spec'))
                or subprocess.run(['git', 'diff', '--quiet', ready['candidate'], '--', *sources], cwd=PROJECT).returncode):
            raise ValueError('development_candidate_not_reviewed')
    storage_headroom(OUTPUT)
    CONTROL.mkdir(exist_ok=True)
    lock = CONTROL / 'active.lock'
    with lock.open('x') as stream:
        stream.write(run_id)
    target = CONTROL / run_id
    target.mkdir(exist_ok=False)
    started = time.monotonic()
    code, job = 2, None
    spec = importlib.util.spec_from_file_location('inherited_job_structures',
        PROJECT / '.scratch/ticket12-budget-20261018/diagnostics/run_check.py')
    inherited = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inherited)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
    kernel.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    info, accounting = inherited.Extended(), inherited.Accounting()
    job = kernel.CreateJobObjectW(None, None)
    info.basic.flags, info.job_limit = 0x200 | 0x2000, 4 * 1024**3 - inherited.RESERVE
    history = [json.loads(p.read_bytes()) for p in CONTROL.glob('*/execution-resources.json')]
    write_left = cfg['new_write_limit_bytes'] - cfg['local_write_upper_bytes'] - sum(r['job_write_transfer_bytes'] for r in history)
    if write_left < 16 * 1024**2:
        raise OSError('development_write_balance')
    try:
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError('development_Job_setup')
        with (target / 'execution.stdout').open('xb') as output:
            child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '_child', command, run_id], cwd=PROJECT, stdin=subprocess.PIPE,
                stdout=output, stderr=subprocess.STDOUT)
            if not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(int(child._handle))):
                child.terminate()
                child.wait(timeout=5)
                raise OSError('development_Job_assignment')
            child.stdin.write(b'GO\n')
            child.stdin.close()
            while child.poll() is None:
                kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
                if (time.monotonic() - started >= cfg['run_watchdog_seconds'] - 10
                        or output.tell() > 1024**2 or accounting.io.write_bytes > write_left):
                    kernel.TerminateJobObject(job, 124)
                    break
                time.sleep(.05)
            code = child.wait(timeout=5)
    finally:
        kernel.QueryInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info), None)
        kernel.QueryInformationJobObject(job, 8, ctypes.byref(accounting), ctypes.sizeof(accounting), None)
        kernel.CloseHandle(job)
        row = {'run_id': run_id, 'command': command, 'seconds': time.monotonic() - started,
            'exit_code': code, 'job_peak_commit_bytes': info.job_peak,
            'job_write_transfer_bytes': accounting.io.write_bytes, 'memory_limit_bytes': 4 * 1024**3,
            'write_balance_before': write_left, 'run_watchdog_seconds': cfg['run_watchdog_seconds'],
            'historical_offline_seconds_are_statistics_only': True}
        (target / 'execution-resources.json').write_text(json.dumps(row, indent=2))
        lock.unlink()
    print(json.dumps(row))
    return code


def main(argv=None):
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == '_child':
        if sys.stdin.buffer.readline() != b'GO\n':
            return 2
        command, run_id = args[1:]
        try:
            return diagnose(command.removeprefix('diag-'), run_id) if command.startswith('diag-') else execute_task(command, run_id)
        except Exception as exc:
            # Exception prose can contain provider/credential text. Never persist it.
            import traceback
            frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                for f in traceback.extract_tb(exc.__traceback__)[-12:]]
            (CONTROL / run_id / 'worker-error.json').write_text(json.dumps({'error_type': type(exc).__name__,
                'stage': 'entry', 'frames': frames, 'usage': None, 'metering_status': 'unknown'}))
            return 2
    command = args[0]
    if command == 'preflight':
        rows = [preflight_task(label, method) for label, method in [('V00', 'S')] +
            [(s, 'M') for s in ('V00', 'V01', 'V05', 'V06', 'Q1', 'Q2')]]
        (PACKAGE / 'preflight.json').write_text(json.dumps(rows, indent=2))
        print(json.dumps(rows))
        return 0
    stamp = str(int(time.time() * 1000))
    if command.startswith('run-'):
        _, label, method = command.split('-')
        run_id = 'T14-D1-' + label + '-' + method + '-' + stamp
    else:
        run_id = ('T14-D1-V00-S-DIAG-' if command.startswith('diag-full') else 'PUBLIC-T14-' + command + '-') + stamp
    return run_guarded(command, run_id)


if __name__ == '__main__':
    raise SystemExit(main())
