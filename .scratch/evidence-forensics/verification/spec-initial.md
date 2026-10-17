# Spec — initial independent review

BASE: `ac49059ffa1f61545033b84f688eee4be58d75be`  
CANDIDATE: `6bbcb800b319ee813f1a94284212f8dfb3d84ca9`

Static review of `git diff BASE...CANDIDATE`; commits `1c61360`, `6bbcb80`. No Python/tests/probes were executed; no private data or reference outputs were read. Governing spec/confirmation are effective through authorization-20261016.md. Five blocking findings; no nonblocking findings.

1. **[P1, blocking] E1 does not enforce source binding.** Contract `spec.md:76`: “外层清单摘要或来源绑定不符” requires “停止受影响会话”. `evidence_access.py:366–372` never compares the acquired snapshot ID/τ to binding: a valid source paired with another snapshot binding can list/read successfully; only E2 catches it (`evidence_verification.py:212–214`). The same path scans candidate facts before rejecting a mismatched principal. Validate the pinned source/authority before candidate acquisition and response publication.

2. **[P1, blocking] Direct redispatch bypasses retries.** `spec.md:126`: “重试为新request，引用retry_of，照计实际用量并占共同重试额度”. After a known `io_error`, repeatedly call public `dispatch` with the same read request: `evidence_access.py:172,216,236–237` leaves `retry_of=None` and retries=0, so a third retry still reaches the Adapter. Track failed-request continuations or require their common retry path.

3. **[P1, blocking] Time reserve is not reserved.** `spec.md:127`: “原子预留最坏返回量/请求量及时间，始终保护最终预留”. `_estimate` holds only logical/physical units (`evidence_access.py:201`); line 215 checks elapsed time only before work. Starting exactly at `limit−final_reserve` admits positive-duration work, consumes the final reserve, and can still return `ok` under line 241. Reserve/enforce an operation deadline including backoff before I/O.

4. **[P2, blocking] Empty acquired ranges never become assessed.** `spec.md:63`: “空获权范围也是可正常结束的页”; line 93 assigns evaluated insufficient evidence `Pending`. An actual empty terminal list creates no read refs/attempts, so `evidence_verification.py:206–208` returns Unassessed forever and cannot permit rejection/advance. Recognize receipted empty-range observations separately from no acquisition.

5. **[P2, blocking] Unexecuted batch items consume logical budget.** `spec.md:126`: “not_attempted项为0逻辑/0物理”. For Adapter results `[ok, io_error, not_attempted]`, `evidence_access.py:348` charges three logical units instead of two. Settle only executed facts/failures and retain the unexecuted item's zero usage.
