# 新版正式分支反例与发送未决归类

Type: task
Status: needs-triage
Blocked by: 无；本轮停止后只记录，不自行创建新协议或再次派发

## Evidence

固定candidate 6fdce71f14f733857c76b9f71d9d28634051ea32；协议macrec-agri-v2。8个真实探针成功只覆盖指定Finish形状，不能证明正式工具循环可靠。原始请求、响应SHA与错误条件见../new-failure-evidence.json；所有历史记录保留。

- 5条生命周期角色Lookup/Search的候选数组含重复索引。现有原生Schema接受，但宿主macrec_evidence_scope拒绝。最小反例d37290e5bf：202项、200个唯一索引，尾部多出20,20。需要在生成协议中表达有界集合语义，并使宿主严格遵守同一规则；不得事后去重冒充原模型输出。
- d1f23636d9：User选择Info却返回preferences。现有action枚举和data.anyOf未关联操作与载荷；原生Schema接受，按所选操作的宿主校验拒绝schema:$.data:fields。需明确关联规则，覆盖正式Info/History/Lookup/Search等工具分支及Finish，而非只核对外层或探针Finish。
- 8f5aff5db1：管理者在派发额度耗尽时仍请求User，macrec_dispatch_exhausted_or_invalid。须验证观察、已完成职责和剩余额度如何进入管理决策；不通过扩大调用上限隐藏失败。
- dce085fef9：原始http_diagnostic.send_state=unknown，local_timeout，HTTP状态、usage均未知；现有发送包装把terminal记为failed。现有terminal保持原样，uncertain-send-audit.json明确未决且禁止重发。后续修复应让新请求直接归未决，并让状态/评价遵守未知语义，不能通过换版本、namespace或删除旧记录绕过。

## Acceptance for a later bounded repair

1. 先用上述原始反例和旧14条做离线失败回归；旧请求/响应/错误/terminal的SHA不变。
2. 原生生成结构和宿主实际业务约束一致；工具操作与载荷不可错配、候选无重复；主运行与探针使用同一校验语义。
3. 空画像、否定/冲突、引用和事实来源限制继续通过；评分公式、面板、候选与六组评分选参不变。
4. 未知发送立即持久化未决，不重发；恢复时保留未知请求所在决策的阻塞状态，不能改ID重新发送同一决策。
5. 新版本兼容性逐项说明并固定候选双轴复核。任何后续真实调用需处于仍有效的明确执行范围、原累计1504/10GiB及原时间界限内；本工单不构成新增探针、重试、延期或自动恢复授权。
