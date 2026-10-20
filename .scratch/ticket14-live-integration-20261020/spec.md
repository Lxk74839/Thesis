# A 阶段离线接线规格

Status: ready-for-agent
BASE: dcd7f1971a41af7dd1b29421e250596af06faffd
来源：draft.md、confirmation.md；最新人类确认优先，B明确不在本包。

## 公共 Interface 与验收

1. assemble_task(plan, task_key, *, execution_record=None)：只读核完整组件、行引用、根／场景／权限绑定，输出安全装配与明确missing；history原值→H、b→base_scores，重新核输入指纹；许可仅精确接受来源。不构造预算账、会话运行、模型或网络。
2. run_task(..., execution_record=None)：保留原PUBLIC接口；新装配结果与注入PUBLIC运行器精确匹配后复用原run／终态／intent规则。真实dev/test无论传什么runtime都只能configuration_required，started=false；模型配置null，B未实现，不能删除旧守卫。
3. RecommendationRun：仅对有装配绑定的初始投影做校验接入；实际A在结束时按现有trace单份封存，audit/task/result记录acquired_ref。组件A摘要与封存同一原值；重复调度不再写。不从参考或源会话补取原文。
4. experiment_io.load_evaluation_inputs(plan, *, execution_index, reference_sources)：只读核task、审计、publication、budget/trace、实际A/G/assessment/components以及独立参考；返回evaluation_plan和observations。失败/未执行/未决/缺记录/坏绑定/参考NA保留原口径，损坏不得填零冒充完成；无模型或取证能力。
5. 参考来源含target、完整C四态、精确BINDING、原始来源定位及摘要；原8/Q接已接受联合参考关联，新增8接工单11独立参考。只关联，不调用生产核验生成gold。实际产物转换不接收reference。真实评价入口本包禁用，PUBLIC文件验证其转换合同。
6. 少数试点按键外连接，开发评价视图仍有每人18场景50槽，未调度槽显式not_started，summary=incomplete；真实计划不变。Q仅完整M实际A/G/fusion/终态与原三组件，未知usage null，失败/重试全计，Q不重复计费。
7. 独立pilot manifest/tasks及成员证明：D1=015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e，8键沿用已确认草案，来源scope独立、父冻结plan_id与文件SHA引用、dev证明及正式100交集0。只冻结，不执行。配置五项null且execution_authorized=false。
8. 公共行为逐项RED→GREEN，手写PUBLIC原件、状态和手算期望，外部transport注入保留fixture。新增tests/test_live_integration.py；只运行新增和直接影响回归。固定最终候选做两个独立轴审查，只修本范围阻塞。

## 文件与资源

仅 experiment_runner.py、recommendation_runner.py、新experiment_io.py、新tests/test_live_integration.py、原run_check.py的新包守护分支，以及本目录控制/证据和独立pilot产物。评价器、Adapter/count/provider、上游、正式计划和T0只读。

900秒含草案30、启动/失败/审查/原生/收尾；180收尾预留，原1800总额并行约束。256MiB累计写入含草案1MiB、64MiB收尾，删除不退款；4GiB含64MiB守护。原生文件/文档/Git操作以明确保守上界计入，审查命令另外计账；不能把上界称实测。API全0，无新依赖。
