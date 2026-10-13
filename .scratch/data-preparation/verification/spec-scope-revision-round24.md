# Spec 第24轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...5af8fb2727ff3c79fca18e03af8eac72c757db6b`，26个提交。复核最终实现、配置、来源／迁移和独立QA；仅写本报告，未运行Python、Conda或测试。

(a) 上轮sold cooked with路径已闭合（`identity_catalog.py:24、43、291–293`）；习惯often cooked with及明确条件烹调保存用途。最终保存记录为129项通过（43.040秒）、41／86回放failures为空，生产器f788db3b…及配置684e0978…一致。历史失败原文保留，不当作当前失败。1.1.12全源／独立验收、随后全部评论与最终报告仍待执行（修订草案:57–60），不计静态缺陷。

(b) 未发现另行实施未经批准的研究规则、正式D2–D12／SIM／模型输入。

(c) 剩余P1两项：

- **直接售卖添加未重复粮种名时仍漏识别。** 草案:13：“实际混粮、调味……仍按 A 排除”。标题`Raw rice kernels`，description=`This product is sold mixed with salt.`，明确指本商品；`identity_catalog.py:258–261`要求该片段再次出现粮种名，:262不匹配mixed，两种判据均不成立，最终:336–337入选为成分未披露。应排除并留原文；再有完整`Ingredients: Rice`时应pending／conflict，当前仍可入选。
- **Powder售卖字段未阻断颗粒身份。** 草案:13要求“存在未解决的关键身份、形态、成分或食用定位反证时仍待裁决”，且A仍排除粉类。标题`Raw rice kernels`、`details.Item Form="Powder"`，配置:174–218只有protein powder而无独立Powder，:460–463的显式形态仅有cut／grits和flaked；`identity_catalog.py:291–293`未记录此粉类反证，最终:336–337入选。应待裁决并留双方依据；这是已确认粉类边界的落实，不是新增范围。

本轮真实发现：P1两项；最高P1。静态结论不代表已完成全量验收。
