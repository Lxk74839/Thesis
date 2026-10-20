# 2026-10-21授权与本轮规格

用户确认从73125bc继续任务14：新增600秒离线包，120秒收尾；累计总额2880秒；新增写入128MiB，4GiB。历史账只追加、超限不冲销。独立诊断一次（原许可未消费）和新D1/V00/S完整工程一次，合计最多13生成，count/other=0。诊断45秒（30HTTP+15保存），S360秒（350工作+10收尾），不得挪作离线预算。

先修两个已确认问题：transport异常明确usage=null数值、usage_diagnostic unknown、计量unknown；所有诊断执行产物≤1MiB，包含共享P1内产物、包内claim/回执/执行账/stdout，重复副本改短摘要。超额拒绝或立即停止，不漏计、不删除历史证据。

公共接口/验收：原diagnose一次sender错误路径及原main产物写入/执行guard边界；PUBLIC复现→修复→定向复验，同一BASE...candidate的独立Standards/Spec。复用原装配/mapper/sender/Windows worker，完整1493输入和strict不变。诊断保存真实stage/code与结构白名单，不保存正文/Key/Authorization。

真实诊断若明确可局部修复，可直接TDD和双轴复核后执行新S许可；不能猜测、忽略未知项、关闭strict或改变输入/渠道/协议以求成功。新S authorization_id=S-COMPLETE-ONCE-20261021，仅D1/V00/S既有task_key；新run/control/output，旧claim/回执不复活。最大12次，最终预留1次/1500，普通cap8192/最终1500、累计输出cap98304，POST2MiB/response64KiB，单HTTP30秒，零重试/回退/重定向。共享P1根64MiB含历史；缺usage保持null及unknown/incomplete，cost/rates/count未知豁免仅本次两个授权。严格模式不变。

执行成功必须实际A/G、发布规则、审计和预算闭合；无usage PUBLIC测试不代替真实S。错误/超时/未知发送/协议或模型不符保留证据并停止，不自动追加执行。本轮不运行M、异常、Q或100账户。收尾交付两次真实结果（若S未具备条件明确not_started）、资源账和剩余六个M任务及只读评价安排。审查等待每10秒检查，设置独立最晚停止时刻，不因等待进入120秒收尾窗口后开启新工作。
