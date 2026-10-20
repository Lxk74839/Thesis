# A 阶段离线接线验收

2026-10-20（Asia/Shanghai）。验收范围仅为 **A阶段离线接线**。真实模型接通、开发预实验及正式实验均未完成，也未执行。

BASE：dcd7f1971a41af7dd1b29421e250596af06faffd。
经独立双轴审查的最终代码候选：e34ef4a2a291e21184f5cc37e20a0d7983d2a1b2。
归档提交只增加本包验收和资源证据，源码、测试、冻结清单及公开样例保持该候选原字节。既有用户修改未纳入本包提交。

## 实际交付及验收结果

| 确认的行为 | 实际结果 |
| --- | --- |
| assemble_task／run_task 必要接线 | 读取并验证组件及逐行来源、根／场景／权限、候选及批次；history原值转H，b转base_scores，重核输入指纹。新增场景使用原请求模板与精确冻结快照。PUBLIC运行器须精确匹配安全输入和预算；终态复用，未闭合intent不重试 |
| A与B隔离 | 非PUBLIC的dev/test仅允许只读装配和configuration_required拒绝；即使注入fixture许可也不能运行。PUBLIC守卫保留；没有sender，model_adapter.py、token_counting.py及provider实现未改 |
| 实际A单份封存 | 每次PUBLIC运行以现有trace写法封存本次实际取得范围A，audit与task以acquired_ref定位，重复调度不重封。不从参考、未取得范围或重新取证补原文 |
| experiment_io | 只读转换真实形状的PUBLIC task／audit／publication／budget／request-response原件和封存A；核同次run、final／commit／seal结算、A／assessment／G／游标闭合及Q组件。缺原件、坏引用、矛盾产物均拒绝；未知usage按尝试回执保留null及已知小计，成功／失败／重试不漏计、不对Q重复计费 |
| 独立参考 | 使用手写PUBLIC原8／新增8／Q对应来源形状，核完整C四态、材料版本、批次、快照和BINDING。参考只在评价侧关联；生产转换不接收参考，不用于生成答案或补A。真实评价入口在A禁用 |
| 独立开发清单 | 1个dev账户、8任务、7个模型任务；成员证明与正式100账户交集0。只冻结，真实运行数0；未改正式100计划 |
| 少量执行的评价视图 | PUBLIC单项贯通score_task；完整18场景50槽中49槽not_started，summarize保持incomplete，C1估计null。没有补跑或把未执行槽填零 |

实现文件为 experiment_runner.py、recommendation_runner.py、experiment_io.py、tests/test_live_integration.py，原run_check.py仅增加本包守护分支；另有本包控制／归档脚本和独立pilot文件。未扩大上游审计或重构范围。

## 开发清单与公开样例

冻结目录：data/recommendation-runtime-audit/ticket14-development/pilot/，包括manifest、membership及五个组件。
pilot_id：6353afe1bf05e4eadd56216d64bb5d29181798e29c6edf9468f9d537e10c1af1。
父冻结plan_id：9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088。
D1：015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e。
8个任务键与已确认草案逐项相同：V00的R/S/M，以及V01、V05、V06、Q1、Q2的M。阶段顺序及停止条件沿用确认草案；本包没有执行许可。

PUBLIC定位见public-example.json及public-Q-example.json；最终分数为public-task-scores-final-v2.jsonl，汇总为public-summary-final-v2.json。evidence-index.json列出实际task、A、audit、publication、budget、模型请求／响应trace及测试stdout的字节／SHA定位。历史轮次的样例与分数保留，不能当作额外样本或真实结果。

## 验证与双轴审查

所有项目Python均经invoke-check.ps1显式使用项目Thesis Conda环境及现有Windows Job守护，无新依赖。最终新增26项测试通过（liveA_060，unittest 5.566秒）；另26项直接影响回归在033的DispatchBoundary 16项、034的RootBudget／批处理／评价器及PUBLIC CLI 10项中通过。其后新增的装配预算分支由新测试补齐；三轮审查修复仅涉及新增I/O及其PUBLIC证据，不改变旧回归的入口行为。这里保留各批实际验证结果，不声称同次运行了52项或全库回归。没有上游或旧T0验收重跑。

逐公共行为17组实际RED→GREEN；9项首次已经满足，如实记录。TDD路径及失败保留在tdd.md。Spec首轮3项、第二轮1项范围内P2已逐项复现修复并定向复验；未修非阻塞建议。

两轴最终均使用同一BASE...e34ef4a2候选，报告原文分别归档：

- **Standards**：硬违反0、阻塞性异味0；1项非阻塞Duplicated Code判断（视图引用映射），保持现状，见review-standards-e34ef4a.md。
- **Spec**：阻塞0、非阻塞0、范围扩张0，见review-spec-e34ef4a.md。

聚合见review.md。保护检查见verification-final.json：22份保护文件原字节未变，包括正式计划六文件、评价器核心／CLI所在模块、Adapter/count/provider、研究原件及既有接受记录；原离线账767278字节前缀不变，T0账全文件不变。冻结pilot七文件未变；9个源码／控制文件的原字节Git blob等于已审候选，且与最后受控运行记录一致。

## 资源结算与边界

按继承的命令时间资源账口径，本包 **287.770818秒／900秒**；原离线累计 **1077.487160秒／1800秒**。普通阶段未达到720秒，180秒收尾预留未被普通工作侵占。累计新增写入计账上界 **70,634,836字节（约67.36MiB）／256MiB**；含草案1MiB及本包源码／文档／Git／原生收尾32MiB上界，64MiB收尾预留仍保留。前包写入上界1,572,133,042字节继承，合计1,642,767,878字节，不作为新增授权。

时间包括guard 50.150243秒、launcher 107.251852秒、独立审查7.368723秒，以及123秒明确上界（草案30、原生及收尾60、前33次launcher取整补计33）。上界不是实测；最初launcher整数重载偏差通过只追加补计修正，未退款。55次受控启动中20次非零退出全部计账，包括实际RED、未成功的GREEN及归档防覆盖拒绝；原生Git换行检查失败也由既有60秒上界覆盖。完整结算见resource-closeout.json；原账只追加，T0账未动。

受控Thesis子进程树最大Job commit为55,943,168字节，加64MiB守护预留为 **123,052,032字节（约117.35MiB）／4GiB**。此数不冒充全机或原生PowerShell/Git的实测峰值；原生文件／Git操作由既有明确保守上界覆盖。

generate／count／other API均0；凭据读取0；真实推荐、评价、统计均0。没有采纳旧模型或价格默认值。模型、渠道、base_url、价格、API预算仍全部null，execution_authorized=false。

B阶段实现及付费试跑须另行明确上述五项配置、实际运行限额与执行确认；本包余额及原账余额均不构成下一阶段授权。下一阶段当前授权API和真实执行上限为0。
