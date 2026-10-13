# Spec 第23轮静态复审

固定比较：`fb5eff2d09bca20381529a5da5dac9c479a28acf...40bc123e64de9d3e87c95bd56ba247c7da910d03`，25 个提交。已复核最终生产实现、本轮两处修复及既有来源／迁移／独立 QA。旧报告保留；未运行 Python、Conda 或测试。

(a) 上轮两项路径闭合：`identity_catalog.py:24、43`保存can be coated／topped用途；:258–271支持添加项在粮种前的真实with连接。真实are coated添加、Recipe及No salt对照均有公共夹具。保存的最终记录为127项通过（42.474秒）、41／86回放failures为空，生产器5197e0d3…、配置684e0978…一致。历史失败不当作当前失败。1.1.12全源／独立验收、随后评论及最终报告仍待执行（修订草案:57–60），不计静态缺陷。

(b) 未发现未经批准的粮种／形态扩围、D2–D12冻结、正式模型输入或SIM事实。

(c) **P1：明确熟制售卖陈述仍被cooked with用途捷径隐藏。** 草案:13规定：“存在未解决的关键身份、形态、成分或食用定位反证时仍待裁决”；:29要求食谱／配餐分别保存语义角色。标题`Raw rice kernels`，description=`This product is sold cooked with salt.`，明确描述实际售卖状态；`identity_catalog.py:24`无条件把cooked with标为用途，:43截出`This product is sold`，使熟制形态和添加反证都不参与检查。最终:336–337可入选为成分未披露。按已有Raw／熟制冲突原则，应阻断入选、待裁决并保留原句；When cooked／Recipe／Serve with仍是用途，不能一并当作实际销售事实。

本轮真实发现：P1一项；最高P1。静态路径结论不代表全量验收通过。
