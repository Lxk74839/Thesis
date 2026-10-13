# Standards 第十八轮

固定差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...b3e879a5c8981cf2d645baefd2854c72c8443de7`。已读 19 个提交，复核最终实现及全部新增块，沿用此前完整逐文件检查。

标准：用户工作准则、AGENTS.md、docs/agents/{issue-tracker,domain,triage-labels}.md，以及实际技能的 12 项 Fowler baseline。

## 硬违反

0。部分披露状态跟随每份声明保存，公共 RED／GREEN 分别控制食谱、真实部分声明及 Salt 续行；保留原文及可检查的 partial_declaration。修改集中于现有解释器，未新增入口、依赖、正式数据视图或研究参数。旧日志、回放及审查报告另存保留，1.1.11 尚未正式生成。

## 启发性判断

新增 0。第十七轮同片段两次 context_role 已实际改为一次 boundary 计算，不再重复扫描；整理未引入抽象。历史轻微 possible Duplicated Code 仍在 `identity_catalog.py:157–159,168–170,179–181` 的三处冲突升级，维持已评估保留及维护代价。声明片段与部分披露布尔值组成的小元组足以表达本轮需求，不建议新增类型体系。

仅静态审查，未运行 Python／Conda；已读 112 项通过日志和 41／74 回放记录，不声称独立执行或全量验收。

结论：硬违反 0；启发式历史累计 2（1 已修复、1 评估保留），新增 0。
