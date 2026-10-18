# C01—C06离线适配实施授权独立归档

日期：2026-10-18。来源为本聊天人类用户明确指令“确认model-preconditions-confirmation-20261018.md中C01—C06技术实施包，开始离线实施”及随后六条边界。

固定BASE：`023a6cc5b906541f01b56cfd805594719bfac557`。确认文件按原字节归档：[集中确认文件](model-preconditions-confirmation-20261018.md)，SHA256=`9cfd918e4b0e3e6316e2e0a62e6a42c8518c38ed990751448b2cbb215fcee08e`。不把其原“待确认”文字回写为历史已确认，也不修改原B表/接受记录。

确认C01—C06：零新增第三方依赖；按该文件白名单实施prepare、native格式、完整计数回执绑定、计数工具和必要公开fixture运行器集成；接受B10/T0衔接合同修订，但不执行T0任何阶段。本次确认后依上述文件直接实施，不再逐接口重复询问。

公共测试Seam已确认：ModelAdapter.prepare、ModelAdapter.invoke、InputCounter.count、必要RecommendationRun.run、计数工具公共CLI。按mattpocock-skills:tdd一次一个行为，实际RED后最小GREEN；公开事实和替代发送器，fixture计数不得成为官方回执。继承批处理接受，仅验证新增及直接影响的必要回归。

允许修改model_adapter.py、recommendation_runner.py；新增provider_openai.py、token_counting.py、tests/test_provider_openai.py、tests/test_token_counting.py、tests/provider_fixtures.py；本目录diagnostics/run_check.py仅增指纹范围，新增diagnostics/check_model_delivery.py及verification/、独立实施/接受记录。其余白名单和只读范围以确认文件§6为准，尤其evidence_access.py、环境锁、旧fixture/测试、原资料和reports只读。

唯一累计资源账仍为`data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl`；开始时40次/70.26800119999098秒，1,800秒额度剩1,729.731998800009秒，进程树4GiB含64MiB守护预留。失败/子进程/诊断均累计，不清零、不换账；所有项目Python显式使用既有Thesis Conda。无未结inflight。

完成后固定候选提交，以023a6cc为BASE，依mattpocock-skills:code-review由独立Standards/Spec代理静态审查，修复阻塞并定向复验/复审，最后另存本子项接受与资源记录。只提交本轮必要文件，不纳入reports或既有产物。

本轮实际供应商计数、生成、其他API均为0；不探测凭据、不安装依赖、不新增真实HTTP生成发送函数。108,800次和24小时只是未启用的规划封顶，C03只授权工具和许可检查实现，外部执行与费用授权仍0。替代HTTP的事件、费用和计数全部fixture，不能伪造成官方回执。

离线适配子项验收为终点；不宣称真实供应商可达或完整容量/G1/G2整体通过，不执行T0/P1、不冻结预算、不关闭工单12或冻结15。
