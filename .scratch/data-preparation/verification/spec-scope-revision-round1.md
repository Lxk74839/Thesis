# Spec 审查：规则修订第一轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；实现：`4d2040becf59cbee5f891189ca9d36530ac020dd`。仅静态审查，未执行 Python／Conda；下列为需要由公共 CLI 验证的具体反例。全量运行与验收尚在推进，不列为缺失。

1. **P1：标题否定重新成为正向身份。** `identity_catalog.py:84–94, 101–103, 157–158`：新 `sold` 从原始标题重新找粮种，未沿用否定作用域。夹具 `title="No Raw Rice Grain"`，旧分类为 `weak_identity`；新分类具有 rice 与 raw/grain，最终 `included`。草案 `scope-rule-revision-draft-20261012.md:29`：“否定声明……不能拼成商品身份或配料。”修复：标题也必须划分否定与肯定售卖对象，否定部分不能提供身份／形态，保留反证。

2. **P1：不同粮种的直接身份反证依赖形态词才检查。** `identity_catalog.py:135–141`：夹具 `title="Raw rice kernels"`、`description=["This product is wheat."]`；此句无 `identity_forms`，因此不比较 wheat 与 rice；legacy 的 `missing_composition` 又被新版放行，最终 `included`。草案 L13：“存在未解决的关键身份……反证时仍待裁决。”修复：先检查直接本商品身份及其矛盾，再独立搜集形态；不能要求同一句反证重复 raw/grain 等词。

3. **P1：同句用途词掩盖真实混粮。** `identity_catalog.py:23–24, 114–121`：夹具 `title="Raw rice grain"`、`description=["This grain blend contains rice and quinoa and is perfect for dinner."]`；`perfect for` 将整句归为用途并跳过，本品 blend／quinoa 反证消失，最终 `included`。草案 L13、L29 分别要求阻断真实混粮、区分语义角色。修复：用途只作用于其局部子句；同句直接售卖／组成声明仍须检查并保存。

4. **P1：明确风味组合标题被当成成分未知原粮。** `identity_catalog.py:86–100, 157–158`：夹具 `title="Whole Grain Oatmeal Apple Cinnamon"`、其他字段为空，既未命中现有 A 外对象，也未进入配料解释，最终 `included/not_disclosed`。草案 L13：“实际混粮、调味……仍按 A 排除”；L19 要求本品售卖对象证据。修复：解释标题中直接描述本品的风味／新增配料组合，不能仅因没有 Ingredients 字段把明确调味对象转为未知原粮；歧义保留待裁决。

汇总：Spec 4 项发现，均涉及错误入选；未发现额外研究参数冻结或模块扩展。
