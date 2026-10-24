# 明确角色协议、严格解析和真实响应回归

Type: task
Status: needs-triage
Blocked by: 无；本轮明确确认及授权

按spec.md先复现14条真实响应，逐项TDD修复角色结构、需求解析隔离、偏好词形与探针/主运行一致性。复用无关算法验收，不改变评分或选样。

## Answer

原生角色Schema、严格JSON、需求解析隔离、真实lover词形及探针一致过滤完成；14实际响应SHA引用和离线回归留档，旧6/8判定及失败记录保持。46项必要影响回归通过；代码待同一候选双轴审查，尚未发送新API。

## Comments

2026-10-24：上述实现随后在固定candidate 6fdce71f14f733857c76b9f71d9d28634051ea32完成双轴审查，8次真实medium/full探针均通过。正式特征阶段又暴露Lookup/Search重复索引及User操作与载荷不对应；原生生成Schema仍未覆盖全部宿主约束。停止运行，整体协议验收保持未完成；原14条历史记录不改。新反例见[03-runtime-protocol-gaps.md](03-runtime-protocol-gaps.md)。
