# 工单12：质量融合与确定性动作模块离线接受报告

日期2026-10-16；固定审查基线`7bd12cdb36b073f65ce9f123939e01288b8a12c0`；实现源提交`f7e55066c8a804890a6b91f0368e74ffd3756c01`。

**两个获批离线模块已通过全部门禁并写独立接受记录；整个工单12保持打开。** D1—D3、D6延续既有授权，不重复确认。K1—K8整体、P1、付费模型、USD600预算、真实六角色运行、账本部署及13联合包未获本次接受。样本充分性仍待判定。

论文题目“一种基于区块链与多智能体技术的农产品可信推荐方法”、双模块和六角色保持。论文、研究材料、07—11接受链、原S及账户分组只读。原诊断没有改名充当正式材料或答案。

## 1 实际交付

| 产物 | 实际入口或位置 |
| --- | --- |
| 公共准备 | [prepare_data.py](C:/Users/Kane/Documents/CodexProject/Thesis/prepare_data.py)：新增quality_fusion阶段，沿用sim-record/output-root，仅新增quality-config参数 |
| 纯评分 | [quality_fusion.py](C:/Users/Kane/Documents/CodexProject/Thesis/quality_fusion.py)：rank_quality(binding, acquired)，无宿主I/O或额外补证 |
| 动作状态 | [recommendation_actions.py](C:/Users/Kane/Documents/CodexProject/Thesis/recommendation_actions.py)：advance_action(state, event)，仅公开确定性适配器 |
| 独立配置 | [quality-fusion-0.1.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/config/quality-fusion-0.1.0.json)，只绑定获批质量臂 |
| prepared主记录 | [generation记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json)，状态保留prepared_pending_independent_acceptance，未回写 |
| 独立接受 | [acceptance记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0-acceptance.json)，仅质量材料/评分与确定性动作合同 |
| 正式材料 | `data/sim-quality/grain-A-1.1.15/sim-quality-fusion-0.1.0/`，两个独立封存视图 |
| 私有审计/失败 | `data/quality-fusion-audit/20261016/`及`data/sim-quality/failures/`，均被/data规则忽略，不纳入Git |
| 字段/边界 | [实际接口说明](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-offline-interfaces-20261016.md)；[TDD及编号映射](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-tdd-and-review-fixes.md) |

版本为quality-preference-protocol-0.1.0、sim-quality-fusion-0.1.0、quality-reference-0.1.0、fusion-score-0.1.0及collaboration-action-contract-0.1.0。它们的模块接受不等于正式质量实验统计设计冻结。

授权和旧研究依据最先归档于提交51d8bc0，见[授权](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-quality-offline-authorization-20261016.md)和[索引](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-quality-research-archive-20261016.json)。原诊断、原件和失败证据原地保留。

## 2 正式材料与独立结果

生成、空目录复现及一致复用均实际启用读取白名单并禁止网络/子进程，各15个项目读取路径，拒绝0。读取范围为获批正常材料/接受/配置、生产源、原报告及授权；没有读取用户、历史、目标、b、08任务或模型输出。原件参考从实际字节、登记、事件、权限和时间重推，先持久化答案，再检查分配；不导入生产评分/最终状态、不读分配答案或旧诊断答案。

SHA-256域/NUL/种子/NUL/父ID与UTF-8并列排序严格沿用用户规则。Q1八格依次187、187、187、187、187、187、186、186；Q2仅交换T档，库存不变。每视图1,494批次、8,964事件、11,952原件、22,410登记，动作明确封存为空。只有零售库存、有效期及对应登记摘要改变；其他原件、事件和权限字节与原正常基准一致。

每视图库存25/50/75/100各374/374/374/372对象；主点q=.6/.9各747对象。C=1/1、A=2/2恒定，公式与来源已核对，**独立贡献尚未验证**；质量异质性来自T。

| 实际核查 | 数量与结果 |
| --- | --- |
| 独立原件参考 | 2,988条，通过 |
| 五种原件/登记/事件/摘要来源引用 | 14,940条，可定位 |
| 生产接口观察 | 无账户合成目录b，共28次：18完整网格、6无q、2均值、2边界 |
| 候选行 | 41,832行，资格、x/z、C/T/A、q/m、分母及稳定次序核对 |
| 数值比较 | 250,992项，容差1e-12，错误0 |
| 评分同属性引用 | 41,832项，错误0 |
| 无q跨视图 | 三个α配对条件分数/次序均一致 |

没有重复P0或320账户/8,320次开发诊断。此次合成b没有真实用户、目标或理想效用标签，以上不是正式测试推荐表现或模型收益。

## 3 公共行为与真实夹具轨迹

最终完整回归**295项通过＝原270＋新增25（质量16、动作9）**，覆盖获批三个公共接口及QF01—06、AC01—04；全量、复现、复用、保护覆盖REL02。公开期望来自获批合同及人工算例，RED与中间失败完整保留；不把subTest、参数、视图或引用当独立用户。

四候选完整质量为B>A>HI>LO，A分.675/B分.75；无q为A>B>HI>LO；均值q=.675，A分.703125。缺到货A=0/2；未取得原文/事件保持Unassessed；库存冲突保留Conflict。非法单位、权限、摘要、时点、登记/事件依赖、schema/对象类型等拒绝；α1、D空、未知维度不重分配w、β零、稳定并列和无I/O均有检查。

公开适配器实际执行F/A/B×完整/无反馈/固定共9套，保存39状态、30转换；独立核对270预算分量格通过：

- F保留错引初稿、实际Issue、引用old/new、父子草案和复核。无反馈不向管理者传Issue，也不能借门禁修订；一次修订仍错时最终记blocked_evidence。
- A在同原件并集和只余一读取单位下，完整/无反馈实际取得零售，固定路由实际取得采样，返回字节与取得集合可区分。
- B拒绝动用最终预留的修订；失败原件换ID重读且略去retry_of仍计重试，结算elapsed不丢失，各角色共用根预算。初始依赖不免费，四对象完整夹具为123逻辑单位/7适配器物理请求。

全部轨迹标明public_deterministic_adapter，不是自然错误率、真实模型修订成功率或六角色消息。物理请求不等于磁盘read次数。模块只接受最小正常v1质量臂；非空撤销/替代、v2及不支持状态明确失败关闭，未声称接入16异常生产核验。正常世界未完成的空输出不记合法空；公开valid_empty核对采用完整C为空的夹具。

## Standards

独立代理按固定7bd12cd审查；初审及所有定向增量审查均通过，**硬阻塞0**。一项非阻塞建议：graph同时表示路径和范围闭合，已记录，不扩大修改。[初审](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-standards-initial.md)、[最终报告](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-standards-final-review.md)。

## Spec

初审三类阻塞为时间/阶段关联、重试/结算计量、单次修订仍错后的终止死路。收齐后逐公共反例RED→GREEN集中修复；复审发现同类缺失事件依赖旁路，继续补未登记拒绝/已登记未读Unassessed及对象类型边界。最终代码和接受写入增量审查**阻塞0**。[初审](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-spec-initial.md)、[第一复审](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-spec-rereview.md)、[最终报告](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket12-spec-final-review.md)。

两轴分别结论：Standards 0阻塞/1非阻塞建议；Spec原三类及余项清零。代理只读静态审查，未运行项目计算，不以一轴替代另一轴。

## 4 复现、保护与接受证据

新空目录重生与正式16组件及prepared共**17文件、56,368,236字节**完全相同；同根一致复用的字节及mtime不变。prepared SHA-256始终为`215ce92c86b55b7b87a6e5677a161b8d9623c39000966651c9b91d13336197bc`。

上游前后完整核对460文件、22,471,368,289字节，改变0；覆盖既有数据、原S/分组、正常/异常材料、接受记录、论文和研究材料。sim_normal.py、sim_scenarios.py代码差异为空。绑定源/配置/原报告/授权的Git blob与工作字节一致；私有数据/审计未被跟踪。

所有门禁真实通过、接受写入脚本再次经两轴审查后才用xb创建独立接受记录。其12,284字节，SHA-256=`fd3a17e94336410f6a971ce6866a8d835ae821035fcfbd8c2f6723bd8968ed8d`；prepared未回写。初审、首次复审、RED、失败及旧夹具轨迹均保留，新审计用独立目录。

## 5 实际资源与成本

| 项目Python子进程树累计计时 | 秒 |
| --- | --- |
| TDD/公共行为，含预期RED | 133.339 |
| 四轮必要完整回归及修复证据 | 680.070 |
| 正式Q1/Q2准备 | 5.600 |
| 独立参考、接口观察及夹具审计 | 37.313 |
| 新空目录复现/同根复用 | 11.131 |
| 上游前后保护 | 40.495 |
| 范围接受写入 | .358 |
| 合计 | **908.307秒，约15.14分钟** |

峰值子进程树提交量348,798,976字节，即332.64MiB；Windows Job实际限制4GiB，累计计算30分钟守卫。使用既有Thesis Conda/Python 3.13.16及标准库。计时不含Conda启动、文档编辑、审查代理及收尾静态Git/文件核对。每轮原始账在忽略审计侧，包含失败，不只统计成功。

实验模型/API/外部付费调用0，推断输入/输出token0，费用USD0；不由字节假估token。代码审查代理只作静态审查，USD600没有执行。

## 6 供一次确认的剩余最小决策

下列均为**推荐，尚未冻结或授权运行**；不替代K1—K8整体，不重复D1—D3/D6：

| 决策 | 推荐 | 依据与取舍 |
| --- | --- | --- |
| 质量臂进入正式比较 | 保留原8视图必要约束比较；另加Q1/Q2受控库存偏好臂，主点α=.5、β=(.25,.5,.25)，R/S/M同H/请求/完整C/b/证据/根上限。full/no-q/mean优先在同方法同AcquiredScope/G内配对重排，0额外付费调用，α1保留边界 | 识别评分融合贡献，不能冒充质量改变后重新调度的全方法消融。库存诉求来源是实验设计；指标与NA由独立评价侧固定，不用融合公式理想排序证明真实效用 |
| 统计family/精度 | 推荐预先列四项：M−S、M−R、质量full−no-q、full−mean；先账户内汇总各自场景/重复。为覆盖融合主张，建议四比较同时95%、条件近似半宽±.08 | Var(配对差)≤1，n=ceil[(z(1−.05/(2m))/h)^2]：m2/h.07需1026，m4/h.07需1274，m4/h.08需975。旧8视图n_J=1111不自动成为新family有效人数。坚持±.07应保留1274目标并讨论扩样/实际更宽区间，不隐藏缺口；相关性和覆盖限制不撤销 |
| 模型/根预算 | 不执行USD600。保留原稿12调用、96k/12k token、2重试、64候选、600秒作为待验证共同上限；拆逻辑/物理，建议后续开发验证以逻辑2048/物理256起算，保留发布额度；未来授权前核验模型/官方价格和实际载荷 | 当前64完整胶囊=1923逻辑；完整R1/R5/库存C/T/A所需12原件＋15登记/对象也为1731，均未含程序步骤。1923再加64 assess及5草案/反馈/最终步骤约1992，2048只余56，**未证明真实接口可行**。旧256不能声称免费覆盖64对象，六角色不能各一份额度；超载先改合同确认，不临场扩额或换S/账户 |

精度是研究设计选项，不是预期提升/优效阈值，未用正式测试表现反推。1,283仅为账户池，最终适用集合、历史/目标集中度/类别覆盖及相关性敏感性继续按D6条件近似路线判定；不能将共享商品/材料、150对象、场景或引用作为独立用户，不提前宣布充分性通过。

真实推荐、自然反馈和协作调度增量仍需未来授权的共同工具适配器/运行与独立评价。C/A独立贡献需另立控制及版本；不默认删论文核心主张，也不伪造本轮结果。

区块链未部署；后续须验证身份/签名及原件完整性、版本/撤销/权限与审计闭合、写入/确认/查询延迟与失败重试、gas/节点/RPC/存储成本。本地SIM登记和SHA核对不等于已部署链。

本次停在上述三项集中决策点；整个工单12保持打开，不启动P1、真实模型/六角色、账本部署或13联合包。
