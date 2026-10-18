# T0-A 独立 Standards 复审原报告

日期：2026-10-18。轴：Standards。仅静态审查，未读取另一轴原报告。

- BASE：`88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a`
- candidate：`623faf14f4940c66c29f676f0b85f1ae8ea0a046`
- 完整差异：`git diff 88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a...623faf14f4940c66c29f676f0b85f1ae8ea0a046`
- 复审增量：`git diff 250de6baf1aede000795d1748e0737d847ba7f6c...623faf14f4940c66c29f676f0b85f1ae8ea0a046`
- 提交：`1c5036c Archive T0-A implementation and execution authorization`；`250de6b Implement offline T0-A request catalog and controlled trace preparation`；`623faf1 Close T0-A metadata permissions and controlled reply review blockers`。

## Standards 结论

**blocking：0；nonblocking：1（判断性 smell）；项目硬规则违例：0。Standards 无阻塞。**

沿用根 `AGENTS.md`、本会话人类 AGENTS 指令、`docs/agents/issue-tracker.md`、`triage-labels.md`、`domain.md`，以及 `mattpocock-skills:tdd` 的 SKILL、tests、mocking 规则和下列 Fowler 基线。没有新增仓库编写标准；原审查范围与静态限制保持。

**非阻塞，possible Duplicated Code**：`tests/test_t0_catalog.py:526` 与 `:547` 各自嵌入相同的外部文件访问陷阱。两处共有 hunk：

```python
'def audit(event,args):\n'
' if event=="open" and isinstance(args[0],(str,bytes)) and pathlib.Path(args[0])==trap:\n'
'  marker.write_text("forbidden body opened"); raise AssertionError("forbidden_target_open")\n'
```

入口分别为 module 和 path，有不同目的；但陷阱判定、marker 和异常需要同步维护。可在本测试文件抽取专用脚本生成 helper，保留两个公共入口的独立断言。依据为 Fowler Duplicated Code 启发式；这不是违反 TDD/项目规则，不影响本次执行门，不要求新增通用测试框架。

其余新增变更保持精准：元数据在正文读取前校验位置，交付路径闭合；固定排序键的配对排序和计划键集合仍是当前工作所需的局部实现。新增测试使用公开 I/O 审计陷阱和替代 sender，未模拟自身生产内部模块或测试私有 helper；理由/Issue 的字面期望来自原合同，发布门另经既有 run 接口观察。

未运行 Python、测试、A 或 API，未读取实际数据、身份键或另一轴报告。TDD 次序及测试结果仅作为已归档上下文核对。本轴结论不替代 Spec、实际覆盖、资源或容量验收。

## 完整 Fowler 基线

全部为判断性启发式；仓库明确规则优先，工具已检查项不重复报告。

- **Mysterious Name**：name does not reveal purpose → rename.
- **Duplicated Code**：same logic shape across hunks/files → extract shared shape.
- **Feature Envy**：method reaches another object's data more than its own → move behavior.
- **Data Clumps**：same fields/parameters travel together → small bundle/type.
- **Primitive Obsession**：primitive/string deserves a domain concept → small type.
- **Repeated Switches**：same-type conditional cascades recur → one mapping/polymorphism.
- **Shotgun Surgery**：one logical change requires scattered edits → gather related changes.
- **Divergent Change**：module changes for unrelated reasons → split reasons.
- **Speculative Generality**：unneeded abstraction/hook/configuration → remove.
- **Message Chains**：caller owns long navigation it should not know → hide the walk.
- **Middle Man**：wrapper mostly delegates without a role → remove.
- **Refused Bequest**：subclass ignores inherited behavior → composition.
