# 定向TDD与继承边界

公共接口按本轮确认：完整RecommendationRun(S)→生产ModelAdapter.prepare/normalize→原工具/发布，以及真实D1的prepare_p1/assemble_task/build_runtime非执行预检。

1. `sA3_grant_red`：精确A3尚未接线时，完整PUBLIC S在S_engineering_limits拒绝，未发送。只加入精确授权后流程已发布；首次测试误把新角色首轮也要求带前一角色密文，修正合成测试断言只检查真实工具续接轮次，不改生产上下文隔离逻辑。
2. `sA3_complete_green`：完整PUBLIC S九次合成模型响应，通过非空summary/content、不透明encrypted_content、工具调用与后续prepare，最终原协议发布；usage缺失，计量仍未知。真实1493候选prepare/preflight通过，模型调用/凭据/网络/评价读取均0。
3. `sA3_shared_time_red`：共享账仅计A1/A2，合成A1=15/A2=16/A3=42秒错误返回31而非73。仅将明确A3加入既有执行域枚举，修复累计扣账。
4. `sA3_directed_final`：新3项+直接影响的共享12调用拒绝、120秒到期停止、原S准入拒绝回归，共6项PASS。已有生产协议、worker、A1/A2失败及上游验收直接继承，无独立PUBLIC联网探针。

所有响应为合成PUBLIC，不是A1/A2回放，不声称真实S成功。测试使用Thesis及Windows Job 4GiB守护，每次前后核对本包/总额/写入余额，结果追加原账。

时限链未重写：A3为LONG_AUTHORIZATIONS精确项→sender HTTP120秒→RecommendationRun模型预留135秒→adapter以冻结reservation_deadline取根/预留窗口的最小值；最后保留145秒、1生成及1500输出。外Job在本次实际余额减10秒停止，回收≤5秒；运行器根额度为余额减20秒。A3入口额外取min(历史余额,1769.082)，生成min(共享余额,10)，输出参数min(共享余额,81920)。正式/未授权模式无新豁免。
