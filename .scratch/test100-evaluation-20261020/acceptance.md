# 独立评价器离线子项验收

日期：2026-10-20。结果：本离线子项通过。正式实验未执行、未完成；上游 ticket12/T0 状态不变。

BASE：73914774e2fedd53071c7240c50b28b85be86194。
独立双轴共同审查的精确候选：564f097faa554ba06337996a772d9aae8de68b08。
后续收尾只归档本包文档，三个源码文件与该候选的原始 Git blob 完全一致，见 verification-final.json。

## 实际交付

- experiment_evaluation.py：纯 score_task(task, execution, reference)、summarize(plan, task_scores) 及仅限 PUBLIC 夹具的小 CLI。
- tests/test_experiment_evaluation.py：手写候选、取证原件、四态参考和手算期望；不调用生产输出生成 gold。
- 原 run_check.py：仅增加本包计账、输出/读取边界和源码绑定；旧路径与旧包账不清零。
- 输出任务评分、用户配对、场景汇总、失败/NA/未执行/管线错误、usage 和未绑定成本；完整与不完整公开样例均实际留存，原始字节摘要见 evidence-index.json。

原8场景主要比较、新8逐场景及 Q1/Q2 分开；固定用户配对/权重/种子/区间和小样本规则。未执行为 null，失败按既定规则评分；参考 NA 带原因。缺记录和错绑定阻止完整交付，不缩 cohort。usage 含失败/重试，Q组件不重复计费，未知与未绑定价格保持 null。

Q组件只从完整 M 的实际 A、G、终态和冻结 fusion 核一致性。复用已接受纯质量评分组件时只传实际 A 和 fusion，完全不传 reference，不取证、不补证、不生成 gold。目标及参考四态独立。

## 验证

按 mattpocock-skills:tdd 完成 19 组初始公共行为 RED→GREEN、4 组 Spec 修复 RED→GREEN；如实记录首次即通过的边界，不制造失败。TDD详情及失败路径见 tdd.md。

最终 eval100_056 在 Thesis 专属 Conda 环境执行新增测试文件：26 个外层用例通过（25 项新增行为；另1项复用两条原预算测试断言，实际 testsRun=2）。unittest 报告 2.824 秒；启动与守护另计。仅运行新增及直接受影响用例，未运行全库或上游验收。原始输出：data/recommendation-runtime-audit/20261018-batch/eval100_056_repaired_public_delivery.txt。

公开样例仅2名虚构 PUBLIC 用户、4个候选、18场景标签及100个公开任务。手算 C1=.25、C2=.25、C3=C4=.18453512321427125；浮点结果在1e-12内。完整样例为 public_fixture_complete；缺执行记录样例为 public_fixture_incomplete、保留100个计划任务并报告管线错误，CLI退出2。所有文件与当前评价器源码 SHA 已核对。这里的100任务和区间均是夹具验证，不是100名真实用户成果。

18个保护文件摘要未变，包括冻结名单/任务/计划、研究材料、运行器及T0账。原离线账前563604字节摘要未变。verification-final.json 与 evidence-index.json 保存检查结果。

## 双轴独立审查

| 轴 | 最终独立代理 | 共同区间 | 结果 |
| --- | --- | --- | --- |
| Standards | /root/evaluation_standards_clean | 7391477...564f097（完整SHA见报告） | 0项文档规范违反/阻塞性异味 |
| Spec | /root/evaluation_spec | 同一BASE...candidate | 0项剩余问题，首轮4项阻塞均已关闭 |

两轴分别报告，不合并重排。见 review-standards-564f097.md、review-spec-564f097.md。首轮可选 P3 保留，未扩范围修复。

一次 Standards 复审因 Markdown 通配符误返回另一轴首轮报告而作废；改由无历史上下文的新代理重审同一候选。偏差、原报告与费用保留，见 review-standards-isolation-retry.md。另一次原生 Git whitespace 检查因字节绑定 JSON 的 CRLF 失败；只为本包 JSON/JSONL 增加局部属性，保留原字节，后续检查通过；失败原生命令包含在60秒上界内。

## 资源结算

- 本包计账239.6350683/600秒，含失败、启动、审查及收尾；剩余360.3649317秒，未自动转作新授权。120秒收尾预留未被普通阶段挤占。
- 计账中30秒为获批草案只读上界、60秒为根代理原生命令/编辑/Git/收尾保守上界，首次启动计4秒为保守向上取整；这些均不称实测。其余守护、启动与代理命令采用工具计时，明细见 resource-closeout.json。
- 继承离线账550.0812735秒，追加后789.7163418/1800秒；未借上一包余量。T0账原字节不变。
- 新增累计写入计账50,476,320字节（48.137970/128MiB），含16MiB原生文件/Git/临时写入上界；删除不退款。32MiB收尾预留保持。继承原写入上界1,521,656,722字节另列，未清零。
- 受控项目进程树峰值提交量47,063,040字节，加64MiB守护预留共108.882813MiB；Windows Job按4GiB上限约束。原生 PowerShell/Git 审查和收尾进程未逐进程峰值计量，此数不能称全进程实测峰值。
- 无新增依赖；所有项目代码/测试显式使用 D:\Work\Codex\Project\Thesis\.conda\envs\Thesis，TEMP/TMP及缓存均在项目。

模型、渠道、价格保持 null。真实推荐、真实评价、真实统计、供应商 generate/count/other API 均0。975只保留历史说明，不作100用户实施门槛，不扩样、重抽、返工或宣称样本充分。未重开旧T0/P3，未增加通用报表或恢复框架。
