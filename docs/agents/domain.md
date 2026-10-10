# Domain Docs

本项目采用 single-context：根目录 GLOSSARY.md 保存领域术语，docs/adr/ 保存架构决策。

## 探索代码前读取

- 根目录 GLOSSARY.md。
- 与当前工作相关的 docs/adr/ 中的 ADR。
- 如果后续存在 GLOSSARY-MAP.md，按其指向读取与当前主题相关的词汇表。

文档不存在时继续工作，不因缺失而提前创建占位文件或建议补建。由 domain-modeling 在实际解决术语或决策时按需创建。

## 使用领域术语

工单标题、规格、假设和测试名称使用词汇表定义的术语。发现缺口时先核对实际领域语言，再交由 domain-modeling 处理。

## 决策冲突

方案与现有 ADR 冲突时，明确指出 ADR 编号、冲突内容及重新讨论的依据，不默默覆盖。
