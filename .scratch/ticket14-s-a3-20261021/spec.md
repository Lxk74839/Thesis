# A3完整S工程复验（本轮确认）

BASE 6e0bb40；继承生产协议e5ea9ed验收，不重跑独立PUBLIC。仅新增S-COMPLETE-ONCE-20261021-A3：D1/V00/S同一冻结任务，独立run/claim/目录；不复活A1/A2，不运行M/Q/异常/正式100。

公共测试接口：完整RecommendationRun(S)经ModelAdapter.prepare→生产normalize→原工具→原发布；合成PUBLIC reasoning（含非空summary/content和不透明encrypted_content）、工具调用及下一轮原样续接，无usage保持未知。首次已满足的行为如实记GREEN。另以prepare_p1/assemble_task/build_runtime及既有非执行_preflight检查1493候选、模型输入隔离、冻结来源、预算/最终预留与时限；无真实claim/Key/API。

仅增加精确A3许可和既有入口的第三个编号，不改方法、协议、工具、框架。A1/A2/A3共享12生成/98304输出参数/1800秒；本次最多10生成、81920输出参数、1769.082秒（含回收/保存），HTTP120秒，保留最终1生成/1500输出与145秒最终阶段。内根为执行余额减20秒，外Job余额减10秒，回收≤5秒；冻结预留窗口照旧。不重试、不重定向/回退，count/other0，费用null，工程计量unknown/incomplete。

本包600秒离线、120秒收尾、累计5400、128MiB/4GiB；A3执行单记并在本地时钟扣除。共享P1产物64MiB含旧证据。原账只追加、历史超限保留，用户等待不计。离线/双轴检查通过立即执行一次；失败保存结构诊断并停止，无A4。
