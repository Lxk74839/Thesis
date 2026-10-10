# 03: 获取完整评论并核查关联与时间事实

**What to build:** 通过公共数据准备入口取得完整评论来源，验证评论与父商品的关联字段和时间字段事实，形成可复核的原始来源与字段诊断。

**Blocked by:** 02：获取完整商品元数据并核查字段

**Status:** resolved

- [x] 记录评论来源版本、获取信息、字节数、SHA-256 和完整扫描结果；保留所有评分及原始文本。
- [x] 核实父商品标识与变体标识的含义，统计关联缺失和异常；不得将真实评论关联到 SIM 批次。
- [x] 通过官方说明和实际样本确认时间字段、单位与时区映射，保留原始时间值及可审计的转换依据。
- [x] 单独报告损坏、解析失败、缺失字段和异常时间；尚未确认的处理规则不能被隐式应用。
- [x] 公共入口夹具覆盖文件末尾评论、关联缺失和时间映射；实验场景、预算及所需用户数未确定不阻断本工单。

## 未决前置事项

D2 的实际字段、单位、时区等事实由官方资料与实际记录交叉核实；时间截断和异常记录处理选择留待工单 06。

## 执行约定

- 规格正文已确认，未决规则与参数尚未冻结。本次仅批准工单拆分；涉及的未决项须先完成明确的事实核查或用户决策，不得代填默认数值。
- 仅保留已确认的一个公共数据准备入口。数据功能实现按 TDD 逐个行为执行红、绿循环，通过入口验证外部结果；完成后按固定提交起点执行 Standards 与 Spec 代码审查，处理发现后提交。
- 项目依赖安装、代码运行、测试及构建显式使用 Thesis 专属环境；论文及原有研究材料只读，修改范围最小。

## Comments

- 2026-10-10：用户授权实施完整评论获取、父商品关联与时间事实诊断。继续唯一公共入口 prepare_data.py，新增 reviews 阶段；全部运行及测试通过 conda run -p 指定 Thesis 环境。审查固定起点保持已确认的初始基线 b59611e97b6eedf07c4e624884c48570fbfa2cdd，另记录工单开始 HEAD c4550bfe78a3f083e729df3f4ecafa4123f6373d 以界定本工单增量。原始数据不筛选、不清洗、不截断、不生成正式目录或联合包；D1—D12 的未决研究选择继续待确认。

- 2026-10-10：7 个新增行为逐项 TDD，连同既有行为共 18 项测试通过。实现提交 5935f9b05829d49cef0919d48a0561f90a45f933 经固定起点的 Standards / Spec 并行审查，两轴均 0 项发现。完整获取及诊断已按下述依据验收，关闭工单；0.0 评分原样保留并继续标记 needs_review，不提前执行工单 06 的清洗选择。

## Answer

通过唯一公共入口 prepare_data.py 的 reviews 阶段取得官方完整 Grocery 评论文件：**1,630,860,152 字节，14,318,520 行／对象**；SHA-256 `7f6ae806af2e2dbdda8564abde3141b81c7ee3cf4d8443d361d6bdad91aea4b8`。HTTP 字节数对账、gzip EOF／CRC、独立落盘摘要与第二进程分块换行／EOF 校验均通过。下载落盘完成时间 2026-10-10 14:05:04.6657715 UTC，来源报告完成时间 14:08:56.003388 UTC；[机器来源记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/sources/amazon-2023-grocery-reviews.json)保留来源、响应头与完整诊断。

损坏、解析失败、非对象、缺失字段和异常时间均 0。发现 1 条官方评分域之外的 0.0 评分（原始行 378447），以及 16,801 条空白正文；两者均未被删除、补值或改写。来源状态 needs_review 明确对应评分异常；获取与诊断完成，不宣称清洗完成。

14,318,520 条评论全部按 parent_asin 匹配 603,182 个父商品，缺失／无法匹配均 0；完整元数据中 92 个父商品无评论。7,961,504 条 asin 与 parent_asin 不同；asin 不作回退关联，真实评论不关联 SIM 批次。

官方字段说明、作者论文及实际整数分布共同核实 timestamp 为 Unix epoch 毫秒，按 UTC 映射；最早 2000-08-09T11:26:35.000+00:00，最晚 2023-09-12T20:20:38.851+00:00。独立 .NET 五点转换和原整数回验通过。[事实与转换依据](C:/Users/Kane/Documents/CodexProject/Thesis/docs/data-sources/grocery-reviews.md)、[独立验收记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-check.json)完整留档。

全部运行及 18 项测试显式使用 Thesis 环境；[TDD 留痕](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/tdd-03.md)与[两轴审查](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review-03.md)已保存。[关闭前再次校验](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/protection-03.json)确认 26 份原稿及既有研究材料、已确认规格和被审查实现的摘要保持不变。D2 仅字段、单位与 UTC 的事实子项已核实；D1—D12 其余研究规则与参数继续待确认。
