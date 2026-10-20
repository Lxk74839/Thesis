# S发送前拒绝修复通过；新一次真实复跑协议失败并停止

代码candidate69e618bd6d748df0ccc23b29667dca091c479cb7，BASE6c038ed。原失败审计+完整1493装配+非零持续递增时钟，实际prepare→reserve→invoke仅外部transport哨兵：RED同一拒绝，deadline超过冻结窗口约84.75毫秒；改为冻结reserve receipt同源期限后GREEN。没有容差、延期或删除校验，仍受根期限和HTTP30秒约束。诊断见diagnosis.md/red-diagnostic.json/fixture-control-diagnostic.json，均明确fixture。

过期、越界、预留不匹配、重复消费仍拒绝；旧新授权不得交叉；新授权真实1493预检及发送控制链到哨兵（含实际POST编码大小）通过；无usage原PUBLIC S仍完整发布、计量unknown。定向矩阵7项及最终两项针对回放/交叉授权测试通过。固定同一candidate独立Standards PASS、Spec PASS，无新增阻塞/P3。R、worker、回执及上游验收复用，未重跑全套。

新授权S-DEADLINE-RETRY-20261020，run_id=P1-D1-V00-S-S-DEADLINE-RETRY-20261020。仅D1/V00/S工程任务a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4。新控制目录/claim/执行账/回执/输出与旧尝试分离；旧六份claim/回执/账/attempt/audit/budget SHA全部保持，旧许可未复活。

## 真实结果

实际尝试1次，Responses生成POST **1次**，HTTP200，返回模型gpt-6-luna，实际POST602,539字节。首响应随后在本地响应协议校验返回engineering_response_error，terminal=failed_model。现有脱敏诊断没有保留更细的失败条件，不能据此断言是usage缺失或哪一条响应schema不符。立即停止，未追加请求、修解析器或补答案。

完整候选1493，核验0，G=0；recommendation_count=null，publication=null，无真实推荐结果。审计位于data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-DEADLINE-RETRY-20261020/audit.json，同目录attempt.json/budget.jsonl保留。实际回执为本目录execution-result.json。

usage诊断accepted：input_tokens255485、output_tokens240、cached_input_tokens0、reasoning_output_tokens157。这些是该响应已解析的原生数值；原始native_usage归档字段仍null，失败响应的运行累计input/output仍null，均保持不改。请求reasoning.effort=none；返回reasoning计数如实记录，不据此推断渠道行为。未知费率及实际费用null，无人民币硬上限，计量unknown/incomplete。

HTTP请求ID=null，response_id=resp_0758eebe18b4dd68016ad76821c9ac8190bb872f8f4274c9b2。count/other API均0、重试0、授权凭据读取1次（仅认证）、独立评价读取0。请求输出容量消耗8192（配置容量，不是实际Token）；最终1次/1500容量保留未被挪用。P1根含旧目录，实际15,819,084字节、守护保守计费17,092,630/67,108,864字节。

## 资源结算

继承offline1918.8261996，新包121.1866019/300秒，余178.8133981秒，45秒收尾预留满足；本地写入保守计费47,420,957/134,217,728字节。native30秒及32MiB为全部非测试/非代理操作和收尾上界，非实测。offline累计2040.0128015/2280秒，历史1800秒下超限及早先写入超限均保留。

新执行Job实测22.7686426/360秒，启动前段按保存review至stdout创建的文件时间间隔保守计费2.1723799秒（包含Job启动重叠，不称纯Conda实测），新执行合计计费24.9410225秒。旧S原执行账逐行seconds实际汇总3.2109987秒（旧快照曾报3.1989222，本轮不修改旧账或旧快照，以原账汇总）；offline+两次S独立执行计费合计2068.1648227秒。执行Job峰值60,338,176/4GiB。完整结算见resource-closeout.json，原账前缀与T0 SHA不变。

结论：发送前拒绝代码及离线/双轴验收通过，本包本地资源验收通过；真实S工程链路失败；Token/费用计量不完整。新尝试已消耗，不自动重跑。未启动M、其他场景、推荐效果统计或正式100用户实验。
