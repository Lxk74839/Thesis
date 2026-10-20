# 逐行为TDD实际记录

日期：2026-10-20（Asia/Shanghai）。BASE=7391477。公共seams已由人类确认：score_task、summarize、公开夹具CLI；run_check只承担本scope计量/路径/源码约束。

原始stdout在data/recommendation-runtime-audit/20261018-batch/eval100_*.txt；每次守护及Conda启动结算均追加原resource-ledger.jsonl。原始失败保留，未退款。下表编号对应eval100_前缀。

| 公共行为 | RED | GREEN |
| --- | --- | --- |
| 本包守护绑定 | 002_guard_red | 003_guard_green |
| 手算合法列表评分 | 004_score_red | 005_score_green |
| 整表门控/坏尾/重复/C外 | 006_gate_red | 007_gate_green |
| 未执行/失败/NA/缺记录 | 008_states_red | 009_states_green |
| 参考/执行绑定及完整键 | 010_binding_red | 011_binding_green |
| 空证明/覆盖/填充/Unassessed | 012_secondary_red | 013_secondary_green |
| M实际锚点与完整C均值 | 014_quality_red | 015_quality_green |
| 质量失败共享及禁止补证 | 016_anchor_red | 017_anchor_green |
| 固定权重的用户配对 | 018_pairs_red | 019_pairs_green |
| 缺任务不缩cohort/不补零 | 020_missing_red | 021_missing_green |
| F2配对区间/种子/索引 | 022_bootstrap_red | 023_bootstrap_green |
| n<2/退化区间/不宣称充分 | 024_small_red | 025_small_green |
| 场景分组及usage一次计量 | 026_reports_red | 027_reports_green |
| 公开CLI和绑定输出 | 028_cli_red | 029_cli_green |
| 缺执行记录的CLI不完整交付 | 030_cli_incomplete_red | 031_cli_incomplete_green |
| 控制组件不改原始因素/均值分母 | 032_quality_metadata_red | 033_quality_metadata_green |
| G作为固定集合/不扩张/无参考补证 | 035_G_set_red | 036_G_set_green |
| 固定NA cohort与补充有效权重 | 037_NA_cohort_red | 038_NA_cohort_green |
| 未知usage不能给完整总量 | 039_usage_missing_red | 040_usage_missing_green |

19组实际RED→GREEN。RED含首次不存在模块/接口，未制造假失败。034新增读真实data/越界写/网络、CLI错误scope/摘要/重复/越界/覆盖拒绝，均首次即绿，未改实现假造RED。

## 必要回归与交付

041选择test_root_budget的unknown_tokens和tool_and_model_retries两条旧测试，因旧setUp硬编码.tmp/recommendation-runtime被新scope路径守护拒绝，断言未运行。042仅把夹具根映射到.tmp/experiment-evaluation，但RootBudget自身journal白名单拒绝，断言仍未运行。043将公开夹具根限定到新的.tmp/recommendation-runtime/eval100-scoped-legacy子目录，并仅增加这一独立本包输出前缀；不改旧测试方法、生产RootBudget或旧运行材料。复用两条原方法体/断言，2/2通过。新测试文件内的外层适配用例检查实际testsRun=2且无error/failure。

044最终运行22个外层用例全部通过：21项新增行为及1个承载两条旧断言的隔离适配。不是新增22+旧2或全库验收。公开CLI样例首次留存因显式cleanup仍清理而未保留；只修测试夹具留存生命周期，045定向重跑该CLI用例通过并实际保留输出。评价器源码自040以后未变，守护仅固定本scope输出/源码约束。

公开样例：两名PUBLIC虚构用户、4个虚构候选、18场景标签，总100个公开任务（不是100名真实用户）；手算C1=.25、C2=.25、C3=C4=.18453512321427125。这些只验证实现，不作为任何真实推荐/效果/样本充分性成果。区间是公开夹具统计。

原975仅historical_planning_n说明，没有实施门槛/扩样/重抽。真实推荐、真实评价、真实统计及供应商API均0；模型/渠道/价格null。没有全库或上游重验收，没有旧P3/T0恢复。
