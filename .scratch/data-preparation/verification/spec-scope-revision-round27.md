# Spec 第27轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...edf07f4320a31a5ccf7184c69f51c8058d86e157`，29个提交。复核最终实现、配置、来源／迁移和独立QA；仅写本报告，旧记录保留，未运行Python、Conda或测试。

(a) 上轮单项完整声明路径闭合（`identity_catalog.py:69–71、129、142–148`）：not mixed with salt不计肯定组成，原句／declaration_parts保留，与Ingredients Rice一致，实际Rice加Salt仍排除。保存记录为133项通过（45.446秒）、41／86回放failures为空，生产器3f5876ba…、配置2537534e…一致。旧失败不当作当前失败。1.1.12全源／独立验收、随后评论与最终报告仍待执行（修订草案:57–60），不计静态缺陷。

(b) 未发现另行实施未经批准的研究规则、D2–D12冻结、正式SIM或模型输入。

(c) **P1：连续否定组成列表只剔除第一项，后项仍被当作真实添加。** 草案:20要求保存完整声明“和每一组成项”，:29规定否定声明“不能拼成商品身份或配料”。标题`Raw rice kernels`，features=`Contains only rice, free from wheat and salt.`，`identity_catalog.py:69–70`只移除free from wheat，留下and salt，:131／137将其判declared_outside_scope，最终:332–333误排。实际是完整单粮声明加明确否定列表，应included／declared_single_grain，跟`Ingredients: Rice`一致，不能制造假冲突。`not mixed with salt or wheat`同样把后一粮种留下当肯定组成。需保持否定列表完整作用域，保留原文；but后的真实添加或未解释的未知组成不得一并吞掉。

本轮真实发现：P1一项；最高P1。静态结论不代表全量验收通过。
