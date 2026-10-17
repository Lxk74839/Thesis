# Standards — independent targeted re-review

BASE: `ac49059ffa1f61545033b84f688eee4be58d75be`

CANDIDATE: `8d10ba9139a37217b59ff5f6be1dc11d32e4fd3d`

Initial candidate: `6bbcb800b319ee813f1a94284212f8dfb3d84ca9`.

Reviewed the fixed BASE...CANDIDATE diff and BASE..CANDIDATE log, plus the targeted initial-candidate...CANDIDATE changes. Commits: `1c61360`, `6bbcb80`, `8d10ba9`. Spec-report contents were excluded. Standards sources and Fowler heuristics remain those of the initial independent review.

## Blocking — documented rules

**Original [P1] resolved.** `.scratch/evidence-forensics/diagnostics/run_check.py:41–55` now rejects an existing unresolved marker and exclusively creates an in-flight record with unknown consumption and its remaining allowance. It flushes/fsyncs that record before spawning the child at lines 73–74. Lines 94–98 flush/fsync the completed ledger entry before removing the marker. Forced termination before settlement therefore preserves an unresolved reservation and blocks another run, satisfying `authorization-20261016.md:14` (“失败和未知用量保留”). A crash after settlement but before removal also conservatively blocks work.

The new `diagnostics/check_guard_interruption.py:12–47` exercises the actual guard with only its audit-directory system seam substituted, kills the nested guard, and checks that the next child cannot start. Its test structure does not mock guard conclusions.

**New blocking documented-rule violations: 0 found** in the targeted static review.

## Nonblocking — judgement call retained (1)

**Possible Duplicated Code:** `evidence_access.py:151–152,354–355` still repeats `self.secret + encoded({key: ... for key in (...)})` and its complete scope-field tuple. Keep the initial suggestion to consolidate that knowledge in a small private helper. This is a Fowler heuristic, not a hard violation; it was correctly left unchanged under the instruction to record nonblocking suggestions without expanding scope.

## Scope and verification limits

The 18 changed paths are additions within the permitted production/test/specialist-record scope; accepted upstream files remain unchanged in the fixed diff. The remediation changes retain public-interface tests and system-seam substitutions, with no new production configuration or runner. No additional standards blocker is evidenced.

Only static Git/code/document reads were performed. No Python, tests, probes, private/ignored data, or Spec report was accessed. Reported RED/GREEN execution and the 42-test result require the parent's runtime evidence; this report does not independently claim acceptance.
