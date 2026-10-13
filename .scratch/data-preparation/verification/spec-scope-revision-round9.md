# Spec 第九轮复审

基线 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；目标 `8bda2f6dc2bed0bff70605dbac075d6819c5f455`。完整静态 Spec 复审，未运行代码。

**P1：标题用途截断掩盖后续独立身份反证。** `identity_catalog.py:122–124,146–158,233–234`：夹具 `title="Raw barley kernels; when cooked, serve with salt; this product is wheat grain."`。sold 截在 when cooked，解除 legacy 的 cooked 排除；source_statements 跳过 title，后续 wheat 不再检查，最终 included/barley。草案 `scope-rule-revision-draft-20261012.md:13` 要求关键身份反证待裁决，L19 包含标题证据，L29 要求用途分别保存语义角色。应按独立陈述边界核对标题后续事实，保留纯烹调上下文控制；须公共 CLI 验证。

上轮熟制反例及 uncooked／when cooked 控制闭合。完整复核 A 范围、多粮种／成分冲突、肯定与否定、未知非验证、父商品评论及零／低评／空文本保留、迁移与独立 oracle，未见其他新增缺口。1.1.4 明确中止且保留五摘要，未伪称完整。06仍为未批准条件诊断，无扩围或研究参数冻结；待生成运行结果不算缺失。

Spec：1 项 P1，最严重为用途掩盖关键身份反证造成错误入选。
