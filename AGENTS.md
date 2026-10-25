# Thesis

## 项目约束

- 工作根目录为 D:\Work\Codex\Project\Thesis；新文件和写入操作均在本项目内完成。
- 论文及原有研究材料保持只读；新产物使用独立路径，不覆盖原材料。
- 论文题目保持“一种基于区块链与多智能体技术的农产品可信推荐方法”。
- 保留全链路证据管理与多智能体推荐双模块，以及需求解析、推荐管理、用户画像、农产品画像、生命周期追溯、推荐依据核验六角色。
- 数据路线采用真实谷物商品与评论，加同商品模拟供应链；历史评论保留在父商品层，SIM 来源明确披露。

## 执行流程

- 开展数据规格或实验工作前，读取 research/数据修复方案与验收草案_20261010.md 和 manuscript/论文初稿_表达与实验结构修订版_20261010.docx；研究草案不替代经确认的正式规格。
- 实施前明确并确认需求、验收条件和公共测试接口；配置与规格草案经用户确认后写入。
- 数据规格必须解决对象关联、独立样本充分性判定和统一联合实验，并隔离模型输入与评价标签。
- 依赖安装、项目代码运行、测试和构建均显式使用 Thesis Conda 环境；环境不存在时先按已确认的运行时要求创建。
- 当前环境为 D:\Work\Codex\Project\Thesis\.conda\envs\Thesis，使用 conda run -p 显式指定；TEMP/TMP 使用项目 .tmp，包缓存使用项目 .conda/pkgs。
- 迁移后继续工单前，读取 docs/operations/project-migration-20261019.md；继承原资源账与未完成状态，历史记录中的旧路径保留为当时事实。
- 保持实现简洁、修改范围最小；完成后按验收条件报告实际结果。

## Agent skills

### Issue tracker

规格与工单使用本地 Markdown，位于 .scratch/<feature-slug>/。见 docs/agents/issue-tracker.md。

### Triage labels

使用五个默认分流标签。见 docs/agents/triage-labels.md。

### Domain docs

采用 single-context：根目录 GLOSSARY.md 与 docs/adr/。见 docs/agents/domain.md。
