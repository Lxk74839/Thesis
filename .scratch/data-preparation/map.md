# 数据准备进度

## Notes

一个公共数据准备入口；仅在项目内生成产物，以 conda run -p 明确使用 Thesis 环境。原材料只读，原始数据、生成数据与私有标签不入 Git；来源清单、核查摘要与复现配置保留在版本管理目录。

## Decisions-so-far

- 工单 01 已完成：Python 3.13.16、标准库最小方案、18 个实际官方 main 包；环境调用通过，26 份原材料摘要一致，仅设置仓库本地 Git 身份。
- 初始基线：b59611e97b6eedf07c4e624884c48570fbfa2cdd。运行方案确认只解决 D12 对应子项。
- 工单 02 开始：完整 Grocery 商品元数据来源获取与字段核查，原始来源和诊断不等待商品筛选或实验参数。
- [工单 02](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/02-metadata-source.md) 已完成：603,274 条父商品元数据，324,346,561 字节；本地 SHA-256 和独立换行复核通过，11 个公共入口行为测试通过。Standards 与 Spec 审查发现均已关闭。[来源与字段核查](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-metadata.md)、[审查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review.md)。
- [工单 03](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/03-review-source.md) 已完成：14,318,520 条完整评论，1,630,860,152 字节，gzip EOF 与独立摘要／计数复核通过；全部按 parent_asin 关联 603,182 个父商品，92 个元数据父商品无评论。epoch 毫秒及 UTC 已交叉核实。1 条 0.0 评分原样保留，来源 needs_review；18 项公共入口测试通过，固定提交 5935f9b05829d49cef0919d48a0561f90a45f933 的 Standards / Spec 均 0 项发现。26 份原材料及规格摘要一致。[事实核查](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-reviews.md)、[审查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review-03.md)。

## Fog

- D1—D12 的其余规则和参数继续待确认；依对应工单提供推荐、理由和用户明确结论。
- 当前未建立正式商品目录、正式用户任务或正式联合包，不能宣称样本充分。
