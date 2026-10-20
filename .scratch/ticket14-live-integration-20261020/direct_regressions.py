"""Existing assertions with only their public fixture directories scoped to this package."""
from pathlib import Path
import tempfile
import unittest

from tests import test_root_budget as budget, test_batched_recommendation as batch
from tests import test_experiment_evaluation as evaluation

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / '.tmp/recommendation-runtime/liveA/direct'
PUBLIC.mkdir(parents=True, exist_ok=True)
budget.PROJECT = PUBLIC / 'budget'
(budget.PROJECT / '.tmp/recommendation-runtime').mkdir(parents=True, exist_ok=True)
batch.PROJECT = PUBLIC / 'batch'


class ScopedCLI(evaluation.PublicCLI):
    def setUp(self):
        parent = ROOT / '.tmp/experiment-evaluation/liveA'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='direct-cli-', dir=parent, delete=False)
        self.root = Path(self.temp.name)


suite = unittest.TestSuite([
    budget.RootBudgetTests('test_final_capacity_is_protected_and_consumed_once_across_roles'),
    budget.RootBudgetTests('test_unknown_tokens_keep_their_hold_and_block_new_work'),
    batch.BatchedRecommendationTests('test_batch_stops_inside_window_at_tenth_eligible_without_reading_eleventh'),
    batch.BatchedRecommendationTests('test_four_quality_candidates_have_six_roles_and_nine_actual_calls'),
    evaluation.TaskScores('test_not_started_failure_reference_na_and_missing_record_are_distinct'),
    evaluation.TaskScores('test_wrong_reference_or_execution_binding_is_pipeline_error'),
    evaluation.TaskScores('test_empty_proof_coverage_and_unassessed_are_reported'),
    evaluation.TaskScores('test_quality_failure_is_shared_and_reference_cannot_supply_missing_facts'),
    evaluation.Summaries('test_scene_groups_and_usage_count_actual_tasks_once_with_unknowns'),
    ScopedCLI('test_cli_rejects_real_scope_damaged_binding_and_outside_path'),
])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
