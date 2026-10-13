# Standards：商品证据规则修订，第四轮

- 固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`。
- 固定目标：`995dbfc129a299401c712140e285111e9be30b62`。
- 差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...995dbfc129a299401c712140e285111e9be30b62`；提交 `c6e23a8`、`4d2040b`、`882f188`、`020b0f3`、`995dbfc`。
- 标准来源：本会话用户工作准则、AGENTS.md、docs/agents/issue-tracker.md、docs/agents/domain.md、docs/agents/triage-labels.md，以及实际读取的 mattpocock-skills code-review smell baseline。未找到 CODING_STANDARDS.md 或 CONTRIBUTING.md。

## 硬违反

**0。** 本轮生产修改仍限于新版解释器：独立分号陈述、明确储存指令、无添加声明、质地及用途边界和部分配料解释，均有公共 CLI 复现测试及逐行为红绿记录。旧配置、目录、评论、规格和历史验收未进入修改差异。独立校验只按已批准的风味排除原则显式修正一条历史代表例预期，并保留旧注释及更正依据，未将新生产判定复制为 oracle。项目路径、最小依赖与公共入口约定保持一致。

## 启发性判断

**0 项可行动 smell。** 新版解释器、旧版解释器和独立对账脚本中的相似结构受“保留旧行为”和“独立验收”约束，不建议抽取共同判定而扩大范围。上下文识别集中于一处角色映射；新增语义修正未引入需求外框架、类型体系或扩展钩子。现有 JSON 状态及证据字典适合当前审计产物，未发现需要额外抽象才能解决的 baseline smell。

## 限制

仅静态审查上述固定提交，未运行 Python／Conda 或测试。已读取 75 项测试通过日志，不声称独立执行。正式全量新产物不在目标提交中，其验收及真实用户历史覆盖由主代理报告；本报告也不替代独立 Spec 语义审查。

结论：Standards 0 项发现；无需 Standards 修复。
