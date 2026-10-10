# 工单 02 固定基线代码审查

实际使用 mattpocock-skills 1.3.1 的 engineering/code-review/SKILL.md；Standards 与 Spec 分别由两个并行子智能体检查。审查仅静态读取，项目运行与测试由主智能体使用 Thesis 环境执行。

固定起点：b59611e97b6eedf07c4e624884c48570fbfa2cdd。初审 HEAD：6c694bd58c0a9a1054cb26fc637616b7d6902e1c。修复复核 HEAD：9e455e396260beee75b920451edf3bec02dd44e8。

完整差异命令：`git diff b59611e97b6eedf07c4e624884c48570fbfa2cdd...HEAD`。修复增量：`git diff 6c694bd58c0a9a1054cb26fc637616b7d6902e1c...HEAD`。

提交列表：

- 9e455e3 fix: bind incomplete HTTP diagnostics to current attempt (ticket 02)
- 6c694bd feat: acquire and diagnose full metadata through public entry (ticket 02)

## Standards

Standards 复核：0 项明确标准违例，0 项需处理的启发式异味。

已确认 HEAD 为 `9e455e396260beee75b920451edf3bec02dd44e8`，结合原完整差异检查本次增量：

- `prepare_data.py:37,107` 的诊断重置与 HTTP 异常捕获只调整相关失败路径，符合 AGENTS.md 的“实现简洁、修改范围最小”。
- 新增测试通过同一公共入口复现具体异常，没有引入额外生产接口或不必要抽象。
- 工单讨论追加在 `## Comments` 下，符合 `docs/agents/issue-tracker.md`。
- 核查记录区分获取时与当前实现摘要，保留原来源事实，未修改论文或研究材料。

本次仅做静态复核，未运行项目代码或测试。

## Spec

修复后 Spec：**0 个未解决发现，两项 P2 均关闭。**

- “不完整来源得到明确诊断”：[异常捕获](C:/Users/Kane/Documents/CodexProject/Thesis/prepare_data.py:107)已包含 `HTTPException`，能够处理 `IncompleteRead` 并保存 `source_incomplete` 记录。[新增公共入口夹具](C:/Users/Kane/Documents/CodexProject/Thesis/tests/test_prepare_data.py:192)覆盖 chunked 截断，检查机器状态及异常类型。
- “提供可追溯的原始来源和诊断结果”：[错误行文件](C:/Users/Kane/Documents/CodexProject/Thesis/prepare_data.py:37)在每次获取开始时创建或清空。[夹具](C:/Users/Kane/Documents/CodexProject/Thesis/tests/test_prepare_data.py:201)覆盖首次下载失败及旧坏行残留；[说明](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-metadata.md:62)明确空文件须结合失败状态与零扫描计数解释。

完整来源记录、来源清单和已确认规格的摘要均保持一致；当前实现摘要与修复记录吻合。未发现新的规格偏差或范围扩张。本轮仅只读静态复核，未运行项目代码或测试。

## 初审与修复留痕

初审 Standards 为 0 项明确违例、0 项需处理代码异味；少量计数器初始化和诊断写入重复不足以支持强制抽象，项目的简洁与最小改动要求优先。

初审 Spec 两项 P2 分别指出：

- `response.read()` 遇到 chunked 截断时抛出 IncompleteRead，其继承 HTTPException，原捕获范围不包含它，入口直接 traceback 而无法保存本次机器诊断。
- 错误行文件原先仅在下载成功后清空；失败报告始终指向固定路径，首次下载失败可能没有文件，再次下载失败可能引用旧来源错误行。

主智能体对每项分别增加公共入口测试：先实际复现失败，再修改最少生产代码使之通过。第十项测试原先无法解析空 stdout；第十一项在首次失败无文件和旧文件残留两个子场景均失败。修复后全部 11 项测试通过；未重新运行无关实验或冻结研究规则。

审查结果：Standards 待处理 0、最严重项无；Spec 初审 2 项 P2、已关闭 2、待处理 0、最严重未解决项无。
