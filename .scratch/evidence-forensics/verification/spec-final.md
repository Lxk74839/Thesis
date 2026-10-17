# Spec — targeted re-review

BASE: `ac49059ffa1f61545033b84f688eee4be58d75be`  
CANDIDATE: `8d10ba9139a37217b59ff5f6be1dc11d32e4fd3d`  
Previous candidate: `6bbcb800b319ee813f1a94284212f8dfb3d84ca9`

Reviewed `git diff BASE...CANDIDATE`, `git log BASE..CANDIDATE --oneline` (`1c61360`, `6bbcb80`, `8d10ba9`), and the previous-to-current delta. Static only: no Python/tests/probes executed, private/ignored data or Standards report read. **Four findings closed; one blocking finding remains.**

1. **Closed — source binding.** Contract `spec.md:76`: “来源绑定不符” requires “停止受影响会话”. `evidence_access.py:64–77` now checks snapshot/τ and pinned policy/principal before scanning candidate components. Failed binding cannot populate A or continue I/O. Added public cases exercise snapshot, τ and principal mismatch.

2. **[P1, blocking] Retry tracking can still be erased by a rejected batch.** Contract `spec.md:126`: “重试为新request，引用retry_of，照计实际用量并占共同重试额度”. `evidence_access.py:333–338` treats top-level `access_denied` as a terminal result for every supplied ref, deleting their failure continuations. Minimal static reproduction: list refs a/b/c; read `[a,b,c]` against an Adapter raising OSError; submit `[a,a,b,c]`, rejected for duplicates at lines 373–374; then read `[a]`, `[b]`, `[c]` separately. All original failure keys were cleared, so those three actual retries reach the Adapter as new requests, while root retries remains 1. **Smallest fix:** clear continuations only for genuine per-item terminal outcomes; parameter/authorization rejection must retain previous failures. Extend the public E1 retry case with this sequence.

3. **Closed — time reservation.** Contract `spec.md:127`: “原子预留最坏返回量/请求量及时间”. Admission now includes 45 seconds, retry backoff and final reserve; receipts hold/settle/release time and record a deadline. Late observations remain retained and halt the root.

4. **Closed — empty scope.** Contract `spec.md:63,93`: “空获权范围也是可正常结束的页”; evaluated insufficiency is “Pending”. Receipted empty enumeration now reaches E2: Pending, missing required originals, settled attempts and safe rejection; no acquisition remains Unassessed.

5. **Closed — not_attempted billing.** Contract `spec.md:126`: “not_attempted项为0逻辑/0物理”. Line 389 excludes these items from logical settlement while preserving observations and releasing unused logical reservation.

No additional blocking regression identified in the inspected affected paths. Q conversion and accepted upstream code remain unchanged. Test source coverage was inspected; execution/probe acceptance is not independently claimed.
