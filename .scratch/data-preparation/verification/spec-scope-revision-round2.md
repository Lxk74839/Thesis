# Spec 复审：规则修订第二轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；固定目标：`882f188b9d09fa7c19ca2903e6ce7d8654e148f9`。只读静态检查，未运行 Python／Conda。全量正式运行和独立验收尚未完成，不列为代码缺口。

第一轮原 ①标题否定、②无形态词的直接不同粮种声明、④Apple Cinnamon 风味标题：固定目标内已修正对应机制，并有公共 CLI 正反例。原 ③同句用途掩盖本品事实仍仅部分修复；新增 split 仅覆盖特定连接结构。

1. **P1：后置用途仍能抹掉本品混粮或身份反证。** `identity_catalog.py:20–26, 121–130`。夹具 `title="Raw rice grain"`、`description=["This grain blend contains rice and quinoa, making it perfect for dinner."]`：`making/perfect for` 仍将整个片段归为用途并跳过，legacy 的 `missing_composition` 在 L170–171 被放行。相同问题还存在于 `description=["This product is wheat for baking."]`。草案 `scope-rule-revision-draft-20261012.md:13` 要求真实混粮及关键身份反证阻断；L29 要求“分别保存语义角色”。建议：先保留明确描述本商品的主句事实，再划分后置用途；纯食谱／配餐句继续不能提供身份。不要仅继续枚举连接词。

2. **P1：储存要求被当作本商品形态证据。** `identity_catalog.py:123–130, 151–154, 170–171`。夹具 `title="Arborio Rice"`、`description=["Store in a cool, dry place."]`：标题确认粮种但无形态；储存句的 `dry` 被加入 `forms`，最终 `included/not_disclosed`。现有 UNKNOWN_FORM 反例只增加该句即会放行。草案 L19 要求“直接描述本商品售卖对象”的 A 内形态，只有关键词或用途不能补出干制状态。建议：储存说明保留为上下文，不提供售卖形态；补公共 CLI 正反例，确认同句真正描述 raw／uncooked grain 时仍可取证。

汇总：Spec 2 项 P1；第一轮 3 项闭合，1 项部分闭合；未发现新研究参数冻结或模块扩展。
