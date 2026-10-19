# Spec 独立增量审查

日期：2026-10-19。固定 BASE：`69918e613fd700fd33c53a0ded5557b604487fcc`；candidate：`b1a50e37714edeebee68a8837ee19273df0a56bd`。审查命令：`git diff 69918e613fd700fd33c53a0ded5557b604487fcc...b1a50e37714edeebee68a8837ee19273df0a56bd`。提交：`c8533d8`、`b1a50e3`。

正式依据为已确认提案的 R01—R05、`authorization-t0-a-storage-repair-20261019.md`及固定资源包 JSON。仅执行静态只读审查；未运行测试、Python、诊断或 API，未访问原开发对象目录，未读取 Standards 报告。

结论：**本次有限存储包未发现阻塞或非阻塞规格偏差。**

- 提案要求“只保存一份完整 W”“只删除顶层四字段”“metadata 保留原 prepared 字段”。`t0_catalog.py:67`保存原 canonical W，保留其余字段；`:122`按固定投影重建 P，验证原字节、摘要及六字段身份。重复对象核对非 source 绑定，编译器仍逐条保存请求 source（`:821`）。未改变 mapper、上游或业务算法。
- 提案要求“损坏段、索引错误、partial 关闭”拒绝，且独立检查“不导入生产代码”。生产 reader 与独立 `stored_objects`均限制段索引及解压长度；独立 `object_info`重算 W/P、mapper/角色摘要及身份。`check-objects`明确输出`object_store_verified_only`，原完整`check`继续要求覆盖完整。
- 提案要求“只复用既有 PUBLIC”“本包时间/磁盘门”。新增测试使用冻结对象和派生损坏副本；生产 prepare 在本包内拒绝新增计划。`run_check.py`绑定确认、原账前缀与封闭扩展，分别限制两域包时间，写入前累计计费，并保留 Job 内存门。
- R05 要求“先程序 TDD 和双轴审查无阻塞，再有界读取三件”。`validate_storage`先核对候选源码和两轴记录，再按首轨迹至 final 的 17 行/1 MiB 上限选择三件；原件累计 24 MiB，必要来源读取 64 MiB，使用生产 writer/reader及独立检查，保留`T0_A_incomplete`。

三件实际落盘与最终资源实绩仍须由授权的后续执行记录证明；本报告不预先接受其结果，不扩大为 prepare 全链路或完整 A 验收。

Spec：0 项发现，0 项阻塞。
