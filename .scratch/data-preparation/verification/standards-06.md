# Standards — 工单06

固定范围：`git diff 34aa1491b71906ec6e47e63ea6c8ecaec72154f2...a76a75aebfe9869472d841d0d96f181ebd413296`；仅提交 a76a75a，39文件，1401插入、2删除。

依据：[AGENTS.md](C:/Users/Kane/Documents/CodexProject/Thesis/AGENTS.md)、人类附加八原则、[issue-tracker.md](C:/Users/Kane/Documents/CodexProject/Thesis/docs/agents/issue-tracker.md)、[triage-labels.md](C:/Users/Kane/Documents/CodexProject/Thesis/docs/agents/triage-labels.md)、[domain.md](C:/Users/Kane/Documents/CodexProject/Thesis/docs/agents/domain.md)，以及实际插件的 [code-review](C:/Users/Kane/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/code-review/SKILL.md)、[TDD](C:/Users/Kane/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/tdd/SKILL.md)、tests.md、mocking.md。未发现 CODING_STANDARDS、CONTRIBUTING、GLOSSARY 或 ADR；未造占位。

**有据的文档标准违反：0。** 新增测试通过 prepare_data.py CLI及报告指向的产物观察行为，无生产内部导入或内部mock，期望采用明确夹具与字面量。15份RED均记录实际失败，对应GREEN逐项通过；完整回归日志记录164项、60.819秒、OK。保护记录的解释器位于项目Thesis环境。以上为提交内证据，本审查未运行Python、Conda或测试。

独立QA程序仅导入标准库；[verify_cleaning06.py:65](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/verify_cleaning06.py:65) 用SQLite的GROUP BY、min/max及严格更早的DISTINCT成员查询建立独立依据，并逐行核对产物与引用；131行起只读核验保护清单哈希，142行起只向verification的新路径写报告。固定diff未修改原稿、原研究材料或05来源。真实数据验收尚待执行，QA脚本存在不代表验收通过。

**判断建议：1，P3，非阻塞。** possible **Duplicated Code**：[review_cleaning.py:163](C:/Users/Kane/Documents/CodexProject/Thesis/review_cleaning.py:163) 的 `write_text(''.join(canonical(row) + '\n' for row in …), 'utf-8')` 在163、164、167、174、176、189行重复；序列化规则变更需同时修改六处。可在以后实际维护时合并为一个小写出函数；该重复本身未证明行为缺陷，不据此触发修订循环。

全部Fowler项已逐项检查。除上述Duplicated Code外，未发现需报告的 Mysterious Name、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest。启发均为判断建议；仓库规则优先，工具已管内容不重复。未混入Spec结论。

计数：硬规则0；Fowler1；阻塞0；最高严重性P3（建议）。
