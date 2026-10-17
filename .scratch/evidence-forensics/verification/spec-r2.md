# Spec — final targeted re-review

BASE: `ac49059ffa1f61545033b84f688eee4be58d75be`  
CANDIDATE: `d1ff0f8776b6b1e0f8f4078f3ca440ed1bb1bee4`  
Previous candidate: `8d10ba9139a37217b59ff5f6be1dc11d32e4fd3d`

Blocking: 0

Reviewed `git diff BASE...CANDIDATE`, `git log BASE..CANDIDATE --oneline` (`1c61360`, `6bbcb80`, `8d10ba9`, `d1ff0f8`), and the previous-to-current delta. Static review only; no Python/tests/probes executed, private/ignored data or Standards report read.

**Remaining retry finding closed.** Contract `spec.md:126` requires “重试为新request，引用retry_of，照计实际用量并占共同重试额度”. At `evidence_access.py:337–339`, read continuation removal now requires a genuine per-item terminal outcome. Top-level parameter/authorization rejection cannot erase earlier failure records; successful list continuation remains independently closable. Consequently the previously reported failed `[a,b,c]` → rejected duplicate batch → separate a/b/c requests still use the shared retry counter. The added public E1 test follows that exact sequence and asserts the remaining attempt consumes the second retry, subsequent attempts are rejected, and denied work performs no Adapter I/O. Its expected values are consistent with the inspected control flow; execution results are not independently claimed.

**Other four findings remain closed.** The one-condition production delta leaves source prevalidation before candidate scanning, 45-second operation/backoff/final time reservation and late-response halt, receipted empty-range Pending assessment with safe rejection, and zero logical charge for `not_attempted` unchanged. No regression was identified in their affected paths, cache/receipt accounting, current-candidate binding or normal Q conversion.

**Scope conforms.** The base-to-candidate file list remains within `spec.md:165–168`: two new production modules, the authorized three public test files, and this special-purpose record directory. Accepted upstream code/configuration is unchanged. New `diagnostics/check_acceptance.py` imports no production module, consumes existing test/probe/A/receipt/resource artifacts, binds reviewed production bytes, and writes only an independent audit result; it adds no method facts or gold dependency. Runtime acceptance and final source-probe evidence remain separate from this static verdict.

All five original Spec findings are closed; no additional blocking or nonblocking Spec finding is recorded for this targeted review.
