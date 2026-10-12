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

## Fog

- D1—D12 的其余规则和参数继续待确认；依对应工单提供推荐、理由和用户明确结论。
- 工单 04 范围目录已生成，正在验收；正式用户任务或正式联合包尚未建立，不能宣称样本充分。历史“待确认”进度条目仅表示当时状态。

2026-10-12 更新：首轮审查 Standards 0 项、Spec 2 项；两项经 TDD 修复，版本升至 grain-A-1.0.3。完整来源重跑入选 14、排除 547,604、待裁决 55,656，32 项测试通过；490,461 个证据引用、目录摘要、机械候选去向及 26 份原材料均独立对账通过。工单 04 等待修复后的两轴复审。
