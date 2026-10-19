# 工单12：有限存储组件实际验收

日期：2026-10-19。结果：**T0_A_storage_component_verified_only**。固定BASE为`69918e613fd700fd33c53a0ded5557b604487fcc`，最终源码candidate为`f97203ab2984b0d86006f72cee70e9a4e78230b1`。用户确认的R01—R05有限修复包已实施、独立审查并完成三件有界验证。工单12保持打开，原实际A保持`T0_A_incomplete`。

## 实际实现与公共边界

- [t0_catalog.py](/D:/Work/Codex/Project/Thesis/t0_catalog.py:53)：`PreparedObjectWriter.add/close`逐件保存一份完整canonical W，zlib level 1独立压缩拼包；manifest保存完整非正文metadata、段索引、版本、字节量和摘要。相同prepared_id严格核对绑定，只存一段，调用方全部请求引用保持。
- [公共reader](/D:/Work/Codex/Project/Thesis/t0_catalog.py:122)：固定删除W顶层四字段重建P，恢复四份prepare公共表示，再核对W/P字节、SHA及六字段prepared_id。旧0.1目录只读可识别；新目录为0.2，store为0.1。损坏、错误规则/版本、重复/越界索引、不完整store及重解析路径均拒绝。
- [独立检查器](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py)：自行解码，不导入生产writer/reader或mapper。新增`check-objects`只接受对象存储；原完整`check`仍要求完整覆盖与原门。
- 编译器与摘要recompute接入同一writer；本包显式禁止展开新根计划。prepare-only、count和invoke原拒绝门保持。未修改mapper、适配器、业务推荐及上游文件，未新增依赖。

新格式不签发prepare授权、官方计数或发送资格。完整新格式prepare/轨迹展开未运行，仍待将来独立受控方案；本次只验收实际测试到的存储组件。

## TDD、修复和双轴审查

[逐行为原始记录](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/verification-storage-tdd-20261019.md)保留199—232各实际RED、最小GREEN和首次GREEN。使用52件冻结PUBLIC对象；派生损坏/超界副本不产生根计划。最终17项存储行为合并通过；守护修复后仅做两项相关定向验证，未重跑生成型或无关已接受测试。

真实边界缺陷包括目录junction被reader跟随，228 RED→229最小修复→230相关17项通过。其后Git自动打包使审计预留分类误拦截：首次三件启动在读原件前失败，整个Conda调用3.9216015秒一次保守补记原T0账；Git产物改计只增数据账，历史loose以先前上界之和保守保留，231/232定向通过。原限制及历史账均未重置或扩大。

| 固定candidate | Standards | Spec | 后续处理 |
| --- | --- | --- | --- |
| b1a50e3 | 0发现、0阻塞 | 0发现、0阻塞 | 原报告保留；补充junction复现后修复 |
| 85e1c85 | 0发现、0阻塞 | 0发现、0阻塞 | 原程序接受保留；发现实际计量分类问题后另修 |
| f97203a | [0发现、0阻塞](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/verification-storage-standards-f97203a.md) | [0发现、0阻塞](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/verification-storage-spec-f97203a.md) | [新程序接受](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/acceptance-t0-a-storage-program-final-20261019.json)先归档，随后执行三件 |

两轴由各自独立代理静态审查，未互读另一轴正文，未运行额外项目测试、API或读取原大目录。以69918e6为BASE审总增量，对后续修复定向复审；各轮原报告不覆盖。

## 存储与三件实际核验

| 冻结PUBLIC组 | 对象 | 原对象字节 | 新pack+manifest字节 | 判定 |
| --- | ---: | ---: | ---: | --- |
| baseline | 26 | 1,710,684 | 111,074 | 小于10%，全字段往返一致 |
| longH | 26 | 3,861,096 | 118,208 | 小于10%，全字段往返一致 |

以上只统计对象存储，不是完整目录容量或全量压缩预测。相同输入两次存储物理字节稳定；环境为Python3.13.16、编译及运行zlib均1.3.2，不承诺跨codec版本稳定。

三件实际运行标签为`storage_repair_006_three_existing_validation`：[选择与component绑定](/D:/Work/Codex/Project/Thesis/data/ticket12-t0/storage-repair-validation-20261019/storage_repair_006_three_existing_validation/selection.json)、[生产往返结果](/D:/Work/Codex/Project/Thesis/data/ticket12-t0/storage-repair-validation-20261019/storage_repair_006_three_existing_validation/validation.json)、[独立核验结果](/D:/Work/Codex/Project/Thesis/data/ticket12-t0/storage-repair-validation-20261019/storage_repair_006_three_existing_validation/object-check.json)。正文、pack及宿主关联保留在本地输出目录，不纳入Git。

| 选择种类 | W字节 | P字节 | 字节/摘要/身份/metadata |
| --- | ---: | ---: | --- |
| 首个analysis | 602,440 | 602,361 | 全部与原件一致 |
| final前最后一个acquire | 2,529,048 | 2,528,969 | 全部与原件一致 |
| 首个final_submit | 2,021,687 | 2,021,608 | 全部与原件一致 |

按首条S/M轨迹读取17行、376,578字节即至首个final并停止。只读这三件原对象，合计22,234,142字节；含必要catalog元数据总读取26,462,299字节，分别低于24MiB与64MiB。没有枚举objects目录、另选样本或重新扫描完整requests。原component字节/SHA匹配，读取前后size/mtime保持；生产reader重建的整个prepared字典等于原件，独立核验3/3通过。新pack+manifest为739,626字节。

## 实际资源与保护

| 资源 | 实绩 | 已确认上限 |
| --- | --- | --- |
| 离线受控命令 | 本包17.15941320010461秒；原账累计234.88381950024632秒 | 包300秒；原总额1800秒 |
| T0三件包，含失败启动 | 3.9216015+0.8387693999975454=4.760370899997497秒；原账累计1802.1127592999999秒 | 包60秒；原总额1860秒 |
| 进程树内存 | 最大Job提交196,710,400字节；加64MiB守护为263,819,264字节 | 4GiB |
| 新测试/PUBLIC输出文件 | 188文件、4,246,069字节，保留失败/损坏副本 | 跨域共同磁盘账 |
| 三件验证全部输出文件 | 5文件、743,368字节 | 跨域共同磁盘账 |
| 006时累计计费写入 | 36,321,908字节，含Git产物和历史loose保守计费 | 数据248MiB；JSON收尾4MiB |
| 006时其它磁盘保守上界 | 1,297,927字节，含启动临时预留 | 其它审计4MiB |
| 最终全包磁盘 | 后附JSON记录收尾快照、未退款累计及预留；向上保守计≤40MiB | 全部新增256MiB |

时间按原guard开始至子进程结束的墙钟累计，包含失败、子进程和检查；首次pre-child拒绝额外按整个Conda命令墙钟保守补记一次。Markdown/JSON归档及只读静态审查不属于项目Python运行。未安装依赖或调用供应商。

[保护核对](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/verification-storage-integrity-before-validation-20261019.json)确认13件只读保护文件、两本原账前缀和52件冻结PUBLIC原件未变；PUBLIC state仍占用原12份，新根计划0。收尾JSON再核对源码接受指纹、原账前缀及只读文件。AGENTS.md原迁移修改保持，未纳入本包提交。

自检：代码、逐行为TDD、固定candidate独立双轴审查、三件生产落盘/还原/独立核验、两域累计时间和全新增磁盘均已交付。原91.6GB目录保留，原`T0_A_incomplete`及未完成计划继承；没有全量重跑、续编译、C/B/P1、生成/profile/I/O诊断或供应商API。不接受完整A、全量吞吐/容量或费用，不关闭工单12。

[机器可读验收与收尾快照](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/acceptance-t0-a-storage-component-20261019.json)保存产物SHA/字节、源码和原件保护结论、最终两账及跨域磁盘计量。该记录的complete仅指本有限存储包。
