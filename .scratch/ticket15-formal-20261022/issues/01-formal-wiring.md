# 01 正式任务接线、预算与启动门禁

Type: task
Status: resolved

规格：[spec.md](../spec.md)，来源是2026-10-22用户原指令。

## Answer

新增独立formal入口，复用已验收的装配、prepare/invoke、工具、运行器和计分器。
每task_key独立一次尝试、发送意图先持久化，5000任务原顺序按50项分批，双进程。
本实现工单完成后仍须取得一次统一启动确认；本轮生成/count/其他供应商API均为0。
验收证据及双轴审查由同目录tests.json、review.md、startup.md收口。
