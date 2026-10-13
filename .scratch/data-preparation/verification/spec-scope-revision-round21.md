# Spec 第21轮静态审查

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...0cc7b641502616da6af747f947ef2b019600e5a9`，22 个提交。按已确认修订审查最终 1.1.12 实现；历史候选、失败日志与旧验收作为档案。未运行 Python、Conda 或测试。

(a) 1.1.12 全量扫描／迁移、独立验收、随后评论复扫及最终报告仍待执行（修订草案:57–60、执行记录:13）；不将这些阶段待办计为静态缺陷。1.1.11 数量 QA 通过但语义拒绝，不视为已验收。

(b) 未发现另行实施未批准的 D2–D12 规则、正式用户划分、模型输入或 SIM 事实。

(c) 实现错误，共 3 项：

- **P1：配料／原料形态仍能补出售卖形态。** 草案:19 要求“直接描述本商品售卖对象”。`identity_catalog.py:219–227、286–293` 对全部声明采集形态，没有配料／原料隔离。标题 `Arborio Rice`、`details.Ingredients="Raw rice flakes"` 会凭配料生成 forms，经:324–325 入选；应缺少售卖形态而待裁决。`Made from raw rice flakes` 同样影响该路径。
- **P1：直接 with 添加陈述被当成未披露纯粮。** 草案:13：“实际混粮、调味……仍按 A 排除”。标题 `Raw rice kernels`、features `Raw rice kernels with salt.` 不产生配料声明；:251 的 mixture 判据缺少直接 with，:280 也不识别 salt，最终:324–325 入选。应排除；明确食谱用途仍仅属上下文。
- **P2：熟制标题的反向关键冲突仍被早退。** 草案:13：“存在未解决的关键身份、形态、成分或食用定位反证时仍待裁决”。标题 `Cooked rice`、features `This product is uncooked rice.` 不命中配置:462–465 的 solid_sale_shapes；`identity_catalog.py:193–209` 直接排除，只保留标题反证。应待裁决并留存双方依据。

本轮真实发现：P1 2 项、P2 1 项；最高 P1。以上均为固定提交的静态路径结论。
