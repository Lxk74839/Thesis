# Issue tracker: Local Markdown

本项目的规格与工单保存为 .scratch/ 下的 Markdown 文件。

## Conventions

- 每个功能一个目录：.scratch/<feature-slug>/。
- 规格：.scratch/<feature-slug>/spec.md。
- 每张实现工单一个文件：.scratch/<feature-slug>/issues/<NN>-<slug>.md；从 01 编号，不合并为一个工单文件。
- 分流状态记录在工单顶部附近的 Status: 行；标签字符串见 triage-labels.md。
- 评论与讨论按时间追加到文件底部的 ## Comments 下。

## 技能要求发布到工单系统时

在上述对应路径创建 Markdown 文件及必要目录。

## 技能要求读取相关工单时

读取用户指定路径或编号对应的文件。

## Wayfinding operations

- Map：.scratch/<effort>/map.md，包含 Notes、Decisions-so-far、Fog。
- 子工单：.scratch/<effort>/issues/NN-<slug>.md；问题写入正文，Type: 记录 research、prototype、grilling 或 task，Status: 按该流程记录 claimed 或 resolved。
- 依赖：顶部的 Blocked by: NN, NN 列出前置工单；全部 resolved 后解除阻塞。
- Frontier：扫描未解决、未阻塞且未认领的工单，按编号取第一张。
- Claim：开始工作前设置 Status: claimed 并保存。
- Resolve：在 ## Answer 下追加答案，设置 Status: resolved，并将结论摘要与链接追加到 map.md 的 Decisions-so-far。
