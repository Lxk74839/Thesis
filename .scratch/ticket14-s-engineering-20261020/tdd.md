# 定向TDD

- seng_001：仅S授权、M预算null、未知Token/费用的准入RED（旧严格合同拒绝）；seng_002 GREEN。
- seng_003：无usage PUBLIC原S贯通RED（预检要求counter）；seng_004 GREEN，9调用，发布通过，计量未知，count/receipt=null。
- 新增真实1493/S非执行预检、精确来源/授权拒绝、11工作+1最终调用及1500容量预留、窄凭据/worker准入的行为首次即满足，如实记录，无制造RED。
- seng_005：17定向回归中1项因全局离线测试审计钩子的错误文本先拦截而失败；仅调整新测试钩子的分类文本，seng_006 17/17通过。未改旧R测试或保护。
- seng_007：新增模型不匹配、无效usage及302均1次后停止、无publication；6项增量通过。

测试均Thesis、Windows Job 4GiB、无网络/实际Key/独立标签读取。真实1493预检未调用run。A、上游验收与联网PUBLIC探针未重跑。
