# 推荐系统论文中的智能体指令版式：原文核对

核对日期：2026-10-25。本文只记录论文证据与面向新图的排版推断，不改动实验、数据、模型或正文文件。PDF 页码从文件第一页起按 1 计数；RecMind 另列正式论文印刷页码。网页 PDF 文本用于定位，实际版式由本地原 PDF 页图逐页核对。

## 1. AgentCF：最直接的指令块依据

使用作者上传的 [arXiv v1 原文](https://arxiv.org/pdf/2310.09233v1)，不是二手示意图。

| 原文位置 | 视觉与内容证据 | 原文 URL |
| --- | --- | --- |
| 附录 C.1，PDF 第 12 页，延续至第 13 页 | **无 Figure/Table 编号**。双栏、横线分区，阶段标题和智能体标签加粗；指令与响应分别标记。不是有完整外边框的卡片。 | [C.1，第 12 页](https://arxiv.org/pdf/2310.09233v1#page=12)、[续页](https://arxiv.org/pdf/2310.09233v1#page=13) |
| C.1，第 12 页左栏前向交互 | 系统指令连续包含身份、用户记忆与候选物品记忆占位符、任务步骤、注意事项，以及 `Chosen CD` / `Explanation` 输出字段。另有禁止编造偏好的约束。 | [原文第 12 页](https://arxiv.org/pdf/2310.09233v1#page=12) |
| C.1，第 12 页左下至右上 | 用户画像更新指令跨栏延续；输入包括旧记忆和先前解释，输出限定为更新后的自我介绍，并约束长度及内容边界。 | [原文第 12 页](https://arxiv.org/pdf/2310.09233v1#page=12) |
| 附录 C.5，PDF 第 16 页 | **无 Figure/Table 编号**。先列不同专家身份，再分草稿、协作建议、修订、评价。协作指令要求只给建议、不替同事修改；修订指令要求直接交付成品，并允许不采纳无价值意见。 | [C.5，第 16 页](https://arxiv.org/pdf/2310.09233v1#page=16) |
| Figure 1，PDF 第 3 页 | 这是框架及优化案例，含简化的系统指令和响应；不是 C.1 的完整角色指令。 | [Figure 1，第 3 页](https://arxiv.org/pdf/2310.09233v1#page=3) |

**取证结论：**引用其完整指令排版时，应写“参考 AgentCF 附录 C.1/C.5”，不能编为“AgentCF 图 X 的提示词模板”。以上定位与版式均已核对实际页图。

## 2. RecMind：附录指令证据，不是完整提示词图

采用 [ACL Anthology 正式原文](https://aclanthology.org/2024.findings-naacl.271.pdf)；[官方书目页](https://aclanthology.org/2024.findings-naacl.271/)给出 NAACL 2024 Findings、4351–4364 页。对应预印本为 [arXiv:2308.14296](https://arxiv.org/abs/2308.14296)。

| 原文位置 | 视觉与内容证据 | 原文 URL |
| --- | --- | --- |
| 附录 A，PDF 第 12 页，印刷页 4362 | **无 Figure/Table 编号**。双栏正文，粗体行内小标题区分工具说明、搜索、SQL、自启发指令；没有包围完整提示词的外框。 | [附录 A，第 12 页](https://aclanthology.org/2024.findings-naacl.271.pdf#page=12) |
| 附录 A 左栏 | 工具权限以项目符号列出；参数使用花括号，如 `{question}`、`{database_info}`。SQL 说明限制可查询信息范围，SQL 转换指令限制只输出查询语句。 | [原文第 12 页](https://aclanthology.org/2024.findings-naacl.271.pdf#page=12) |
| 附录 A 右栏 | 自启发指令显式接收任务、历史步骤与当前步骤占位符，并规定有替代方案与无替代方案时的输出。 | [原文第 12 页](https://aclanthology.org/2024.findings-naacl.271.pdf#page=12) |
| Figure 1，PDF 第 2 页，印刷页 4352 | 两个细边框并排比较规划轨迹，以粗体标签重复区分推理、动作、观察；局部底色突出差异。这是执行示例，不是完整角色指令。 | [Figure 1，第 2 页](https://aclanthology.org/2024.findings-naacl.271.pdf#page=2) |

**取证结论：**在正式版本中未找到有图号/表号的“完整单角色提示词图”。实际可引用的完整指令来源是附录 A；Figure 1 可借鉴字段标签与局部高亮，但不能称为提示词模板图。

## 3. 对“用户画像智能体”新图的排版推断

以下为本次设计建议，不是论文原图复刻，也不主张上述论文规定了这五项角色要素。

1. **标题只用“用户画像智能体”。**不用“提示词模板”副标题；采用黑灰细线、白底、稳定字号与左对齐正文，不加入卡通或机器人。
2. **用一个连续指令框，按“系统指令—用户输入—输出格式”纵向分区。**参考 AgentCF 的阶段横线与明确标签，将原文双栏跨栏形式改为单框，避免读者追踪续栏。
3. **五项角色信息写成可执行系统指令。**身份说明服务谁；目标说明要形成什么结果；职责写成执行步骤；协作写明接收谁的材料、向谁交付什么；边界写明证据限制和不承担的操作。它们是框内段落标签，不做五张介绍卡片。
4. **动态材料全部集中在用户输入区。**统一使用 `{用户交互记录}`、`{现有画像}`、`{协作反馈}` 等一种占位符形式。花括号做法可参考 RecMind 附录 A；不要把实例内容与系统规则混排。
5. **输出区展示真实字段与填写规则。**字段须由主代理按当前项目协议核实；用字段名、值占位符和缺失处理规则呈现，避免仅写“输出结构化画像”。参考 AgentCF C.1 将输出规范放入指令本身的做法。
6. **视觉重点落在协议。**只对区段标签、变量和关键边界做有限强调；不照搬 AgentCF Figure 1 的装饰性图标，也不复制 RecMind Figure 1 的完整推理轨迹。

建议图注措辞：**“用户画像智能体的系统指令、输入变量与输出格式。指令展示形式参考 AgentCF 附录 C.1/C.5 与 RecMind 附录 A，具体角色内容和交互协议按本文方法定义。”**图注中的“参考”应指版式与指令组织，不暗示论文提供了本文的用户画像角色或本项目输出字段。

## 4. 可直接视觉复核的本地材料

以下均保存在当前研究目录内。页图直接由列出的官方 PDF 渲染，没有裁切提示词区域或改写原文。

- [AgentCF 原 PDF](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/agentcf-2310.09233v1.pdf)
- [AgentCF C.1，PDF 第 12 页](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/agentcf-2310.09233v1-p12.png)
- [AgentCF C.1 续页及 C.2.1，PDF 第 13 页](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/agentcf-2310.09233v1-p13.png)
- [AgentCF C.5，PDF 第 16 页](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/agentcf-2310.09233v1-p16.png)
- [AgentCF Figure 1，PDF 第 3 页](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/agentcf-2310.09233v1-p03.png)
- [RecMind ACL 原 PDF](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/recmind-naacl2024.pdf)
- [RecMind 附录 A，PDF 第 12 页/4362](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/recmind-naacl2024-p12.png)
- [RecMind Figure 1，PDF 第 2 页/4352](D:/Work/Codex/Project/Thesis/.scratch/meeting-role-refinement-20261025/recmind-naacl2024-p02.png)

自检：只使用论文与官方论文发布源；已实际查看相关整页图；将图号与附录号分开；未为无编号指令块编造图表编号；未修改源码、Word、数据或实验，未调用推荐模型 API。
