# Spec 第29轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...0ad81e1cfc979ab39d802902e1edd5969437dd46`，31个提交。复核最终实现、共享组成表达式、配置、来源／迁移和独立QA；旧记录保留，未运行Python、Conda或测试。

(a) 上轮whole grain wheat／organic barley否定对象、Ingredients Rice一致、真实mixed及but contains salt控制均闭合；共享组成表达式和分隔语法仍只处理已有词表，novel_additive保留未决。保存记录为135项通过（44.317秒）、41／86回放failures为空；生产器5f3af59f…、配置2537534e…一致。旧失败不当作当前失败。1.1.12全源QA、全部评论及06建议仍待执行（修订草案:57–60），不计静态缺陷。

(b) 未发现另行实施未经批准的研究规则、D2–D12冻结、正式SIM或模型输入。

(c) **P1：本商品粮种的X-free直接否定在冲突重建中丢失。** 规格:76：“未解决的关键冲突不得进入正式目录”；修订草案:13要求关键身份反证待裁决，:29要求否定声明保存语义角色。标题`Raw rice kernels`，features=`This product is rice-free.`，`catalog.py:73–80`原能保留同粮种否定冲突；但`identity_catalog.py:75`无条件删除X-free，:233–235清除旧field_identity_conflict后，:286–298只重判not／no等否定，未恢复rice-free反证，最终:350–351可入选为成分未披露。应pending并保存标题／字段原文和否定角色。异粮种`wheat-free`对raw oat／rice仍不制造身份冲突。

本轮真实发现：P1一项；最高P1。上述为可证静态路径，未做运行复现；不将未证实猜测计为发现，也不代表全量验收通过。
