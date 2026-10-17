# Standards — independent initial review

BASE: `ac49059ffa1f61545033b84f688eee4be58d75be`

CANDIDATE: `6bbcb800b319ee813f1a94284212f8dfb3d84ca9`

Reviewed the fixed `git diff BASE...CANDIDATE` and `git log BASE..CANDIDATE --oneline` (substituting the exact SHAs above): authorization `1c61360`, implementation `6bbcb80`. Static Git/code/document reads only; no Python, tests, probes, private/ignored data, or Spec report inspected.

## Blocking — documented-rule violation (1)

**[P1] Persist an unresolved resource reservation before starting a child.** `.scratch/evidence-forensics/diagnostics/run_check.py:41,63–85` loads only completed ledger rows and first appends this run in `finally`, after `child.wait()`. If the guard is forcibly terminated or the host fails while its child runs, `finally` cannot execute: the next invocation has no record of that run and admits work against the old total. This loses unknown consumption and can exceed the shared cumulative allowance. The rule is explicit in `.scratch/evidence-forensics/authorization-20261016.md:14`: “共用一份资源账，失败和未知用量保留；到限停止并报告，不自动扩额。” Minimal fix: durably record an in-flight reservation before spawning; settle it after completion; refuse further runs while a previous reservation remains unresolved, or conservatively charge its reserved allowance. This is a static failure-path finding, not evidence that the actual budget was exceeded.

## Nonblocking — judgement call (1)

**Possible Duplicated Code:** `evidence_access.py:140–141,313–314` repeats `self.secret + encoded({key: ... for key in (...)})`, including the full scope-field tuple, during initialization and advancement. A later scope-field change could update one path and weaken the other. A small private scope-seed helper would keep that knowledge together. Fowler heuristic only; record without expanding this review's implementation scope.

## Other standards checks

All 14 diff paths are additions within the allowed production/test/specialist-record paths; no accepted upstream file changes appear. Tests exercise the agreed public acquisition/audit/assessment interfaces; randomness/time substitutions are permitted system seams. No additional hard violation is evidenced by static review. TDD history and resource totals remain runtime-evidence checks for the parent; this report does not claim acceptance.
