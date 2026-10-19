# Spec 独立增量复审

日期：2026-10-19。BASE：`69918e613fd700fd33c53a0ded5557b604487fcc`；固定 candidate：`85e1c85d4f7115bf6b4684544b27350ef671d6cb`。

依据仍为已确认提案 R01—R05、`authorization-t0-a-storage-repair-20261019.md`及固定资源包。先检查`git diff b1a50e37714edeebee68a8837ee19273df0a56bd...85e1c85d4f7115bf6b4684544b27350ef671d6cb`，再结合先前逐项审查确认`69918e6...85e1c85`总增量。原独立报告`verification-storage-spec-b1a50e3.md`保留。

结论：**阻塞 0 项，非阻塞 0 项；本有限存储组件的规格审查通过。**

定向修复只在`iter_prepared_objects`读取前补齐 objects、manifest、pack及旧 catalog 的既有`_path`检查（`t0_catalog.py:125`），拒绝 Windows junction、符号链接及其他重解析路径。该变化服务于提案“旧目录/旧接受只读”和有界来源保护，不改变 W/P、metadata、prepared_id、投影或去重规则，不增加根计划或供应商访问。

新增公共测试使用冻结 PUBLIC 对象创建真实 Windows junction，经公共 reader 和独立 CLI 验证拒绝，最后移除测试 junction。TDD记录新增228真实RED、229最小GREEN、230相关17项合并通过；本轴只检查记录及测试代码，没有重新执行。其余生产、守护、检查器和验证模式相对已审候选未变；总增量仍在已确认白名单内。迁移前已有的 AGENTS.md 工作区修改不归因于本修复。

本报告只执行静态审查，未读取另一轴报告，未运行项目代码、测试、诊断或 API，未访问原91.6GB开发目录。

接受边界：三件原开发对象的实际生产落盘、reader还原、独立核验、原件保护和资源实绩尚待授权执行；本报告不预先接受这些结果，不接受新格式 prepare 全链路或完整 A，不关闭工单12。`T0_A_incomplete`及原历史资源消耗继续继承。
