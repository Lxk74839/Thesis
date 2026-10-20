# 真实S第一次失败、局部修复完成、第二次因收尾门未开始

BASE85e06ff，时限/共享额度候选6a63d56，真实响应后局部协议候选ee9d2cc。两者分别完成同范围独立Standards/Spec，均无阻塞。复用已有A/R/worker/原S与上游验收，本轮无独立诊断请求。

PUBLIC TDD：首次测试临时路径不符合旧RootBudget要求，不是目标RED；修正后以S_engineering_limits复现旧时限配置拒绝。修复后，原S夹具9次各延后45秒仍发布；120001毫秒返回到期停止且无重试；sender向transport传递120秒、过期不发送；跨两尝试第13个意图被拒绝。新许可真实1493装配/预检无模型、Key或网络。定向6项（含直接受影响既有拒绝/usage用例）及新授权预检通过，未重跑全套。

## 真实A1

authorization_id=S-COMPLETE-ONCE-20261021-A1；run_id=P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A1；task_key=a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4。完整1493候选，实际POST602539字节。

终态failed_model，reason=unsupported_output_type。真实HTTP200、返回gpt-6-luna；output_item/unsupported_output_type，output_index0、field type、item_type reasoning。这次确实观察到reasoning项，依据来自响应类型诊断，而非从reasoning Token推测。模型调用/worker/共享发送意图各1，count/other/retry均0。原生解析input255485/output156，cached0、reasoning47属于156子量；原始native_usage归档null，费用null，计量unknown/incomplete。

真实A已取得候选数0、核验0、G=[]；未运行工具；recommendation_count=null、publication_path=null（未发布，不能填成已交付0项）。实际审计和预算位于data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A1/audit.json及budget.jsonl。P1真实产物根目前22,284,185字节，64MiB未超；旧证据未删。guard_denied网络/凭据/评价均0，认证读取1次。

## 局部修复及未闭合部分

原normalizer把所有reasoning项当未知输出拒绝。按实际类型定位及公开协议，新增只接纳空reasoning元数据的限定分支并记录安全结构；其余形状继续拒绝，不关闭strict。手写PUBLIC fixture先复现相同unsupported_output_type，再GREEN，并验证未知字段/类型及角色Schema额外字段仍拒绝；不是A1全文回放。具体字段/非空内容在A1中未归档，修复是否适配下一真实响应仍待真实复验，不能标成S已成功。

A2未启动、无claim/run/审计、不消耗剩余额度。delta_poll检查本包只余112.940秒，进入120秒收尾窗口；两轴结论均已取得，但不能再启动新工程尝试。没有自动补发、第三次尝试或延长额度。

余额：本轮真实调用1/12、剩11；请求输出参数cap已扣8192/98304、剩90112；真实执行15.0341833/1800秒、剩1784.9658167秒（包含进程和保存）。余额不复活A1、不重置计数。A2后续仍须通过本地资源准入，读取A1审计/共享账、使用ee9d2cc或后续同候选双轴认可版本，不能因本记录自动启动。

时限改动只适用两个精确许可：HTTP120、每模型预留135秒，最终145秒含出版收尾，根限额为执行余额减20秒，外层Job在余额减10秒停止并给回收≤5秒。冻结预留/根期限/HTTP期限均取最小；旧grant及严格模式保持旧要求。未知计量不填零，无人民币费用硬上限。

资源结算见resource-closeout.json；新工作段从本轮恢复开始，不含两轮之间用户等待，历史账前缀及历史超限保留。任务14整体未完成；S未通过所以不运行M、异常、Q或正式100。下一序列仍为V00/M→V01/M→V05/M→V06/M→Q1/M→Q2/M，随后只读实际A/G/组件/独立参考评价衔接；六M各12生成合72、评价0API仅是既有待确认提案，未执行或新增授权。

最终本包保守计费611.0598292/600秒，超11.0598292秒，**本地包资源验收未通过**。最后检查尚余3.940秒，随后按15秒归档/Git/交付保守上界结算导致计费上界超出；该15秒不称实测，也不撤回、冲销或扩额。累计offline3373.2084699/3480秒，余106.7915301秒，新增写入32,320,101/134,217,728字节。新执行15.0341833秒单记，历史跨域合计3446.8413761秒；原所有超限记录保留。此追加仅澄清收尾资源，不启动测试、代码修正或第二次S。
