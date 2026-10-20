# 回执修正通过；一次S工程尝试失败并停止

代码candidate00c68e74d465d033ab3800256eb549b6710f6d9b，BASE896d3b8。只修改回执/准入处理；未改Windows worker、模型适配、推荐方法、数据、正式计划、评价核心或论文。TDD准确复现旧not_started导致拒绝后两项GREEN；同一候选独立Standards/Spec均PASS。既有S/R/1493预检及worker验收直接复用。

旧.scratch/ticket14-s-engineering-20261020/result.json保留原字节。启动父/子进程使用同一ensure_first_execution；claim、execution-result、execution-resources或实际attempt任一已存在即拒绝。新的实际回执为.scratch/ticket14-s-engineering-20261020/execution-result.json，独占写入，不覆盖旧记录。

执行前四类标记均不存在，记录见pre-execution-markers.json。使用原未消耗S许可一次，authorization_id=S-ENGINEERING-ONCE-20261020，run_id=P1-D1-V00-S-S-ENGINEERING-ONCE-20261020，任务键a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4。

实际回执：started=true，terminal=failed_model，完整候选1493，核验0、合格0，recommendation_count=null，publication=null。首个适配器调用在transport之前返回not_started；审计missing为S_engineering_reservation_or_deadline，request_sent=false、retryable=false。该统一拒绝码不能区分具体哪条条件失败，本轮不进一步定位或修复。不将测试通过当作工程链路通过。

实际生成/count/other API均0，model_calls=0；守护凭据及HTTP worker许可使用计数均0，评价读取0。首请求仅预留了8192输出容量，未发POST；这不是实际输出Token。原生usage/输入输出Token/费用/HTTP状态/返回模型/供应商请求ID均未知null（没有HTTP响应），不能标为field_absent。无真实推荐结果可展示。

审计：data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-ENGINEERING-ONCE-20261020/audit.json；同目录attempt.json和budget.jsonl均保留。本次工程尝试已发生并留下claim/执行账/attempt，不自动重试，不再次使用原许可。

本修正包保守计费80.2839958/120秒，含native20秒及16MiB上界（非实测），收尾预留15秒满足；本地累计写入上界16,781,449/67,108,864字节。离线累计1918.8261996/1980秒。S执行Job1.2109987秒，含Conda外层3.1989222/360秒，另域记账；合计1922.0251218秒，不把执行计入离线或反向挪用。P1共享根实际9,357,634/67,108,864字节；执行Job峰值62,017,536字节，受4GiB限制。详见resource-closeout.json及原执行资源账。

原offline账前缀、T0账、旧not_started均SHA核对不变。此前1800秒上限下超限38.542秒及早先写入超限继续保留，不追溯更改验收。

结论：回执处理和本包本地资源验收通过；S工程链路失败；Token/费用计量unknown/incomplete。R/M及正式实验均未执行。
