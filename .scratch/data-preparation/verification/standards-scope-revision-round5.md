# Standards：商品证据规则修订，第五轮

- 固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`。
- 固定目标：`cdb2b955eaa24386dd8603512c90584df852afe9`。
- 差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...cdb2b955eaa24386dd8603512c90584df852afe9`；本轮新增提交 `cdb2b95`，此前提交及逐文件标准检查沿用第四轮，并复核全部新增实现、配置与验收记录。
- 标准来源：本会话用户工作准则、AGENTS.md、docs/agents/issue-tracker.md、docs/agents/domain.md、docs/agents/triage-labels.md，以及实际读取的 mattpocock-skills code-review 的 12 项 smell baseline。没有 CODING_STANDARDS.md 或 CONTRIBUTING.md。

## 硬违反

**0。** `identity_catalog.py` 的修正直接对应独立审查和全量新入选样本暴露的反例，配套公共 CLI 行为测试及实际红绿记录。独立新增 `grain-A-1.1.1.json`，没有覆盖 1.1.0 配置；拒绝记录显式区分结构对账通过与语义验收失败，并保存此前六项产物摘要。旧 04／05、研究材料、规格、公共准备入口和依赖均未改写。未借本轮冻结工单 06 的清洗、资格或充分性规则。

## 启发性判断

**0 项可行动 smell。** 两份版本配置的重复是保留旧版及可复现的明确要求，不建议消除。新版身份与成分解释仍集中于已有模块；新增上下文角色和商品形态修正未带来无需求的框架、钩子或类型体系。独立 oracle 的摘要及集合运算重复服务于独立验收，不建议与生产判定合并。未发现可依据 baseline 要求扩大重构的地方。

## 限制

仅静态审查固定提交，未运行 Python／Conda 或测试。读取了 83 项通过日志，不声称独立执行；1.1.0 的语义拒绝不能以测试或结构对账掩盖。1.1.1 正式全量新产物尚未纳入此固定差异，不作漏实现判断；实际验收及 Spec 语义由相应流程判断。

结论：Standards 0 项发现；无需 Standards 修复。
