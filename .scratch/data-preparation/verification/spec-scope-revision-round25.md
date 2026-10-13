# Spec 第25轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...b7490016b2e8e83b9ee152a5680594ad3a5a4869`，27个提交。已复核最终实现、配置、来源／迁移及独立QA；旧记录保留，未运行Python、Conda或测试。

(a) 上轮两项路径闭合：本商品mixed添加及完整单粮声明冲突由`identity_catalog.py:262–271、327–329`处理，can be mixed／Recipe保留用途；配置新增powder／powdered，颗粒／Powder字段冲突待决、明确粉类标题排除，否定与食谱对照保留。保存的最终记录为131项通过（42.778秒）、41／86回放failures为空；生产器bd9e7dd0…、配置2537534e…一致。旧失败不当作当前失败。1.1.12全源／独立验收、随后评论及最终报告仍待执行（修订草案:57–60），不计静态缺陷。

(b) 未发现另行实施未经批准的研究规则、正式D2–D12／SIM／模型输入；powder落实既有A粉类排除。

(c) **P1：否定混合陈述仍被当作真实添加而排除。** 草案:29要求“否定声明分别保存语义角色；不能拼成商品身份或配料”，:13只排除实际混粮／调味。标题`Raw rice kernels`、features=`This product is not mixed with salt.`，`identity_catalog.py:44–52`的被否定词表没有mixed，:64–69仅移除紧接组成项的否定，故not mixed with salt保持为肯定候选；:262–267匹配mixed及salt，输出excluded／declared_outside_scope。应保留否定原文／角色，保持included／not_disclosed，不补造完整组成。`This rice is not mixed with salt.`同样误排；真实mixed with salt须仍排除，but后的真实contains wheat／salt反证也不能被整体删除。

本轮真实发现：P1一项；最高P1。静态结论不代表全量验收通过。
