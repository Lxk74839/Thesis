# Spec 第28轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...0b185d6526b376501b594fdd51d3b9e8b4a467cf`，30个提交。复核最终实现、配置、来源／迁移和独立QA；仅写本报告，未运行Python、Conda或测试，旧记录保留。

(a) 上轮裸组成项连续否定列表已闭合（`identity_catalog.py:35–60、75–78`）：已知列表整体剔出肯定组成，but后真实添加保留，novel_additive仍unresolved。:229–231重建旧composition_declaration_conflict，避免一致Ingredients Rice留下旧假冲突；真实声明冲突仍由:337–339恢复。保存记录为134项通过（45.746秒）、41／86回放failures为空，生产器ac06d61b…／配置2537534e…一致。旧失败不当作当前失败。1.1.12全源／独立QA、随后评论和06建议仍待执行（草案:57–60），不计静态缺陷。

(b) 未发现另行实施未经批准的研究规则、D2–D12冻结、正式SIM或模型输入。

(c) **P1：已有形态修饰词使否定混合失效，产生假混粮。** 草案:20要求正确保留完整组成声明及每一组成项，:29规定否定声明“不能拼成商品身份或配料”。标题`Raw rice kernels`，features=`Contains only rice, not mixed with whole grain wheat.`，whole／grain已在配置composition_modifiers中；但`identity_catalog.py:50–55、75–78`只允许mixed with后直接是粮种别名，未识别被否定的whole grain wheat。:138／145把rice、wheat计作多粮种，最终:340–341排除。应included／declared_single_grain，与`Ingredients: Rice`一致，保留原句和否定角色。落实已批准修饰词不等于吞掉未知novel_additive；but后真实添加仍须保留。

本轮真实发现：P1一项；最高P1。静态结论不代表全量验收通过。
