# Spec 第十七轮固定复审

基线：fb5eff2d09bca20381529a5da5dac9c479a28acf。目标：e20102a0f48e242c79436b62fda2a50b1aecfb43。核对完整三点差异及 18 个提交记录；依据用户已采纳的修订草案正文、执行记录、正式规格与工单 04／05。

(a) 缺漏／部分：未发现额外静态实现缺漏。新全源目录、评论复扫及实际覆盖仍须运行验收；不将待执行验收记为代码缺失或已通过（草案 57—60；spec.md:68）。

(b) 扩围：未发现。A 边界、父商品评论关联及来源声明限制保留；独立验收脚本没有生产导入，工单 06 仅聚合条件选项，未冻结清洗、资格、截断或输出模型输入／标签（草案 39、43、59；05-review-diagnostics.md:12、18）。

(c) **[P2] 食谱的部分声明标记污染本品完整声明。** 草案 20 要求保存实际成分范围，29 规定食谱“不能拼成商品身份或配料”，30 禁止强行续接明确食谱。identity_catalog.py:100 已结束食谱前的配料列表，但 119、124 仍在整个字段搜索部分声明标记。公共夹具：标题 `Raw rice kernels`，features 为 `Ingredients: Rice. Recipe: made with rice and salt.`；本品 declaration_parts 仅 Rice，食谱的 `made with` 仍令完整声明变为 unresolved，最终 pending；应 included／declared_single_grain，仅表示来源声明。须按各声明范围判断部分性，保留原文；真实本品部分声明仍未决，普通 `Ingredients: Rice. Salt.` 仍排除。

上一轮第二个完整 Ingredients 标签及明确 Recipe 边界在本目标静态闭合。本轮 1 项 P2；只读静态审查，未运行 Python、Conda、测试或全源验收。
