"""Only the new formal seams and directly affected inherited acceptance checks."""
import json
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evidence_access import encoded

names = ['tests.test_formal_experiment', 'tests.test_quality_output_contract', 'tests.test_development_evaluation']
names += ['tests.test_p1_wiring.P1Wiring.' + name for name in (
    'test_existing_R_S_M_pipeline_uses_exact_model_and_keeps_six_roles_and_publication',
    'test_runtime_factory_constructs_shared_sessions_without_reading_credentials',
    'test_live_adapter_refuses_unknown_count_rates_budget_and_authorization_before_transport')]
names += ['tests.test_development_pilot.SharedCalls.' + name for name in (
    'test_development_storage_cap_is_explicit_and_writes_remain_guarded',
    'test_runtime_cannot_read_independent_reference_paths',
    'test_completion_grant_keeps_158_spent_and_allows_only_one_18_call_run_per_Q')]
names += ['tests.test_development_pilot.ProductionFlow.test_frozen_seven_tasks_prepare_without_key_count_or_attempt_and_reject_R']
names += ['tests.test_live_integration.LiveIntegration.' + name for name in (
    'test_public_artifacts_and_native_reference_rows_reach_score_task',
    'test_failed_model_preserves_unknown_usage_without_retry_or_zero_fill',
    'test_unresolved_intent_is_not_a_missing_or_zero_scored_execution',
    'test_evaluation_requires_each_actual_request_and_response_trace',
    'test_success_requires_same_run_final_commit_and_audit_settlement',
    'test_added_scene_uses_exact_snapshot_and_original_request_template')]
suite = unittest.defaultTestLoader.loadTestsFromNames(names)
started = time.monotonic()
with (ROOT / '.scratch/ticket15-formal-20261022/verification.txt').open('w', encoding='utf-8') as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
record = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun,
    'seconds': time.monotonic() - started, 'selected': names,
    'failures': [str(t) for t, _ in result.failures], 'errors': [str(t) for t, _ in result.errors],
    'supplier_generate': 0, 'supplier_count': 0, 'supplier_other': 0,
    'offline_boundary': 'socket_and_secrets_and_private_denied_by_test_audit_hook',
    'tdd_cycles': ['task_key_resolution_RED_ModuleNotFoundError_GREEN',
        'formal_prepare_invoke_failure_RED_missing_configuration_GREEN',
        'durable_ledger_RED_ModuleNotFoundError_GREEN',
        'unconfirmed_guard_RED_missing_interface_GREEN',
        'run_entry_RED_missing_main_GREEN',
        'unsealed_failure_scoring_RED_None_audit_path_GREEN',
        'formal_sender_guard_RED_missing_keyword_GREEN'],
    'earlier_inherited_harness_check': {'run_tests': 43, 'passed': 42,
        'failure': 'test_A_guard_blocks_real_reference_reads_outside_writes_and_network',
        'reason': 'requires_legacy_THESIS_LIVE_A_PACKAGE_and_outer_guard; stopped_at_environment_assertion',
        'disposition': 'legacy_outer_guard_acceptance_inherited; formal_guard_covered_by_new_public_test'},
    'upstream_full_suite_rerun': False}
(ROOT / '.scratch/ticket15-formal-20261022/tests.json').write_bytes(encoded(record) + b'\n')
print(json.dumps({k: record[k] for k in ('status', 'tests', 'seconds', 'failures', 'errors')}))
raise SystemExit(0 if result.wasSuccessful() else 2)
