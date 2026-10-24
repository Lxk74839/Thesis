# 协议版本、固定8探针、累计账与独立运行

Type: task
Status: needs-triage
Blocked by: 03-runtime-protocol-gaps

保留所有旧绑定/响应/错误。新版协议、命名空间、health和绑定路径分版本；物理总账1504含旧14不重置。固定medium/full8形状，双轴通过后直接启动至V00评价；具体原始错误保留，不无界调参重试。

## Comments

2026-10-24：原预算摘要和所有旧绑定保留；新协议、计划、审查、绑定已固定版本，并由独立PowerShell入口实际启动。8探针成功，特征阶段出现新协议错误后执行安全Stop，worker已退出。累计89次含旧14；B0/I1主对照未启动。另1条本地超时被旧发送包装记录failed，但原始诊断send_state=unknown，已审计单列未决且不重发；不改写原terminal。已生成独立S5停止后部分评价，不冒充evaluate-v00阶段完成。结果及资源见../results.md。
