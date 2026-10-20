"""D1 V00 R/S/M preparation. Missing contracts stop before credentials or assembly."""
import argparse
import copy
import json
import time
from pathlib import Path

from evidence_access import PROJECT, digest
from experiment_runner import _path, _task_plan, assemble_task
from provider_fourrouter import contract_missing
from p1_storage import P1StorageGuard

PILOT_ID = '6353afe1bf05e4eadd56216d64bb5d29181798e29c6edf9468f9d537e10c1af1'
PLAN_ID = '9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088'
D1 = '015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e'
TASK_KEYS = {'R': '7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874',
    'S': 'a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4',
    'M': '4fc09c3d2c7a0ad10bf5af864479975fc62c3d12c7b4f8b8f476094651a9694e'}
PILOT = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/pilot'
DEFAULT_CONFIG = PROJECT / '.scratch/ticket14-p1-wiring-20261020/p1.config.draft.json'
OUTPUT = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/p1'


def _valid_budget(table):
    from evidence_access import RootBudget
    return (isinstance(table, dict) and set(table) == set(RootBudget.resources)
            and all(type(v) is int and v >= 0 for v in table.values()))


def _engineering_config(cfg, method):
    from p1_engineering import AUTHORIZATIONS, authorized
    return (method == 'S' and authorized(cfg['model_binding'])
        and cfg.get('authorization_id') in AUTHORIZATIONS
        and cfg['model_binding'].get('engineering_authorization') == cfg.get('authorization_id')
        and cfg.get('execution_authorized') is True
        and cfg.get('authorized_task_keys') == [TASK_KEYS['S']])


def prepare_p1(config_path, method, *, counter=None, storage_guard=None):
    cfg = json.loads(Path(config_path).read_text(encoding='utf-8'))
    _, manifest, rows = _task_plan(PILOT)
    if (method not in TASK_KEYS or manifest['pilot_id'] != PILOT_ID or manifest['parent_plan_id'] != PLAN_ID
            or cfg['pilot_id'] != PILOT_ID or cfg['parent_plan_id'] != PLAN_ID
            or cfg['task_keys'] != TASK_KEYS):
        raise ValueError('P1_identity_mismatch')
    task = next(r for r in rows['tasks.jsonl'] if r['task_key'] == TASK_KEYS[method])
    relation = next(r for r in rows['user-scenarios.jsonl'] if r['binding_id'] == task['binding_id'])
    scene = next(r for r in rows['scenes.jsonl'] if r['view_id'] == relation['view_id'])
    if relation['root_task_id'] != D1 or scene['label'] != 'V00' or task['method'] != method:
        raise ValueError('P1_scope_mismatch')
    missing = []
    engineering = _engineering_config(cfg, method)
    if cfg['model_binding'].get('engineering_authorization') and not engineering:
        missing.append('S_engineering_authorization')
    project_id = cfg['model_binding'].get('project_id')
    if not isinstance(project_id, str) or not project_id.strip():
        missing.append('project_id')
    if cfg['model_binding'].get('provenance') != '4router':
        missing.append('fixture_cannot_authorize_D1')
    if (cfg['model_binding'].get('execution_kind'), cfg['model_binding'].get('model_id'),
            cfg['model_binding'].get('channel'), cfg['model_binding'].get('base_url')) != (
            'fourrouter_responses', 'gpt-6-luna', '4Router', 'https://4router.net/v1'):
        missing.append('exact_4router_binding')
    if cfg.get('execution_authorized') is not True or not cfg.get('authorization_id'):
        missing.append('execution_authorization')
    if TASK_KEYS[method] not in cfg.get('authorized_task_keys', []):
        missing.append('execution_task_authorization')
    for name in ('limits', 'final_reserve'):
        from p1_engineering import SEngineeringBudget
        table = cfg.get(name, {}).get(method)
        valid = (isinstance(table, dict) and set(table) == set(SEngineeringBudget.resources)
            and all(type(v) is int and v >= 0 for v in table.values())) if engineering else _valid_budget(table)
        if not valid:
            missing.append(name)
    limits, reserve = cfg['limits'][method], cfg['final_reserve'][method]
    if _valid_budget(limits) and _valid_budget(reserve):
        if any(reserve[k] > limits[k] for k in reserve):
            missing.append('final_reserve')
        if method == 'R' and any(limits[k] != 0 or reserve[k] != 0 for k in (
                'model_calls', 'input_tokens', 'output_tokens', 'cost_microusd')):
            missing.append('R_must_have_zero_model_budget')
    if cfg.get('storage_limit_bytes') is None:
        missing.append('storage_limit_bytes')
    if (type(storage_guard) is not P1StorageGuard or getattr(storage_guard, 'limit_bytes', None) != cfg.get('storage_limit_bytes')
            or getattr(storage_guard, 'root', None) != OUTPUT):
        missing.append('controlled_storage_guard')
    if engineering:
        if not missing:
            try:
                if (not 1 <= limits['model_calls'] <= 12 or limits['request_output_tokens'] > 98304
                    or reserve['model_calls'] < 1 or reserve['request_output_tokens'] < 1500
                    or reserve['elapsed_ms'] < 10000 or limits['elapsed_ms'] > 350000
                    or limits['retries'] != 0 or any(reserve[k] > limits[k] for k in reserve)):
                    missing.append('S_engineering_limits')
            except (KeyError, TypeError):
                missing.append('S_engineering_limits')
        missing.extend(contract_missing(cfg['model_binding'], counter))
    elif method != 'R':
        missing.extend(contract_missing(cfg['model_binding'] | {
            'execution_authorized': cfg.get('execution_authorized')}, counter))
        model_limits = [cfg['limits'][m] for m in ('S', 'M')]
        if (not all(_valid_budget(v) for v in model_limits)
                or type(cfg['model_binding'].get('api_budget_microusd')) is not int
                or sum(v['cost_microusd'] for v in model_limits) > cfg['model_binding']['api_budget_microusd']):
            missing.append('P1_shared_api_budget')
    return {'task_key': TASK_KEYS[method], 'method': method, 'pilot_id': PILOT_ID, 'parent_plan_id': PLAN_ID,
        'terminal': 'not_started' if missing else 'ready', 'started': False,
        'missing': sorted(set(missing)), 'provider_requests_sent': 0,
        'input_tokens': None, 'pricing': cfg['model_binding'].get('pricing'), 'usage': None}


def frozen_snapshot_error(binding, snapshot_ref):
    """Admit frozen R or this independently authorized S; never a directory."""
    try:
        _, manifest, rows = _task_plan(PILOT)
        from p1_engineering import AUTHORIZATIONS
        method = binding.get('method')
        allowed = method == 'R' or (method == 'S' and binding.get('authorization_id') in AUTHORIZATIONS
            and binding.get('run_id') == 'P1-D1-V00-S-' + binding['authorization_id'])
        if (manifest['pilot_id'] != PILOT_ID or manifest['parent_plan_id'] != PLAN_ID
                or binding.get('pilot_id') != PILOT_ID or binding.get('root_task_id') != D1
                or not allowed or binding.get('task_key') != TASK_KEYS.get(method)
                or binding.get('plan_source_scope') != 'development_pilot' or binding.get('fixture') is not None):
            return 'frozen_task_identity'
        task = next(t for t in rows['tasks.jsonl'] if t['task_key'] == TASK_KEYS[method])
        relation = next(r for r in rows['user-scenarios.jsonl'] if r['binding_id'] == task['binding_id'])
        scene = next(s for s in rows['scenes.jsonl'] if s['view_id'] == relation['view_id'])
        root = next(r for r in rows['root-references.jsonl'] if r['root_task_id'] == D1)
        if (relation['root_task_id'] != D1 or scene['label'] != 'V00'
                or binding.get('view_id') != scene['view_id'] or binding.get('arm') != scene['arm']
                or binding.get('snapshot_id') != scene['snapshot_id']):
            return 'frozen_view_binding'
        if any(binding.get(b) != root[r] for b, r in (
                ('C_sha256', 'C_sha256'), ('H_sha256', 'H_sha256'), ('base_score_sha256', 'base_scores_sha256'))):
            return 'frozen_input_binding'
        expected = scene['snapshot']
        if snapshot_ref != expected or binding.get('source_snapshot_ref') != expected:
            return 'frozen_snapshot_reference'
        path = _path(snapshot_ref['path'])
        if path.resolve(strict=True) != _path(expected['path']).resolve(strict=True):
            return 'frozen_snapshot_path'
        raw = path.read_bytes()
        if len(raw) != expected['bytes']:
            return 'frozen_snapshot_bytes'
        if digest(raw) != expected['sha256']:
            return 'frozen_snapshot_sha256'
        snapshot = json.loads(raw)
        if (snapshot['snapshot_id'] != scene['snapshot_id'] or snapshot['verify_at_ms'] != binding['verify_at_ms']
                or snapshot.get('read_principal_id', binding['principal_id']) != binding['principal_id']):
            return 'frozen_snapshot_identity'
    except (OSError, ValueError, TypeError, KeyError, StopIteration):
        return 'frozen_source_validation'
    return None


def build_runtime(assembly, cfg, method, *, counter, output_root=OUTPUT, storage_guard=None):
    from evidence_access import RootBudget, EvidenceSession, LocalEvidenceSource
    from joint_access import JointSession
    from model_adapter import ModelAdapter
    from provider_fourrouter import make_sender
    from recommendation_runner import RecommendationRun
    binding = copy.deepcopy(assembly['binding'])
    binding.update(schema_version='rsm-run-0.4.0', execution_kind='fourrouter_responses', fixture=None,
        execution_authorized=True, execution_budget=cfg['limits'][method], pilot_id=PILOT_ID,
        orchestration='batch32-0.1.0', project_id=cfg['model_binding']['project_id'])
    engineering = _engineering_config(cfg, method)
    if engineering:
        from p1_engineering import SEngineeringBudget
        RootBudget = SEngineeringBudget
        binding['authorization_id'] = cfg['authorization_id']
    output = Path(output_root) / binding['run_id']
    budget = RootBudget(binding, cfg['limits'][method], cfg['final_reserve'][method],
        clock=lambda: time.monotonic() * 1000, journal_path=output / 'budget.jsonl')
    joint = JointSession(assembly['root'], assembly['candidates'], assembly['catalog'], assembly['view'], binding['run_id'])
    queue = sorted(zip(binding['C'], binding['base_scores'], binding['batches']), key=lambda v: (-v[1], v[0].encode()))
    evidence_binding = {k: binding[k] for k in ('run_id', 'root_task_id', 'snapshot_id', 'principal_id',
                                               'verify_at_ms', 'arm', 'necessary_clauses')}
    evidence_binding.update(parent_asin=queue[0][0] if queue else None, sim_batch_id=queue[0][2] if queue else None)
    evidence = EvidenceSession(evidence_binding, LocalEvidenceSource(assembly['snapshot_ref']),
        limits=cfg['limits'][method], final_reserve=cfg['final_reserve'][method], root_budget=budget, joint=joint)
    model = None if method == 'R' else ModelAdapter(make_sender(clock=budget.clock,
        max_request_bytes=cfg['model_binding']['max_request_bytes'], storage_guard=storage_guard),
        capability_binding=cfg['model_binding'] | {'execution_authorized': True}, counter=counter, root_budget=budget)
    return RecommendationRun(binding, evidence=evidence, model=model, root_budget=budget, output_root=output)


def execute_p1(config_path, method, *, counter=None, storage_guard=None):
    prepared = prepare_p1(config_path, method, counter=counter, storage_guard=storage_guard)
    if prepared['terminal'] != 'ready':
        return prepared
    cfg = json.loads(Path(config_path).read_text(encoding='utf-8'))
    run_id = 'P1-D1-V00-' + method + '-' + cfg['authorization_id']
    if not run_id.replace('-', '').isalnum():
        raise ValueError('invalid_P1_authorization_id')
    output = OUTPUT / run_id
    if output.exists():
        return prepared | {'terminal': 'not_started', 'missing': ['existing_execution_no_retry']}
    with storage_guard:
        if _engineering_config(cfg, method):
            storage_guard.authorize_S(cfg['authorization_id'])
        output.mkdir(parents=True, exist_ok=False)
        with (output / 'attempt.json').open('x', encoding='utf-8') as stream:
            stream.write(json.dumps({'task_key': TASK_KEYS[method], 'run_id': run_id,
                'pilot_id': PILOT_ID, 'authorization_id': cfg['authorization_id']}) + '\n')
        assembly = assemble_task(PILOT, TASK_KEYS[method], execution_record={'run_id': run_id})
        runtime = build_runtime(assembly, cfg, method, counter=counter, storage_guard=storage_guard)
        observed = runtime.run()
    counts = [m['response'].get('provider_requests_sent') for m in runtime.state['messages']]
    return {'task_key': TASK_KEYS[method], 'started': True, 'terminal': observed['terminal'],
        'run_id': run_id, 'provider_requests_sent': None if any(c is None for c in counts) else sum(counts),
        'audit_path': observed['audit_path'], 'publication_path': observed['publication_path']}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'execute'))
    parser.add_argument('--method', choices=('R', 'S', 'M'), required=True)
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    args = parser.parse_args(argv)
    execution_entered = False
    try:
        result = prepare_p1(args.config, args.method)
        if args.command == 'execute' and result['terminal'] == 'ready':
            execution_entered = True
            result = execute_p1(args.config, args.method)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        result = {'terminal': 'execution_unknown' if execution_entered else 'not_started',
            'started': None if execution_entered else False, 'missing': ['invalid_P1_configuration'],
            'provider_requests_sent': None if execution_entered else 0}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['terminal'] == 'ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
