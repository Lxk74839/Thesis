# 单次首请求诊断增量

继承d282bf8及protocol-diagnostics/one-request-diagnostic-plan.md；本次用户已授权执行该方案一次。只增加独立入口，不修改生产推荐方法或normalizer。公共行为为：首请求原组合器/mapper；单次发送及重复许可拒绝；白名单协议诊断。测试仅PUBLIC fixture、transport seam，无Key或联网。

新authorization_id=S-FIRST-DIAGNOSTIC-20261020；仅D1/V00/S首请求。完整C=1493及原安全输入，8192输出cap、reasoning none、POST≤2MiB、响应≤64KiB；1生成、0count/other/retry、30秒HTTP、45秒执行含15秒保存；共享P1根64MiB、诊断产物≤1MiB、4GiB。首响应无论成功失败均结束，不执行工具、不生成publication。严格Schema/未知output拒绝不变。

不新加离线额度：继续前包剩余56.7704041秒（原180秒包），保留30秒收尾；全局剩116.7576026/2280秒。native10秒/4MiB为本次所有非测试非代理操作和归档的保守计费上界，不称实测；测试和并行审查另按实计入原账。历史超限保留，旧证据只读。诊断执行45秒是本次已批准方案的独立执行域，不使用已消耗S360秒许可。
