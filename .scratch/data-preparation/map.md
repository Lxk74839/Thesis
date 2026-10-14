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

## Fog


- D1—D12 的其余规则和参数继续待确认；依对应工单提供推荐、理由和用户明确结论。
- 工单 04、05 已验收关闭；工单 06 的清洗、时间截断和用户资格规则待确认。正式用户任务或正式联合包尚未建立，不能宣称样本充分。下列“待确认／等待审查”历史进度条目仅表示当时状态。

2026-10-12 更新：首轮审查 Standards 0 项、Spec 2 项；两项经 TDD 修复，版本升至 grain-A-1.0.3。完整来源重跑入选 14、排除 547,604、待裁决 55,656，32 项测试通过；490,461 个证据引用、目录摘要、机械候选去向及 26 份原材料均独立对账通过。工单 04 等待修复后的两轴复审。

2026-10-12 再更新：第二轮审查 Standards 0 项、Spec 3 项；逐项 TDD 修复并补同类标题否定回归，36 项通过。当前 grain-A-1.0.4 完整扫描入选 13、排除 547,052、待裁决 56,209；488,452 个证据引用和全部摘要对账通过，26 份原材料不变。1.0.0—1.0.3 均拒绝验收，仅当前版等待最后两轴复审；工单 05 依赖此验收。

2026-10-12 最新：第三轮审查 Standards 0 项、Spec 2 项；补齐所有文本字段的成分续行及未知后句，修正文档旧计数，37 项测试通过。当前 grain-A-1.0.5 完整扫描仍入选 13、排除 547,052、待裁决 56,209；488,474 个原文字段引用与全部摘要对账通过，26 份原材料及规格不变。旧版均 rejected_pre_release，等待当前修复版两轴复审后关闭 04。

2026-10-12：第四轮 Standards 0 项、Spec 1 项 P2；专用成分续行列表经公共入口 TDD 修复，全套 38 项通过。当前 grain-A-1.0.6 全量重跑及独立对账通过，入选 13、排除 547,052、待裁决 56,209；继续最终两轴复审，05 在 04 验收后推进。
