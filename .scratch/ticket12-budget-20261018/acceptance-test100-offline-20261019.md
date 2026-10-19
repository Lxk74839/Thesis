# 100×18 离线准备子项交付与验收

日期：2026-10-19（Asia/Shanghai）。本记录仅接受 **100×18离线准备子项**。工单12保持开放，旧G1仍未通过，`T0_A_incomplete`保持；未签发正式实验完成或G2—G6接受。

## 固定范围与交付

原交付 `5de02867ed8dd98389d9c5c7f4d56285a4094207`；确认归档BASE `d5992e67fb44f88e12545880584dbb9118a37fb7`；双轴审查及独立检查所对应的精确代码candidate `7a5f1412845b8a3db47562f71facce10a5d2dc4f`。随后提交仅归档本记录、检查结果、资源和引用索引，代码candidate不变。

冻结目录为 `data/recommendation-runtime-audit/ticket12-100x18/plan/`：

| 文件 | 实际内容 |
| --- | --- |
| `sample-users.jsonl` | 100个唯一测试账户、排名及抽样摘要；开发账户交集0 |
| `root-references.jsonl` | 100份来源行/偏移/长度/SHA定位与C/H/b摘要 |
| `scenes.jsonl` | V00—V15及Q1/Q2共18份共享快照映射 |
| `user-scenarios.jsonl` | 1,800份用户—场景引用绑定 |
| `tasks.jsonl` | 5,000个唯一方法任务键，repeat=1，3,400个计划模型任务 |
| `plan.json` | 来源权限、组件摘要、抽样规则/种子、null模型绑定及计划身份 |

计划ID：`9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088`。008仅冻结一次真实来源清单，其后未重抽、补用户或重建真实计划。

抽样种子为ASCII `20261019`，对原1,283测试账户按 `SHA256(b"Thesis|ticket12|test100|v1\0" + b"20261019\0" + root_id_ASCII)` 的摘要字节升序取前100，平手按root_id ASCII升序。只使用原池的账户ID/split投影，不依模型结果或评价标签选择。原320开发账户隔离。

16证据场景各100份R/S/M，Q1/Q2各100份完整M：R本地1,600、S模型1,600、M证据1,600、M质量200。3,400是计划模型任务数，不是API调用数。任务行仅含task_key/binding_id/method/repeat/uses_model，不嵌入完整C/H/b、批次映射、证据或请求正文。

## 实现与运行边界

新增 `experiment_runner.build_plan/run_task`；按需接口以实际请求绑定prepare/count/usage及单根预算，保留必要正文/返回一次及SHA引用。仅新路径采用登记kind、target_id UTF-8、version、evidence_ref UTF-8的稳定事实顺序。新增守护与独立检查CLI；未更改旧T0组装行为、旧恢复检查器或上游生成器。

真实计划 `execution_authorized=false`；模型、渠道、base_url、价格、正式API预算均null，真实任务在sender前拒绝。公开外部替身只消费手写公开夹具，合成单位不是官方token或报价。终态重复调度复用结果，未决意图停止；未知usage/计数漂移保留原返回与占用，不发布。

真实100账户推荐0、效果评价0、bootstrap 0。供应商推理/计数/其他API分别0。没有恢复旧9,600项请求目录；没有复制原商品、评论、完整候选或已接受SIM，没有修改原材料。原8主比较、新8分别报告及质量单独评价的后续口径保持；本次不作100账户样本充分或精度承诺。

## 验证与独立审查

- [TDD逐行为记录](tdd-test100-on-demand-20261019.md)：12组实际RED→GREEN；首次满足行为如实记录，无人为制造RED。新增8场景首次即通过已有核验器，因此 `evidence_verification.py`未修改。
- 045实际运行30个新增及7个直接影响旧回归：30新增和5旧项通过，2旧项在setUp因旧硬编码输出目录被守护拒绝，未运行断言。046只将这两项的公开夹具目录置于允许路径，复用原方法体及断言，2/2通过。结论是 **30新增+7直接影响回归分批通过**；没有宣称一次37/37或运行全库。
- [独立检查结果](../../data/recommendation-runtime-audit/ticket12-100x18/independent-delivery-7a5f141.json)：049退出0，重新核对真实清单、场景接受映射、原引用字节与摘要；核13份有效公开运行审计的请求/返回、prepare/count绑定及usage/终态账，包含合法非空actions_scope的null原文。核对161份受保护文件、原离线账历史前缀及T0账未变。
- [Standards轴](review-test100-standards-20261019.md)：阻塞0、非阻塞0；[Spec轴](review-test100-spec-20261019.md)：阻塞0、非阻塞P3一项。P3是事实/回执重载再组装的组合回归覆盖缺口，按用户边界保留，不扩展非阻塞修复。

公开原件继续保存在项目 `.tmp/recommendation-runtime/test100-delivery-20261019/`，旧回归公开夹具在 `.tmp/recommendation-runtime/test100-legacy-regressions/`；不移动或重封原审计。故意损坏的负例保留，不计为有效审计。原stdout位于原离线审计目录 `ondemand_*.txt`。最终 [evidence-index-test100-20261019.json](evidence-index-test100-20261019.json) 提供文件定位、长度与SHA，不复制整套数据。

47份原始stdout一并归档，其中原生子进程失败输出含CR/CRCRLF。原样保留，不清理原记录空白；审计目录新增的 `.gitattributes` 仅对 `ondemand_*.txt` 禁止Git文本转换，逐份核对Git对象与工作区原始字节一致。文档空白检查单独通过。归档阶段的失败检查亦包含在原账120秒原生操作保守预扣内。

## 资源结算与自检

以 [resource-closeout-test100-20261019.json](resource-closeout-test100-20261019.json) 为完整结算；原离线账仅追加，原历史前缀不变，旧T0账完全不变。包含所有RED、失败、Conda启动/守护与收尾；可精确计时部分和保守上界分别列出。原磁盘上界1,242,221,743字节继承另列，未删除退款。

本包900秒、原离线总额1,800秒、新增累计写入1GiB（含256MiB收尾预留）和4GiB内存限制均满足。所有项目Python使用Thesis专属Conda、项目TEMP/TMP及缓存，无依赖安装。最终仅提交本范围产物；已有AGENTS迁移改动及其他未跟踪迁移/恢复资料未纳入本次提交。

自检结论：名单100、场景18、绑定1,800、唯一方法任务5,000、计划模型任务3,400、开发交集0、供应商API 0；新增及直接影响验证完成，独立检查通过，两轴无未处理阻塞。接受范围止于本离线准备子项。
