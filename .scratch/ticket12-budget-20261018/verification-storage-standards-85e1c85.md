# Standards 独立增量复审

日期：2026-10-19。BASE：`69918e613fd700fd33c53a0ded5557b604487fcc`；固定 candidate：`85e1c85d4f7115bf6b4684544b27350ef671d6cb`。

先审`git diff b1a50e37714edeebee68a8837ee19273df0a56bd...85e1c85d4f7115bf6b4684544b27350ef671d6cb`，再核对`git diff 69918e613fd700fd33c53a0ded5557b604487fcc...85e1c85d4f7115bf6b4684544b27350ef671d6cb`总范围。新增提交为`85e1c85 fix: reject object store reparse paths before reading`；原`c8533d8`、`b1a50e3`仍在范围内。

沿用前报标准来源：会话工作准则第3—7条、当前`AGENTS.md`、`docs/agents/{issue-tracker,triage-labels,domain}.md`、mattpocock TDD及tests/mocking规则、code-review十二项判断性smell。无新增适用标准。

结果：**阻塞0，非阻塞0，文档硬标准违例0，判断性smell发现0。**

- `t0_catalog.py:125`起仅对objects目录、manifest、pack及旧catalog入口复用既有`_path`边界，符合工作准则第4条最小改动；未引入重复验证框架或无关重构。
- `tests/test_t0_catalog.py:1035`起通过公共reader和独立CLI观察真实Windows junction的拒绝行为，没有调用私有helper；局部系统联接用于实际I/O边界，清理只解除本测试联接。符合TDD公共Seam及系统边界原则。
- TDD记录新增228真实RED→229最小GREEN及230相关17项合并验证；此次代码变化给出定向复验理由，未把旧静态通过当新源码通过。

总增量16文件：原Standards报告列明的14项完整范围（生产模块、测试、检查器、资源守护、验证脚本、两份诊断原件副本及授权/规格/证据/计量/TDD记录），加两份`verification-storage-{standards,spec}-b1a50e3.md`原报告。定向源码变化只在上述reader与公共junction测试；其余生产、守护、检查及验证源码保持前次固定candidate内容。因此总增量未发现新增标准阻塞。另一轴原报告只识别为留档文件，未读取正文；独立核验器必要重复仍按已确认独立性要求处理。

现有`AGENTS.md`工作区修改不属本candidate；未要求提交或撤销。仅静态读取源码和本轴相关记录，未执行项目代码、Python、测试、诊断或API，未读取原开发目录；原报告保留。此结论仅针对Standards轴，不替代Spec复审及三件运行核验。
