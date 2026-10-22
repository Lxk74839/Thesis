"""Offline configuration preparation. Never grants execution or contacts suppliers."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evidence_access import encoded, digest
from formal_runtime import PLAN, PLAN_ID, CONFIG, AUTHORIZATION, PROTOCOL, reference, budget_tables

if CONFIG.exists() and json.loads(CONFIG.read_bytes())['status'] == 'frozen_pending_confirmation':
    raise SystemExit('configuration_already_frozen')
code = {p.name: reference(p) for p in sorted(ROOT.glob('*.py'))}
cfg = {'schema_version': 'ticket15-execution-0.1.0', 'protocol': PROTOCOL,
    'status': 'frozen_pending_confirmation' if '--freeze' in sys.argv else 'preparing',
    'authorization_id': AUTHORIZATION, 'execution_authorized': False,
    'baseline': '1a2419db4d10e641b3c97548ea51c1a9fc327338',
    'inherited_reviewed_code': '75f5943dfbf53301cf48217e4b11d1c734c3e8b0',
    'plan_id': PLAN_ID, 'plan_files': {p.name: reference(p) for p in sorted(PLAN.iterdir())},
    'data_sources': json.loads((PLAN / 'plan.json').read_bytes())['sources'],
    'code_files': code, 'code_identity': digest(encoded(code)),
    'versions': {'prompt': 'rsm-role-composer-0.15.0', 'runner': 'rsm-runner-4router-0.3.0',
        'mapper': '4router-responses-mapper-0.4.0', 'orchestration': 'batch32-0.1.0',
        'product_profile': 'acquired-product-object-0.3.0', 'ranking_issue': 'ranking-issue-proof-0.1.0'},
    'protocol_records': {name: reference(ROOT / name) for name in (
        '.scratch/data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md',
        '.scratch/data-preparation/ticket12-final-experiment-protocol-review-20261016.md',
        '.scratch/ticket14-q-contract-20261022/acceptance.md',
        '.scratch/ticket15-formal-20261022/spec.md')},
    'python_version': sys.version, 'conda_prefix': str(ROOT / '.conda/envs/Thesis'),
    'model': {'channel': '4Router', 'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna'},
    'tasks': 5000, 'model_tasks': 3400, 'generate_limit': 61200, 'run_model_calls': 18,
    'quality_prefix_limit': 32, 'quality_profile_chunk_size': 4,
    'batch_size': 50, 'concurrency': 2, 'http_seconds': 120, 'run_watchdog_seconds': 1800,
    'active_seconds_limit': 5000 * 1800, 'run_storage_limit_bytes': 128 * 1024**2,
    'shared_storage_limit_bytes': 640 * 1024**3, 'minimum_free_bytes': 20 * 1024**3,
    'control_reserve_bytes': 2 * 1024**3, 'run_memory_limit_bytes': 4 * 1024**3,
    'retry': 0, 'attempts_per_task': 1, 'count_api': 0, 'other_api': 0,
    'max_request_bytes': 2 * 1024**2, 'max_response_bytes': 1024**2,
    'ordinary_output_tokens': 8192, 'final_output_tokens': 1500, 'final_reserve_seconds': 145,
    'pricing': None, 'cost': None, 'failure_policy': 'retain_no_retry',
    'interrupted_policy': 'unresolved_no_resend', 'sampling': 'original_frozen_order'}
cfg['runtime_budgets'] = {method: dict(zip(('limits', 'final_reserve'), budget_tables(method, cfg)))
    for method in ('R', 'S', 'M')}
cfg['configuration_id'] = digest(encoded(cfg))
CONFIG.write_bytes(encoded(cfg) + b'\n')
if '--freeze' in sys.argv:
    draft = {'status': 'pending_user_confirmation', 'execution_authorized': False,
        'authorization_id': AUTHORIZATION, 'plan_id': PLAN_ID,
        'configuration_id': cfg['configuration_id'], 'code_identity': cfg['code_identity'],
        'human_confirmation': None, 'scope': 'all_original_tasks_all_batches_one_attempt',
        'generate_limit': cfg['generate_limit'], 'storage_limit_bytes': cfg['shared_storage_limit_bytes'],
        'count_api': 0, 'other_api': 0, 'pricing': None, 'cost': None}
    with CONFIG.with_name('authorization.draft.json').open('xb') as stream:
        stream.write(encoded(draft) + b'\n')
print(json.dumps({'status': cfg['status'], 'configuration_id': cfg['configuration_id'], 'supplier_calls': 0}))
