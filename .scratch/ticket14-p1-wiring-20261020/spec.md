# 真实运行器接线与D1 P1离线准备

Status: claimed

BASE：1d688a3ddee04f634773ad62204a69f45fd55f19。继承A及PUBLIC验收，不重复探针，不复用已消耗的联网许可。当前API/真实推荐/评价/统计授权均0。

仅接4Router / https://4router.net/v1 / gpt-6-luna至既有ModelAdapter与RecommendationRun的R/S/M、六角色、工具及发布校验。共享纯Responses映射可小幅提取，旧模型和旧费率仅保留在旧分支，4Router路径不进入它们。不另写简化推荐demo。

公共测试边界：provider_fourrouter.prepare/usage_diagnostic/normalize与既有ModelAdapter.prepare/invoke；RecommendationRun在PUBLIC手写来源上的完整R/S/M；P1的只读prepare/execute入口、原assemble_task与运行器构造。原run_task的A阶段拒绝守卫不改。HTTP、计数、时钟及受控存储为外部边界，测试无真实发送。

完整C、H和安全输入仍由原装配/角色composer生成，不从独立参考补答案或原文。R无模型调用。4Router精确绑定、完整输入计数凭证、费率与预算、usage核算策略及执行授权缺失时，必须返回not_started/具体missing；保留RootBudget预留、final/commit/seal与未知usage挂起，不填0或伪造真实凭据。

未来原生usage只保存脱敏诊断：field_absent / value_null / parser_rejected / accepted；已封存PUBLIC回执无法判断原字段时保持unknown，不补发。价格与计数仍null。

P1仅冻结D1的V00/R、V00/S、V00/M三个既有task_key与pilot/父plan身份；不改pilot或正式计划。配置与一次执行授权草案独立于冻结文件，当前全部未授权。入口先集中检查条件，未满足不读取Key、不装配真实任务、不创建运行产物。离线测试用PUBLIC合成计数/费率且标fixture，不作为真实配置。

逐行为TDD；同一固定BASE...candidate独立Standards/Spec审查，只修本轮阻塞项并定向复验。只运行新增和直接受影响回归，不重验A或上游，不安装依赖，不改论文、冻结数据或评价器核心。

资源：本包命令自限300秒，240秒普通阶段/60秒收尾；写入32MiB，4GiB Job（含64MiB守护预留）。继承原离线1337.2683664001365/1800秒，原账仅追加p1wire_，T0不动。原生读写/Git/收尾30秒、8MiB保守上界计入，非实测，不重置额度。
