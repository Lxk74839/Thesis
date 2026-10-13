# Standards 第十七轮

固定差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...e20102a0f48e242c79436b62fda2a50b1aecfb43`。已读 18 个提交及完整文件清单，复核最终生产差异和本轮全部新增修改，沿用此前逐文件检查。

标准：用户工作准则、AGENTS.md、docs/agents/{issue-tracker,domain,triage-labels}.md，以及实际技能的 12 项 Fowler baseline。

## 硬违反

0。重复声明与食谱边界分别有公共 RED／GREEN 和真实 Salt 续行控制。旧回放备份，1.1.11 保持尚未全源生成的状态，没有虚构 1.1.12。未新增依赖、入口或冻结工单 06。

## 启发性判断

新增 1 项轻微 possible Duplicated Code：`identity_catalog.py:100` 的 `context_role(fragment) and context_role(fragment)[1] == 0` 对同一片段重复执行完整角色扫描。可保存一次返回值再检查位置，不需增加抽象；没有功能缺陷证据。

历史轻微重复 1 项仍在 `identity_catalog.py:154–156,165–167,176–178`，维持已评估保留及维护代价，不称已消除。其余领域条件及独立 oracle 不要求为消除启发式而扩大架构。

仅静态审查，未运行 Python／Conda；读取 111 项通过日志及 41／74 条回放记录，不声称独立执行或全量验收。

结论：硬违反 0；启发式累计 2，新增 1（轻微重复计算），历史 1 已评估保留。
