"""Frozen test100 task assembly. Preparation alone grants no sending capability."""
import copy
import json
from pathlib import Path

from evidence_access import PROJECT, digest, encoded
from experiment_runner import _task_plan, assemble_task

PLAN = PROJECT / 'data/recommendation-runtime-audit/ticket12-100x18/plan'
PLAN_ID = '9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088'
PACKAGE = PROJECT / '.scratch/ticket15-formal-20261022'
CONFIG = PACKAGE / 'config.json'
OUTPUT = PROJECT / 'data/recommendation-runtime-audit/ticket15-formal'
AUTHORIZATION = 'T15-TEST100-20261022'
PROTOCOL = 'formal-test100-0.1.0'


def reference(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': digest(raw)}


def load_config(*, validate_code=True):
    cfg = json.loads(CONFIG.read_bytes())
    if cfg['configuration_id'] != digest(encoded({k: v for k, v in cfg.items() if k != 'configuration_id'})):
        raise ValueError('formal_configuration_digest')
    if (cfg['plan_id'] != PLAN_ID or cfg['authorization_id'] != AUTHORIZATION
            or cfg['protocol'] != PROTOCOL or cfg['execution_authorized'] is not False
            or cfg['model'] != {'channel': '4Router', 'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna'}):
        raise ValueError('formal_configuration_identity')
    for name, ref in cfg['plan_files'].items():
        if reference(PLAN / name) != ref:
            raise ValueError('formal_plan_bytes_changed')
    if validate_code:
        for name, ref in (cfg['code_files'] | cfg['protocol_records']).items():
            if reference(PROJECT / name) != ref:
                raise ValueError('formal_code_changed')
    return cfg


def authorized(binding):
    """Contract marker only. The sender additionally requires the durable human grant."""
    return (binding.get('formal_protocol') == PROTOCOL
        and binding.get('authorization_id') == AUTHORIZATION and binding.get('plan_id') == PLAN_ID
        and isinstance(binding.get('formal_configuration_id'), str)
        and len(binding['formal_configuration_id']) == 64)


def budget_tables(method, cfg):
    from evidence_access import RootBudget
    from p1_engineering import SEngineeringBudget
    limits = dict.fromkeys(RootBudget.resources if method == 'R' else SEngineeringBudget.resources, 100000)
    limits.update(candidates=1494, retries=0, elapsed_ms=1780000)
    reserve = dict.fromkeys(limits, 0)
    if method == 'R':
        for key in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'):
            limits[key] = 0
        reserve.update(elapsed_ms=145000, logical_tools=64)
    else:
        limits.update(model_calls=cfg['run_model_calls'],
            request_output_tokens=(cfg['run_model_calls'] - 1) * 8192 + 1500)
        reserve.update(model_calls=1, request_output_tokens=1500, elapsed_ms=145000, logical_tools=64)
    return limits, reserve


def prepare_task(task_key, *, validate_code=True):
    """Resolve one original task; do not create output, read labels or credentials."""
    cfg = load_config(validate_code=validate_code)
    _, manifest, _ = _task_plan(PLAN)
    if manifest['plan_id'] != PLAN_ID or manifest['source_scope'] != 'accepted_test_pool':
        raise ValueError('formal_plan_identity')
    assembly = assemble_task(PLAN, task_key, execution_record={'run_id': 'T15-' + task_key})
    b = assembly['binding']
    b.update(formal_protocol=PROTOCOL, formal_configuration_id=cfg['configuration_id'],
        authorization_id=AUTHORIZATION, plan_id=PLAN_ID, implementation_candidate=cfg['code_identity'])
    if b['arm'] == 'quality':
        from quality_fusion import RULES
        b.update(prefix_limit=cfg['quality_prefix_limit'], profile_chunk_size=cfg['quality_profile_chunk_size'])
        b['fusion'] = {'schema_version': 'fusion-binding-0.1.0', 'task_id': b['root_task_id'],
            **{k: copy.deepcopy(b[k]) for k in ('C', 'C_sha256', 'H_sha256', 'base_scores',
                'base_score_sha256', 'snapshot_id', 'verify_at_ms', 'principal_id', 'K')},
            'base_score_version': assembly['root']['score_version'], 'contract_sha256': digest(encoded(RULES)),
            'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
            'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
    limits, reserve = budget_tables(b['method'], cfg)
    model = cfg['model'] | {k: b[k] for k in ('formal_protocol', 'formal_configuration_id', 'authorization_id', 'plan_id')}
    model.update(execution_kind='fourrouter_responses', execution_authorized=True,
        project_id='Thesis-task15-formal', provenance='4router', max_request_bytes=2 * 1024**2,
        max_output_tokens=8192, max_response_bytes=1024**2, wire_schema_subset=True,
        pricing=None, context_token_limit=None, api_budget_microusd=None)
    return {'assembly': assembly, 'configuration': {'authorization_id': AUTHORIZATION,
        'model_binding': model, 'limits': {b['method']: limits}, 'final_reserve': {b['method']: reserve}},
        'started': False, 'provider_requests_sent': 0}


def task_allowed(binding):
    try:
        cfg = load_config(validate_code=False)
        if (not authorized(binding) or binding.get('fixture') is not None
                or binding.get('plan_source_scope') != 'accepted_test_pool'
                or binding['formal_configuration_id'] != cfg['configuration_id']
                or binding.get('run_id') != 'T15-' + binding['task_key']):
            return False
        expected = prepare_task(binding['task_key'], validate_code=False)['assembly']['binding']
        fields = ('root_task_id', 'method', 'repeat_id', 'view_id', 'arm', 'C', 'base_scores', 'batches',
            'C_sha256', 'H_sha256', 'base_score_sha256', 'snapshot_id', 'source_snapshot_ref',
            'material_version', 'request_profile_id', 'verify_at_ms', 'principal_id', 'necessary_clauses',
            'safe_initial_messages', 'assembled_input_sha256', 'prefix_limit', 'fusion')
        return all(binding.get(k) == expected.get(k) for k in fields)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def frozen_snapshot_error(binding, snapshot_ref):
    if not task_allowed(binding):
        return 'formal_task_identity'
    if snapshot_ref != binding['source_snapshot_ref']:
        return 'formal_snapshot_reference'
    ref = reference(PROJECT / snapshot_ref['path'])
    return None if all(ref[k] == snapshot_ref[k] for k in ('bytes', 'sha256')) else 'formal_snapshot_digest'
