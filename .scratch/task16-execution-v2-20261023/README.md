# 任务16：费用修订与独立执行入口

本修订接续[原方案](../macrec-algorithm-20261023/README.md)，只替代费用、阶段顺序及S4运行控制安排。保留原320人离线比较、既有哈希顺序前16人面板、六角色职责、公平条件、100人历史结果和论文原稿。本次真实API为0；推荐算法和真实运行计划仍待后续实施与确认。

- [执行规格](spec.md)：V00优先、阶段调用和完成判据。
- [修订预算](budget.md)：指定中转价、缓存/倍率未知项、时间与10GiB共享账。
- [运行说明](runbook.md)：下面命令的语义、故障处理及生产就绪条件。
- [实施工单](issues/01-independent-control.md)、[进度地图](map.md)。

独立PowerShell查询（可立即执行，不读取凭据）：

```powershell
Set-Location -LiteralPath 'D:\Work\Codex\Project\Thesis'
$task16Runner = '.\.scratch\task16-execution-v2-20261023\run-task16.ps1'
& $task16Runner -Action Status
```

未来算法、冻结计划及最终双轴封存齐全，并明确授权真实API启动后：

```powershell
& $task16Runner -Action EndDevelopment
& $task16Runner -Action Start -ConfirmLive
& $task16Runner -Action Status
& $task16Runner -Action Stop
& $task16Runner -Action Resume
```

本轮不执行真实Start。当前Status应为`not_ready`；此时即使指定`-ConfirmLive`也不能绕过缺失算法/计划的门禁。后续就绪后，Start返回后台监督进程编号，PowerShell和Codex聊天可结束；后台按冻结阶段自动推进至完成、预算到限或未决阻断。睡眠和关机不运行任务，但时间继续计入原24小时；开机后可独立Resume。

原账起算2026-10-23 20:28:03日本时间，截止2026-10-24 20:28:03；22小时后停止新模型派发。任何后续开发、人工等待和运行都使用这条原期限。
