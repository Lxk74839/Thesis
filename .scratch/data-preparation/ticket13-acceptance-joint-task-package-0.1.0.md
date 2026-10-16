# 工单13：联合数据准备子范围接受

2026-10-16（Asia/Shanghai）。合同C13-01—C13-10、S1/S2及A01—A12的本次实施和真实门禁已通过。接受状态为`accepted_joint_preparation_component_only`；整体样本充分性仍为`not_determined`，正式联合版本为`not_released`。工单13仅本次联合准备子范围resolved。

批准合同原字节SHA-256保持`d279bbeda1e406569e2c186e23988a3402a8946cab3ba8dee2a716ad76056221`。[授权归档](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket13-implementation-authorization-20261016.md)先于配置和实现提交。未重新讨论F1—F3或全面重审已接受模块。

## 实际产物

| 入口/产物 | 实际结果 |
| --- | --- |
| [prepared主记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json) | 1,603根、1,494父商品及唯一SIM批次、16,030计划视图绑定；生成后未回写 |
| [独立接受记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0-acceptance.json) | 独占新建，绑定prepared、全部组件、S2、复现/保护、最终审查与资源快照 |
| [联合总清单](C:/Users/Kane/Documents/CodexProject/Thesis/data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0/package-manifest.json) | 完整来源图；56,903原始匹配评论、56,427清洗对象及既有去重/来源审计；原料及SIM事实只读引用 |
| [独立S2 check](C:/Users/Kane/Documents/CodexProject/Thesis/data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/check.json) | `passed_joint_association_only`；全根、完整C、分数、投影、探针、独立引用通过 |
| [覆盖汇总](C:/Users/Kane/Documents/CodexProject/Thesis/data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/coverage.json) | 开发/测试各自pool及UQ，包含历史、目标聚类、类别/UTC年份0格及暴露状态 |
| [冻结交付证据](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket13-delivery-evidence.json) | 含接受进程的完整资源账、62轮日志、程序及各接受证据的精确字节摘要 |
| [TDD与公共行为映射](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket13-tdd-and-acceptance-map.md) | 31项测试、24轮实际RED→最小GREEN、失败历史及A05定向补证 |

稳定包11文件共745,961,763字节（约0.695GiB）：candidate-map、roots、base-scores、view-bindings、package-manifest；model下catalog/roots/candidates/manifest；private下session-map/access-probe。这是引用上游的本地逻辑包，不是独立可搬运归档。

独立参考5个稳定文件共14,328,366字节：preference-reference 1,603行、sim-reference-index 14,940行、q-applicability 3,206行、uq-mask 1,603行及coverage，另有check。逐根目标、会话与参考留在忽略的data目录，不入Git。引用/视图/候选行数不充当独立样本数。

prepared SHA-256：`2226fb160a0e25cdf4c1ecf3b7bf213197de144bbd97286311b0bf0f58f9eb58`；接受记录SHA-256：`9937ff98a530b0b51cb072fc9d055da9bc11f006dcca8ac4296500bed3200976`。接受后prepared仍保持原状态和原字节。

## 实际验收映射

唯一准备入口仍为prepare_data的joint_tasks阶段；独立S2仅接record/audit-root，不导入生产计算。[公共接口说明](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/joint-tasks.md)保存完整命令、字段和边界。

| A项 | 结果与证据 |
| --- | --- |
| A01 全部原料 | 通过。56,903源评论/56,427清洗对象的引用及去向绑定、行数对账；没有重新提取或计算清洗语义 |
| A02 同根配对 | 通过。继承08根/H/S/T/分组；1,494唯一批次、2,393,008完整候选关联、16,030视图绑定。R/S/M是计划方法及共同绑定，未冒称已经运行 |
| A03 正式基础分 | 通过。char3-tfidf-history-1.0.0每根全C计算一次，S2独立复算容差1e-12；人工(1,0)、同分/单候选0.5通过，P0未重算 |
| A04 安全投影/分页 | 通过。model manifest只列三安全数据文件；全根完整C对账及1,603实际首分页核对；公开35候选按返回游标32+3闭合。未声称真实全C均逐页调用 |
| A05 私有变更 | 通过。公开夹具替换合法私有目标/评分/正文，model/b及完整probe摘要不变；前后S2成功，只有指定根偏好参考目标改变 |
| A06 隔离拒绝 | 通过。16,030份实际序列化请求+1,603首分页+8,015拒绝=25,648探针；逐根全视图及五类拒绝集合齐全。tools=[]、模型API调用0；不是OS ACL或真实工具接受 |
| A07 独立来源 | 通过。偏好从08私有评价源关联；证据从11/12独立已接受参考关联，同父商品/批次/快照/profile及原件摘要逐引用核查。四态语义接受直接引用，不用生产状态生成gold |
| A08 新Q/旧P0 | 通过。新Q关联3,206行；实测测试nQ=1,283、开发320；原8 n8=1,111直接引用P0。公开nQ=3/n8=2/HHI=5/9通过 |
| A09 NA/错误 | 通过。缺键、篡改、范围外v2等失败而非NA；正常v1、空actions及normal批次/事件/policy精确摘要守卫有效。真实Q1/Q2开发/测试NA各0，原8不适用保留P0依据 |
| A10 引用/覆盖 | 通过。14,940参考引用齐全；类别/年份0格、历史、目标集中度、暴露unknown完整；按来源账户计数，不按视图重复计数或按共享目标去重 |
| A11 发布门 | 通过。批准摘要与31输入绑定，严格类型及全部祖先reparse/暂存路径守卫；半发布/损坏/不一致拒绝。预算仍null、执行授权false、候选限额pending |
| A12 复现/保护 | 通过。新空根11组件及5参考逐字节相同；一致复用保持prepared及组件mtime；1,556保护文件无变更，原.gitattributes字节前缀不变 |

新空根保留于`.tmp/ticket13-reproduction-1e1bc3f`，参考复现为同版本`reproduction-reference-0.1.0`。易变主记录的输出根、时间与Git状态不作为稳定数据比较；复现/复用证据由接受记录及冻结清单绑定。

## 实测人数与覆盖

| 指标 | 开发Q适用集合 | 测试UQ |
| --- | --- | --- |
| 来源账户/适用数 | 320/320 | 1,283/1,283 |
| Q1/Q2不适用 | 各0 | 各0 |
| 历史父商品深度1 / 2 / 3+ | 277 / 30 / 13 | 1,151 / 105 / 27 |
| 历史父商品覆盖 | 169 | 388 |
| 历史事件均值 / 中位数 / p90 / p95 / 最大 | 1.215625 / 1 / 2 / 2 / 6 | 1.134840 / 1 / 2 / 2 / 5 |
| 不同目标父商品 | 132 | 320 |
| Top1 / Top5 / Top10 / Top20人数 | 27 / 106 / 140 / 175 | 94 / 394 / 522 / 661 |
| 目标HHI | 0.0284961 | 0.0240297 |
| 旧语料暴露账户 | 43 | 70 |
| 已知智能体结果暴露 / 未知 | 2 / 318 | 0 / 1,283 |
| 已知人工结果暴露 / 未知 | 0 / 320 | 0 / 1,283 |

测试UQ有89.71%仅一个历史父商品；Top5占30.71%、Top10占40.69%。粮种目标为corn 681、rice 351、oats 174、wheat 48、millet 23、barley 3、teff 3，其余10类为0；corn+rice占80.44%，再加oats为94.00%。完整0格、聚类大小直方图、历史正文分布见coverage。

测试目标UTC时间为2011-06-20T20:00:05Z至2023-07-23T16:46:07.454Z；2011—2023年度人数依次为1、4、21、52、70、63、77、73、119、240、260、225、78。历史评论与2026固定SIM时点分开披露，不构成历史真实供应链验证。

975规划人数门对nQ及引用n8均met，只代表人数条件。来源账户未证明是独立自然人；共享商品/材料、稀疏历史、类别/时间集中和未知暴露保留。未产生实际效果区间，不能宣布整体样本充分性、精度或新盲测通过。

## Standards

固定base为`cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1`，最终candidate为`27a03a59e72991faddbc88b5828b8516dcd6b760`。初审1项路径阻塞经公开RED/GREEN关闭，真实形状及验收断言修订再作独立定向复核。最终硬阻塞0、非阻塞建议0。[最终Standards报告](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket13-standards-acceptance-final.md)。

## Spec

同一固定base/candidate。初审2项阻塞（正常v1范围、实际probe覆盖）经公开RED/GREEN集中关闭；11主体继承和A05补证再作定向复核。最终阻塞0、非阻塞0，未扩到工具/运行器/统计或重议F1—F3。[最终Spec报告](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket13-spec-acceptance-final.md)。

两轴由独立代理并行完成，历史报告分别保留；[审查摘要](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket13-review-summary.json)绑定精确字节。Standards最终0项、最严重问题无；Spec最终0项、最严重问题无。静态审查不替代真实接受。

## 资源与保护

项目Python统一Thesis Conda/Python 3.13.16、标准库，经Windows Job顺序执行。62轮累计657.348263秒（10分57.35秒），含测试、失败、真实生成/S2、复现/复用、保护及接受进程；未触及1,800秒上限，未扩额。峰值子进程树提交内存454,582,272字节（433.523MiB），加64MiB守卫预留为497.523MiB，低于4GiB。内存指标为Windows Job峰值提交内存。

28次非零退出全部保留并入账：24个预期RED、1个早期GREEN夹具元数据失败、1次真实生成字段接入失败及2次定位尝试。真实失败因误要求11快照包含Q顶层主体；第24轮公开反例修正为从精确绑定policy继承，未改上游。定位器第一次runpy路径错误及后续定位到原生成错误均未从资源账排除。

31项测试全套通过，随后仅增强既有A05并定向通过，生产字节不变。原295项、SIM生成、旧P0计算及上游已接受全量语义核查本轮运行0次；必要影响回归仅四个旧阶段缺参数分派。引用完整性核查不等于重算旧语义。

保护覆盖1,556份既有上游/论文/研究及基线文件，共22,571,699,120字节，前后改动0，原.gitattributes前缀不变。论文、原S、账户划分及已接受上游未写入。接受记录绑定接受前快照；冻结清单补全包含接受进程的完整62轮账，避免自引用摘要。冻结后未再运行项目Python。冻结清单SHA-256为`385e4bb220cb9034084aa5c4eee527bba18067611288d8f6ba84a92ca4b72631`。

## 提交与剩余依赖

授权`fb315b2`；初实现`ee5bb27`；集中修正`7de5d37`；真实形状修正/最终生产源码`1f3f6bc`；实际生成运行`1e1bc3f`；A05补证/最终审查候选`27a03a5`；最终审查归档`1a59dae`。实际生产和S2源码与最终候选逐字节一致；最后交付提交只增加接受/汇总元数据和工单索引，不改实现或配置。

后续依赖保持：

- 真实受限取证Adapter：证据列取/读取、宿主身份/快照/候选绑定、实际授权与成本计量；内存数据会话不能替代。
- 原8所需异常生产核验：缺件、否定、冲突、过期、合法版本、权限/撤销；不得用独立gold代替。
- 推荐运行器、模型与六角色Adapter：真实R/S/M、M组件共用实际A/G/终态、反馈和失败结算，均未实现或运行。
- 工单12预算验证与执行冻结：模型/提示/工具版本、T0/P1等依专项授权；当前预算pending/null、执行授权false。
- 14/15整体充分性、适用门禁与正式封存，以及后续效果统计/区间、真实账本；本次不宣布完成。

未启动T0/P1、付费模型或区块链部署，模型API调用0。没有合同外实质阻断需扩范围处理；既定后续依赖不被数据子范围接受抹掉。
