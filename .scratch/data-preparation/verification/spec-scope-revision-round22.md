# Spec 第22轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...b02b93df785cd95be8ec341074642533d5a2fa9f`，24 个提交。复核最终生产实现、配置、来源／迁移及独立 QA；未运行 Python、Conda 或测试。第21轮报告保留。

(a) 未发现新的阶段缺漏。上轮三项已有相应修复（`identity_catalog.py:79–83、200–214、258–271、327–329`）。保存的最终日志为125项通过、41／86回放失败列表为空；此前失败档案不当作当前失败。1.1.12全源／独立验收、随后全量评论及最终报告仍待执行（修订草案:57–60），不计为静态缺陷；1.1.11仍是语义拒绝档案。

(b) 未发现新增未经批准的研究规则或正式 D2–D12／SIM／模型输入实现。`quick 1 minute oats`落实已允许的quick oats形态。

(c) 剩余实现错误，P1两项：

- **烹调用途仍可能被with误作实际添加。** 草案:29要求“食谱、配餐……分别保存语义角色；不能拼成商品身份或配料”。标题`Raw rice kernels`，description=`These raw rice grains can be coated or topped with salt after cooking.`，是明确建议；`identity_catalog.py:20–43`未切开该用途，:258–267因rice→with→salt排除并标A外组成。应保持入选并留用途角色。新增用途夹具只有`long grains`而无粮种别名，不能覆盖此路径。
- **添加项在粮种前的真实mixed with陈述漏排。** 草案:13：“实际混粮、调味……仍按 A 排除”。标题`Raw rice kernels`，features=`This product is salt mixed with raw rice kernels.`，:258强制粮种位于with之前，:262又只匹配mix／blended而不匹配mixed，最终:336–337入选为成分未披露。应排除并保存明确添加反证；食谱用途与否定添加仍应保留正确对照。

本轮真实发现：P1两项；最高P1。结论针对固定提交的静态路径，不代表已完成全量验收。
