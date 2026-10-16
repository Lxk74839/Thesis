# 工单12公共行为TDD与初审修复

三个已获批测试缝隙：公共CLI、rank_quality、advance_action。没有新增生产测试入口；公开期望来自获批§8—9和四候选算例。原始每轮输出、失败和资源账保存于忽略的`data/quality-fusion-audit/20261016/`，不把失败擦掉或改写为通过。环境为既有Thesis，标准库；实验模型/API/付费0。

## RED/GREEN序列

| 范围 | 原始账标签 | 实际行为 |
| --- | --- | --- |
| CLI缺参 | red01 / green01 | 新stage及机器可读参数拒绝 |
| 独立准备 | red02、red02b / green02 | 首次缺新config属夹具准备失败，保留；red02b为真实缺stage实现的失败，随后最小实现 |
| 一致复用 | red03 / green03 | 原字节复用、冲突不覆盖 |
| 纯评分算例 | red04 / green04 | 公开B>A>HI>LO及精确分数 |
| 无q/均值 | red05、red06 / green05、green06 | 真实算法差异与固定均值分母 |
| 原件可采用 | red07 / green07 | 摘要、批次、权限、到期、v2、非空动作、事件路径拒绝 |
| 未取得/同属性 | red08、red09 / green08、green09 | 缺到货A=0/2；位置一致性、非法单位、冲突、运输/采样绑定 |
| 数值/输入 | red10 / green10b | 不完整C、无穷/NaN、非法权重、私有资格字段拒绝；green10首轮暴露校验顺序异常，保留 |
| 退化/并列 | red11 / green11b | D空、未知属性保留w、β零、α1和UTF-8并列；中间浮点中间量断言改用公开字面值容差，不改生产舍入规则 |
| 范围闭合 | red12 / green12 | 未读相关登记不能冒充完整；空C定义 |
| 动作初始/反馈 | red13、red14 / green13、green14 | 实际初稿→Issue→引用修订→复核→共同门禁 |
| 路由/初始依赖 | red15、red16 / green15、green16 | 实际不同取证槽位；初始登记、原件逐对象计量 |
| 根预算/门禁 | red17—red21 / green17—green21 | 失败/重试、最终预留、合法空、游标、状态/任务绑定、停止后门禁 |
| 时间/准备绑定 | red23—red25 / green23—green25 | 迟到与overrun、quality/normal配置分别绑定、独立错误审计 |
| 初审时间缺口 | red26 / green26 | 4个公开负例均先失败再拒绝：材料错阶段、签发早于事件、批次晚于首事件、观察早于到货 |
| 初审计量缺口 | red27、red27b / green27 | 先观测结算elapsed丢失及无retry_of绕限，再按实际失败对象推断重试并对齐结算用量 |
| 初审终止缺口 | red28 / green28 | 完整/固定均先复现单修订仍错的死路，再保留Issue走共同门禁blocked_evidence |
| 复审依赖闭合 | red29 / green29 | 未登记依赖先失败再拒绝；已登记但未取得事件保持Unassessed，不能由无关六阶段替代 |
| 对象类型边界 | red30、red30b / green30 | 批次额外kind字段不能冒充库存原件；schema与登记类型不匹配拒绝；两项真实错误均保留 |

existing22-pure为已存在纯计算/无I/O行为的追加观察，初次即通过；没有制造虚假RED。每个实际新行为以失败先于实现为准，保留必要中间失败。原参考与原诊断不改名、不成为新正式参考答案。

编辑自检还发现早期.gitattributes编辑曾误替换既有条目；已在提交前恢复全部原规则，最终相对基线只追加本次13行。该中间编辑未发布，没有改写旧文件；后续完整字节保护通过。

## 覆盖映射

| 验收 | 公共测试/独立证据 |
| --- | --- |
| QF01 | QualityCLITests三项；全量SHA八格分配、read guard与上游保护另核 |
| QF02 | verify_quality12_public的公开原件；verify_quality12_raw独立全量；export/compare分离 |
| QF03 | admissible、stock_same_attribute、unacquired_receipt、wrong_material_stage四类测试及负例 |
| QF04 | public_stock_quality、no_quality、mean_quality公开字面期望；完整C分数输入绑定 |
| QF05 | empty_unknown_preferences、rejects_mutated_binding、empty_C及UTF-8并列 |
| QF06 | pure_computation、unread_registered_stock、快照/摘要负例；文件I/O禁止观察 |
| AC01 | feedback_preserves_drafts、common_gate_no_feedback、unsuccessful_single_revision |
| AC02 | routing_executes_different_real_slots、cursor测试及公开A实际回执 |
| AC03 | failures_retries、retry_inferred、state_tampering及B根预算夹具 |
| AC04 | common_gate、stopgate、未修复的终止与实际F初稿/修订日志 |
| REL01 | 完整unittest发现原270项与新增公共测试，不重做07—11数据验收 |
| REL02 | 正式参考、空目录复现、无写入一致复用及460原文件保护；结果另见最终接受记录 |

## 两轴初审及集中处理

固定起点始终7bd12cd。两个独立代理仅审查，不运行项目计算。Standards初审阻塞0；`graph`命名一项建议保留为非阻塞，不为其扩大修改。Spec初审三类真实阻塞收齐后，按上述26—28组集中修复；首次定向复审又发现同类的缺失事件依赖旁路，按29补齐，并补30的对象类型负例。没有通过重新定义期望、删负例或降低合同消除阻塞。独立复审报告及最终实测另存，尚未完成之前不发布accepted。
