# C01—C06离线适配子项验收归档

日期：2026-10-18。结论：**已确认的离线适配技术子项实现及验收完成**。仅接受下列离线行为；真实供应商可达、官方完整计数和真实容量均未验证。工单12保持未关闭。

## 授权、基线及提交

工作根为`C:\Users\Kane\Documents\CodexProject\Thesis`，沿用原任务及分支`codex/ticket12-offline-batch`。批处理验收`023a6cc5b906541f01b56cfd805594719bfac557`直接继承，没有重跑其30项收口、旧13公开组合或上游数据生成。

实施前归档提交`c5e2963`保存[本次人类确认](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/authorization-model-offline-20261018.md)及[集中确认文件原件](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/model-preconditions-confirmation-20261018.md)。后者SHA256=`9cfd918e4b0e3e6316e2e0a62e6a42c8518c38ed990751448b2cbb215fcee08e`，保持原字节及原历史状态；确认生效依据为独立人类授权。

| 提交 | 实际内容 |
| --- | --- |
| c5e2963 | 先归档确认及原提案，随后才改源码 |
| cd4a2e7 | 请求准备、原生格式、回执绑定、计数CLI及公开fixture集成 |
| c9483d8 | 关闭漏S/M根和错误usage/迟到保护问题，保留首轮审查 |
| 8a97c2f | 全入口规划门、HTTP失败原件/未知占用、错误分类费用边界，保留第二轮审查 |
| **8c5ed82423c9506aa29f8251405e194f47ab70a0** | 最终实现候选；补齐覆盖/失败摘要，保留第三轮审查 |

最终独立审查固定比较`023a6cc...8c5ed82`。本验收及最终审查报告在随后独立文档提交归档；最终候选之后生产、测试及诊断源码不再改变。

## 实际改动与公共合同

| 白名单文件 | 实现 |
| --- | --- |
| model_adapter.py | 纯本地prepare；0.3 native分支核对W/P、版本、项目、回执及既有根预留；原生调用/工具/输出/usage归一化；错误、漂移和晚到保原件并停 |
| provider_openai.py（新增） | 既定`gpt-5.4-mini-2026-03-17`单一Responses映射，完整消息/工具历史和六角色封闭schema；单次HTTP计数边界；生成仅注入sender |
| token_counting.py（新增） | InputCounter离线回执/fixture与显式许可入口；export/count/import公共CLI；全入口目录门、去重及每个原请求引用、来源、失败和覆盖账 |
| recommendation_runner.py | 仅新增openai_native_fixture公开数据分支：prepare→离线count→同一RootBudget预留→invoke；保final及共同重试；live仍不开放 |
| tests/test_provider_openai.py、tests/test_token_counting.py、tests/provider_fixtures.py（新增） | 只从prepare/invoke/count/run/CLI观察公开行为；原生发送、HTTP、时间和字面计数为外部替身 |
| 本目录diagnostics、verification及独立记录 | 原守护仅增加新源码指纹；新增交付原件/保护检查、逐行为TDD与审查记录 |

零新增第三方依赖；没有安装tiktoken/SDK，没有改环境锁。全部项目Python经既有Thesis Conda和原Windows Job守护执行，守护核对Python3.13.16。evidence_access.py/RootBudget、joint及评分/融合/业务核验模块、账户/C/H/S/质量主点、原测试/fixture和预算配置均未改。六角色职责及完整候选/信息访问范围沿用接受设计。

prepare冻结完整原生请求W与计数载荷P（含相同模型、消息、工具、输出结构和相关设置），以规范字节、摘要、mapper/schema版本、项目及prepared_id绑定回执。内容或设置变化不能直接复用旧绑定。没有以字节或本地文本整数作为官方完整token计数。

计数CLI只消费显式prepared JSONL和计划，不新增/运行T0枚举器。每个声明S/M根必须有请求；R可为0；逐根17槽/U≤108800在导出、导入和直接count共用入口检查。每个原请求保留引用，重复W可共用一次回执但逐根累计不去掉原调用。缺项保持整根累计null，摘要列roots/references/unique/valid_receipts/missing_count/failed_attempts/unresolved_attempts及原missing表。

缺许可、费用证据或完整目录时计数发送前拒绝。当前108800次/24小时只是未启用的规划封顶；真实执行另需独立批准的执行记录、项目、官方费用/失败规则、金额与调用/时间上限和显式凭据路径。fixture发送器或替代HTTPS取得的回执始终是fixture，重贴标签不能变成官方来源。

HTTP固定origin/POST，无重定向或自动重试；失败保留已取得的状态、头、有界正文/读错误，超限最多读1MiB+1字节以留越界证据。未知结果继续占用并停止重开后的发送。实际供应商计数、生成和其他API调用均**0**，未探测凭据；真实HTTP生成函数未实现。

## 实际测试及原件

[逐行为TDD记录](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/verification/tdd-model-offline.md)保留40个实际产品RED→最小GREEN行为。首次已满足检查及测试编写错误另记，没有制造RED；所有失败留在同一累计账。

| 实际检查label | 结果与用途 |
| --- | --- |
| 110-native-and-impact | 39/39（当时34新增+5必要旧回归）；历史首次收口 |
| 117-native-and-review-fixes | 41/41（当时36新增+同5旧回归）；4.305秒。旧回归仅未绑定provider、两项消息/工具身份及画像接地/共同重试 |
| 119-late-drift-green | 新迟到交叉及2项直接回归，3/3，0.102秒 |
| **128-native-counter-final** | **40/40新增测试**，4.679秒；计数全入口及HTTP失败修复后收口，没有重跑旧库 |
| **130-error-binding-green** | **6/6**，0.141秒；新增1项异常费用边界与5项直接影响行为 |
| **134-coverage-summary-green** | **4/4**，0.940秒；新增1项覆盖摘要及3项直接CLI回归 |

合计**42个不同新增测试与5个必要旧回归分批通过**；不是一次47项运行。128之后仅改错误分类和CLI聚合数字，分别由130、134定向复验；未再重跑已通过部分。原始输出保存在同一审计根的对应label.txt，源码指纹随每次检查留账。

公开运行器轨迹观察到：M必要臂六角色完成、9次fixture模型调用；S/M质量分支保留同历史、完整公开C及M组件；缺计数发送前停在0模型槽；格式/截断的I=99相对回执100发生冲突时仅发送1次，原99留在响应，根I/O/费用预留保持unresolved且final不动。100输入/40缓存/30输出/20推理的字面fixture归一化为100/30、183微美元，推理不重复叠加。以上只验证会计和映射行为。

独立原件检查131通过：对应128留存**6份公开运行审计、158个文件、10,857,936字节**，含负向测试原件；13条fixture intent记录、5条替代HTTPS记录，实际供应商请求0。该检查固定于8a97c2f；后续仅摘要字段改动由134核对，不把旧原件重标为新执行。

原件索引：[model-delivery-128-native-counter-final.json](/C:/Users/Kane/Documents/CodexProject/Thesis/data/recommendation-runtime-audit/20261018-batch/model-delivery-128-native-counter-final.json)，SHA256=`0342e6e52570fa280cf362f509cb6df26d1fe187e85f40cd1172e0af7cbf1699`。每个文件均有字节数/SHA；负向原件不被当成有效官方回执。最终135保护检查通过，原1192个受保护文件变化0，包括论文、研究、历史接受和reports的摘要核对；未读取正式推荐表现。

## 独立双轴审查

按mattpocock-skills:code-review分别由独立Standards/Spec代理审查；两个轴不互读、不运行测试/API。首轮和复审原件保留；Spec发现的四个阻塞及最后覆盖摘要P2均经逐行为TDD修复。

| 最终候选8c5ed82 | 阻塞 | 非阻塞 | 本轴最高严重性 |
| --- | --- | --- | --- |
| Standards | 0 | 0 | 无 |
| Spec | 0 | 0 | 无 |

分轴原文与结论见[双轴汇总](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/verification/model-review-8c5ed82.md)。仅接受离线技术子项；旧批处理结论直接继承。

## 累计资源与只读门

沿用唯一账：[resource-ledger.jsonl](/C:/Users/Kane/Documents/CodexProject/Thesis/data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl)。旧40次/70.26800119999098秒继续累计，未清零、换账或借T0额度。下列为135检查完成后的冻结读数；随后仅静态审查、Markdown和Git归档。

| 项目 | 读数 |
| --- | --- |
| 全账命令/非零退出 | 135 / 59 |
| 本子项新增命令/非零退出 | 95 / 42（含RED、未通过GREEN尝试及测试编写错误） |
| 本子项增量 | 44.559039999963716秒 |
| 累计/1800秒 | **114.82704119995469秒** |
| 剩余 | **1685.1729588000453秒** |
| 全账进程树峰值+64MiB守护预留 | 422,125,568字节，低于4GiB |
| 本子项进程树峰值+守护预留 | 118,267,904字节 |
| 检查中源码变化/未结inflight | 0 / 无 |
| 受保护文件 | 1192，变化0 |

账SHA256=`15918e4b1c5dfc410d83938d5a05268493efdaf8c79687e9225387af71f5f904`；[最终保护报告](/C:/Users/Kane/Documents/CodexProject/Thesis/data/recommendation-runtime-audit/20261018-batch/model-protected-after-accepted-candidate.json)SHA256=`b08b201a02f620a271b713220c455ade4aee6241b61ea294e702c91aec842e70`。所有失败、诊断及受管子进程均累计。reports及data原件不纳入Git提交。

## 剩余门槛与终点

官方账户能否使用既定快照计数、联合字段/strict schema（包括保留的uniqueItems）实际接受、计数成功/失败费率及金额上限、全开发目录的真实U/上传量/耗时、每条完整官方回执和真实容量，仍未知或未执行。fixture计数及公开小样本不能证明这些事项。

后续外部计数仍需独立执行/费用授权及前置证据；缺一项即发送0。T0 A离线准备、C外部计数、B容量回放及P1均未执行；原T0规模和联合资源门保持确认合同所列，不在本轮生成9600目录或做容量统计。自然生成的新W、动态计数及final新增依赖仍需将来各自闭合时间/费用/调用门。

本轮未批准正式模型费用，未冻结可执行预算，未沿用USD600作批准额；不宣称G1/G2整体通过或真实供应商可达，不部署链、不冻结工单15、不关闭工单12。本轮终点为上述离线适配子项验收归档。
