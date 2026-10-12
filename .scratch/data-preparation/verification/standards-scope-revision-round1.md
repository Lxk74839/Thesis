# Standards：商品证据规则修订，第一轮

- 固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`。
- 审查目标：`4d2040becf59cbee5f891189ca9d36530ac020dd`。
- 范围：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...4d2040becf59cbee5f891189ca9d36530ac020dd`，提交 `c6e23a8`、`4d2040b`。
- 标准来源：本会话用户提供的工作准则，项目 `AGENTS.md`，`docs/agents/issue-tracker.md`、`docs/agents/domain.md`，以及实际读取的 mattpocock-skills code-review 技能 smell baseline。

## 硬违反

**0。** 新增配置、诊断、执行记录与测试均在 Thesis；旧配置和旧验收文件不在差异中。新增行为经既有 `prepare_data.py` CLI 观察，没有第二个正式准备入口或新增依赖。执行记录承接新版，保留旧 Answer，符合本地工单及最小修改约定。

## 启发性判断

**0 项可行动 smell。** 新版独立披露解释与保留的旧版解释存在相似结构，但用户要求保留旧版行为，抽取共同解释器会扩大旧行为的改动风险，本轮不据此建议重构。诊断脚本独立遍历字段用于对账，不建议复用生产判定来生成独立校验的预期值。小型字符串状态及字典符合当前 JSON 审计边界，无需额外类型体系。

## 限制

本轮为静态 Standards 审查，未运行 Python、Conda 或测试，未判断研究规则的语义正确性、全量目录结果或用户历史覆盖；这些由 Spec 审查及主代理独立验收确认。不存在 CODING_STANDARDS.md、CONTRIBUTING.md、GLOSSARY.md 或相关 ADR，不创建占位文档。

结论：Standards 0 项发现；无需 Standards 修复。
