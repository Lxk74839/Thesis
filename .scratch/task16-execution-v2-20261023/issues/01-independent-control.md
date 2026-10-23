# 01 修订费用与实现独立运行控制

Type: task
Status: resolved
Blocked by: 无；用户本轮明确授权本范围，不包含真实API

规格：[spec.md](../spec.md)。仅S4 PowerShell/CLI与持久化接口。

交付：给定中转价的费用拆分、V00优先阶段矩阵、独立PowerShell启动/状态/续跑/停止、请求意图与结果复用、原24小时/10GiB继承账、无API夹具测试、固定候选双轴审查和启动说明。

验收：未就绪真实启动无网络；成功不重发；未决持久保留；已完成槽复用；Resume不重置预算；后台独立存活/可查询；暂停/关闭间隔记等待；真实算法缺失时明确not_ready。

## Comments

2026-10-23：原算法工单01—05不在本轮冒充完成，原草案保持。此工单实现运行控制并将未就绪门禁做实。

## Answer

独立PowerShell/Thesis控制、指定价格预算、固定V00优先阶段、不可刷新原账和持久请求索引已交付。24项无API测试通过，三轮固定候选审查后Standards/Spec分别PASS；最终控制候选097015bb71319eaab900f6b35a4a4750dc6dccf9。见[验收](../validation.md)、[启动说明](../runbook.md)、[双轴报告](../reviews/round3.md)。真实API为0，生产仍not_ready。本resolve仅关闭本轮控制子任务，不关闭原算法/开发评价工单。
