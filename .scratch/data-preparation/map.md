# 数据准备进度

## Notes

一个公共数据准备入口；仅在项目内生成产物，以 conda run -p 明确使用 Thesis 环境。原材料只读，原始数据、生成数据与私有标签不入 Git；来源清单、核查摘要与复现配置保留在版本管理目录。

## Decisions-so-far

- 工单 01 已完成：Python 3.13.16、标准库最小方案、18 个实际官方 main 包；环境调用通过，26 份原材料摘要一致，仅设置仓库本地 Git 身份。
- 初始基线：b59611e97b6eedf07c4e624884c48570fbfa2cdd。运行方案确认只解决 D12 对应子项。
- 工单 02 开始：完整 Grocery 商品元数据来源获取与字段核查，原始来源和诊断不等待商品筛选或实验参数。
- [工单 02](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/02-metadata-source.md) 已完成：603,274 条父商品元数据，324,346,561 字节；本地 SHA-256 和独立换行复核通过，11 个公共入口行为测试通过。Standards 与 Spec 审查发现均已关闭。[来源与字段核查](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-metadata.md)、[审查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review.md)。
- [工单 03](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/03-review-source.md) 已完成：14,318,520 条完整评论，1,630,860,152 字节，gzip EOF 与独立摘要／计数复核通过；全部按 parent_asin 关联 603,182 个父商品，92 个元数据父商品无评论。epoch 毫秒及 UTC 已交叉核实。1 条 0.0 评分原样保留，来源 needs_review；18 项公共入口测试通过，固定提交 5935f9b05829d49cef0919d48a0561f90a45f933 的 Standards / Spec 均 0 项发现。26 份原材料及规格摘要一致。[事实核查](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-reviews.md)、[审查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review-03.md)。
- [工单 04 范围审核草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/product-scope-proposal.md)待用户确认：全量 603,274 行机械诊断比较 A 5,372、B 6,538、C 5,888 个候选父商品；逐行计数与摘要复核通过。这些是条件诊断数量，尚未完成语义裁决，不是正式目录；D1 和 D3 元数据冲突子项尚未冻结，工单 04 保持 claimed。
- 2026-10-12：用户确认方案 A 及范围／冲突原则；规则 grain-A-1.0.2 全量扫描得到入选 10、排除 547,643、待裁决 55,621。30 项公共入口测试和独立源引用／摘要对账通过；工单 04 等待固定提交的 Standards／Spec 审查后验收关闭。[范围与产物](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grain-catalog.md)。

- 2026-10-12：[工单 04](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/04-product-scope.md)验收关闭；grain-A-1.0.6 全量 603,274 行，入选 13、排除 547,052、待裁决 56,209，38 项测试及独立对账通过，最终两轴均 0 项发现。实现提交 64bb0cb；目录摘要 e344b11fabf8296a93ea99050c70d2feda1f51a0ad8eb856c5feba0f0d13cc4b，26 份原材料及规格不变。以下历史进度保留追溯，当前推进工单 05。

- 2026-10-12：[工单 05](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/05-review-diagnostics.md)验收关闭；完整 14,318,520 行复扫，13 个商品提取 260 条原始评论、256 个来源账户；3 条完全重复副本原样保留，条件归并不减少账户。181 个文稿正向条件候选中 180 个无正向历史、1 个有一个历史商品，资格与充分性均未确定。48 项公共入口测试、独立全源字节／分组／损失／时间核对通过，固定实现提交 b3a0dfe 的 Standards 与 Spec 均 0 项发现；26 份原材料及规格不变。[诊断说明](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/selected-reviews.md)、[验收记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-extract-05-check.json)、[审查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review-05.md)。工单 06 的正式规则尚待用户确认。

- 当前更新（2026-10-14）：[04／05证据修订闭环](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/scope-revision-execution.md)已resolved。grain-A-1.1.15全源及独立验收通过：1,494商品、56,903原始评论、53,576来源账户；条件正向历史≥1／2／3为1,603／175／40，非正式样本。固定实现d1b24dc、149项测试、两轴复审及保护摘要通过，旧版和原稿保留。[06草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket06-rule-proposal-grain-A-1.1.15.md)待确认；06状态needs-info，未实施正式规则或联合实验，不因资格／充分性待决重开目录开发。以下历史进度保留追溯。

- 2026-10-14：[工单06](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/06-cleaning-eligibility.md)已resolved。用户明确确认D2—D4本轮政策及公共入口最小扩展；review-cleaning-1.0.0正式清洗56,427对象、有效文本56,363、资格账户1,603，所有1,494商品保留。164项回归、独立SQL、六类产物新目录字节复现及47保护文件／26原材料摘要通过。固定实现a76a75a、两轴0阻塞，各1P3已评估／附绑定格式勘误，未重开工程修订。[06验收](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket06-acceptance-review-cleaning-1.0.0.md)与records/cleaning接受清单保留实际依据。本轮停止于06，不进入07分组、模型输入或SIM，D10充分性待判定。

- 2026-10-14：[工单07](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/07-user-split-diagnostics.md)已resolved。第一阶段诊断及方案A／接口确认保存于13448a7，实现b6f79ea，独立证据cd984f7；user-split-1.0.0复用06合格1,603账号，开发320（旧16强制＋哈希补304）、测试1,283。独立SQL逐账号一致、交集0且完整覆盖，新目录稳定组件字节复现及资格／暴露／引用行序不变性、4,809条引用继承通过；178项回归通过，固定e2617ad起点的Standards／Spec首轮均0发现，阻塞修订0轮。70项保护来源不变；未知暴露保持未知，未宣称新盲测。D5本轮政策生效；只发布分组组件，不进入08、模型输入、SIM或D10结论。[正式验收与交付索引](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-acceptance-user-split-1.0.0.md)。

- 2026-10-15：[工单08](issues/08-preference-task-isolation.md)已resolved。用户C1—C9／输入schema／公共接口确认先保存于06cf2b6；实现480551b，首轮1.0.0因失败明细junction旁路拒绝保留，仅一轮集中修订f3adc26后验收preference-task-1.0.1。text_portrait_trial_v1／finite-text-1.0.0完整保留1494商品标题／粮种、1603根任务（320开发／1283测试）、1845合格较早正文及真实评分，历史标题关闭。197项回归、2393008候选统计全行SQL／文本追溯、26次API分派探测、真实开发目标私有副本变更不变性、6稳定组件新目录字节复现与707保护摘要通过。固定90ecec3双轴复审Standards 0阻塞／1P3、Spec 0发现，修订轮数1。D6仅本轮文本试制与A通道生效；未调用推荐模型、不进入SIM／互动训练／正式联合实验，D10待判定。[正式验收与交付索引](ticket08-acceptance-preference-task-1.0.1.md)。

2026-10-15当前更新：[工单09](issues/09-evidence-protocol.md)已作为规则确认类工单resolved，协议sim-evidence-protocol-1.0.0绑定原草案摘要，C1—C11总体方案/适用边界获用户确认；具体配置值尚未批准。下一项为[工单10实施前确认稿](ticket10-preimplementation-confirmation-20261015.md)，未启动正常SIM实现；工单11分配、12统计及后续模型/账本接入不在本轮推进。以下旧状态保留为历史。

- 2026-10-15工单10续办验收关闭：本次新授权集中修复S2整数类型，cf97cb1完整226项回归、固定755f277两轴无阻塞。正式sim-normal-1.0.0实际1494批/8964事件/11952材料/22410登记，独立R1 Supported=1494；六稳定组件/参考新空根字节复现、一致复用、982份保护通过，独立接受记录已归档，主记录字节不改。正常SIM组件通过；正式联合实验/样本充分性/模型/账本未完成，11/12未启动。[最终接受](ticket10-acceptance-sim-normal-1.0.0.md)。历史失败继续保留。

## Fog



- D1—D12 的其余规则和参数继续待确认；依对应工单提供推荐、理由和用户明确结论。
- 工单04／05／06／07／08已验收关闭；D2—D6仅用户明确确认子项生效，D6已完成偏好文本试制与A通道，其余正式实验规则继续待确认。偏好根任务已有试制产物，正式联合包未建立，D10充分性未判定；历史“待确认／等待审查”条目仅表示当时状态。本轮止于08，不自动推进其他工单。

2026-10-12 更新：首轮审查 Standards 0 项、Spec 2 项；两项经 TDD 修复，版本升至 grain-A-1.0.3。完整来源重跑入选 14、排除 547,604、待裁决 55,656，32 项测试通过；490,461 个证据引用、目录摘要、机械候选去向及 26 份原材料均独立对账通过。工单 04 等待修复后的两轴复审。

2026-10-12 再更新：第二轮审查 Standards 0 项、Spec 3 项；逐项 TDD 修复并补同类标题否定回归，36 项通过。当前 grain-A-1.0.4 完整扫描入选 13、排除 547,052、待裁决 56,209；488,452 个证据引用和全部摘要对账通过，26 份原材料不变。1.0.0—1.0.3 均拒绝验收，仅当前版等待最后两轴复审；工单 05 依赖此验收。

2026-10-12 最新：第三轮审查 Standards 0 项、Spec 2 项；补齐所有文本字段的成分续行及未知后句，修正文档旧计数，37 项测试通过。当前 grain-A-1.0.5 完整扫描仍入选 13、排除 547,052、待裁决 56,209；488,474 个原文字段引用与全部摘要对账通过，26 份原材料及规格不变。旧版均 rejected_pre_release，等待当前修复版两轴复审后关闭 04。

2026-10-12：第四轮 Standards 0 项、Spec 1 项 P2；专用成分续行列表经公共入口 TDD 修复，全套 38 项通过。当前 grain-A-1.0.6 全量重跑及独立对账通过，入选 13、排除 547,052、待裁决 56,209；继续最终两轴复审，05 在 04 验收后推进。

2026-10-15工单10当前更新：I1—I6确认并实施，候选2d3953b完整218项回归通过；唯一集中修订后Spec仍1项P2（快照policy.records布尔值漏检），Standards无阻塞/1P3。动态复现S2错误passed，失败证据已归档；按用户限额停止，10为needs-info未关闭，未发布真实1494正常包、正式参考或接受记录，正式联合实验仍未完成。见[ticket10未通过记录](ticket10-blocked-sim-normal-1.0.0.md)。
