# 工单10正常SIM组件接受记录

2026-10-15（Asia/Shanghai）。正常SIM组件验收通过，工单10关闭。正式联合实验尚未完成；样本充分性尚未判定，模型未运行，区块链未部署。

本次用户在2b44220之后另行授权整数类型这一类缺口集中修复及验收收尾；I1—I6保持有效。原失败证据、错误passed审计、旧版与06—09材料保持原字节。未正式发布的版本继续使用sim-normal-1.0.0，正式配置及生产生成器未变。

## 实际生成与独立验收

| 对象 | 实际数目 |
| --- | ---: |
| 真实父商品 | 1,494 |
| SIM批次 | 1,494 |
| 六阶段事件 | 8,964 |
| 原始材料 | 11,952 |
| 接收登记 | 22,410 |
| R1私有参考 | 1,494 |

以上为正式CLI实产与独立程序逐对象核算的一致结果。全量原件/登记/策略/快照/请求的关联、精确字节摘要、ID、时间、严格整数、签发/读取授权均通过；R1状态Supported=1494，Refuted/Pending/Conflict均0。参考由独立标准库程序从原文事实推导，不导入生产校验函数、不读取目标/异常答案。

数据位于data/sim/grain-A-1.1.15/sim-normal-1.0.0；私有R1位于data/sim-reference/grain-A-1.1.15/sim-normal-1.0.0/r1-reference-1.0.0。真实评论仍只归父商品。全部新原件标SIM，主体是模拟allowlist，无真实签名或上链声称。

## 公共行为与审查

固定候选cf97cb108c57c92beab0e70459cd777decb8605e完成一次完整回归：226项通过，107.944秒，Thesis Python3.13.16，新增依赖0。循环19—25均真实RED→最小GREEN，覆盖主记录/快照组件bytes/records、输入bytes、counts、cutoff、配置与业务版本/序号/时间；合法0/2^53−1及策略布尔继续GREEN。旧已关闭问题沿用原证据。

固定755f277基线，两个独立代理分别复审：Standards硬违反0/阻塞0，保留原P3命名建议1；Spec发现0/阻塞0，原P2关闭。非阻塞建议未扩展修改。正式生成运行HEAD为d650eeec72fc3ad7b4c97503c4b37f54b08c0400、worktree_dirty=false；这比审查点只增加回归/审查归档，五份源码与审查Git对象的SHA逐份一致。

## 复现与保护

新空root重新通过唯一CLI生成并独立核查，六稳定组件逐字节相同，snapshot_id及1494条参考行逐字节相同。一致复用返回原主记录，主记录SHA与字节未改。跨运行实际时间及工作树状态只在各自主记录，不进入稳定组件。

本次起始982份保护文件全部字节不变；原919清单仍为918份字节不变及此前已归档的.gitattributes新文件规则追加，旧规则前缀保持，受保护内容变化0。原论文、研究材料、06—09和历史失败均保留。保护程序首次并行启动遇到Conda共享TMP冲突，尚未进入Python；已保留启动失败，随后在同一Thesis环境顺序运行通过，无代码或数据修订。

## A1—A14证据索引

| 验收行为 | 实际证据 |
| --- | --- |
| A1参数与批准依赖 | 原S1循环01—03/08及最终226项回归 |
| A2目录覆盖 | 全量check的1494/8964/11952/22410与唯一父商品 |
| A3封闭字段、SIM、整数 | 全量核查及本次循环19—25 |
| A4 ID/对象 | 全量原件/登记逐对象核查及DEMO黄金向量 |
| A5原件/文件摘要 | 每条登记原字节与六文件摘要、D4/D5字面量、损坏拒绝 |
| A6时间 | 原循环06和全量配置/原件/登记双时间核查 |
| A7当前/历史有效性 | 零售半开区间，其他七材料无TTL；全量通过 |
| A8来源授权 | 固定SIM主体/allowlist、读取范围及全量登记核对 |
| A9 R1组合 | 独立1494条sample+report推导；有效fail/缺绑定反例 |
| A10参考独立性 | 独立程序源码SHA、原件定位、原人工例与09四态核对 |
| A11输入隔离 | 仅五项绑定、目录最小投影、私有/metadata哨兵不变性 |
| A12新空复现 | 六组件与参考字节、snapshot_id相同 |
| A13复用/保护 | 主记录不变、冲突/junction拒绝及982份保护 |
| A14接受门禁 | 全部gates通过后独占写独立接受记录；生成主记录仍pending_separate_record |

## 正式证据

- [独立接受记录](../../records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json)
- [生成主记录](../../records/sim/grain-A-1.1.15-sim-normal-1.0.0.json)
- [全量独立check归档](verification/ticket10-independent-full-check.json)
- [固定候选完整回归](verification/ticket10-regression-cf97cb10.json)
- [两轴分别报告](verification/ticket10-integer-code-review.md)
- [新空目录复现](verification/ticket10-reproduction-d650eeec.json)
- [原材料/旧版本保护](verification/ticket10-protection-d650eeec.json)
- [接受记录摘要及实际数量](verification/ticket10-delivery-evidence.json)

原授权、当前授权、协议/配置、六组件、独立程序/参考/check、公共测试、复现/保护与两轴报告的路径及实际SHA均由接受记录绑定。接受记录没有自含摘要，其摘要保存在delivery-evidence。这里只接受正常SIM组件；异常场景归11，正式样本与统计设计归12，模型工具及区块链部署留后续，不将1494个模拟批次解释为独立真实用户或现实品质验证。
