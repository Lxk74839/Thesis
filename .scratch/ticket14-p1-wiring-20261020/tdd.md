# 增量TDD与必要回归

BASE：1d688a3ddee04f634773ad62204a69f45fd55f19。API 0，凭据读取0，未执行D1推荐/评价/统计。

| 实际行为 | RED→GREEN标签 |
| --- | --- |
| usage absent/null/rejected/accepted诊断 | 001→002 |
| ModelAdapter保留角色/工具/Schema，精确映射gpt-6-luna | 003→004 |
| 计数/费率/预算/授权缺失先拒绝且保持null | 005→006 |
| 原R/S/M完整流水线、M六角色和发布 | 007→008 |
| D1三任务只读准入与未开始 | 009→010 |
| 延迟认证的真实HTTP桥接 | 011→012 |
| 正文不可用不能推断usage不存在 | 013→014 |
| PUBLIC夹具能力不能授权D1 | 015→016 |
| 空limits/reserve不算完成配置 | 018→019 |
| 共享运行器工厂/时钟/会话接线 | 020→021 |
| 已知原生token不因未知缓存费用而丢失 | 022→023 |

共11次真实RED→GREEN；诊断同一接口分两步完善，不伪称11项不同测试。usage故障全流水线（三种情形均一调用停止、无重试、无原值泄漏）首次即通过，未制造RED。费用1170夹具单位、正文与来源隔离等新增断言首次通过。

026新增11项测试最终通过（unittest 1.156秒）：R模型调用0，S/M各9次PUBLIC替身请求，M六角色、完整两个候选及原发布校验保留；三方法均成功发布PUBLIC结果。计数100/输出30、费率与成本均明确PUBLIC夹具，不是真实模型或费用结算。

025直接影响回归29项通过（unittest 1.766秒）：旧ModelAdapter/native Responses映射与预算、一个既有批式六角色质量贯通、两项默认8KiB边界。旧模型仅用于已有离线夹具回归，4Router路径不调用旧模型/旧费率。未重跑A、上游或T0。

027实际CLI prepare M返回not_started、API 0、缺项清单，退出码2为预期拒绝；不当作RED或真实模型失败。测试审计钩子拒绝socket及真实凭据/private路径；唯一HTTP桥接用PUBLIC-key文件与注入HTTP替身。无新依赖，所有Python经Thesis Conda/原4GiB Job守护；新包原账只追加p1wire_标签。
