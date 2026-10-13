# Spec 复审：规则修订第四轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；固定目标：`995dbfc129a299401c712140e285111e9be30b62`。读取实际 code-review 技能，确认基线及非空 three-dot diff；只读静态审查，未运行 Python／Conda。以下结果来自固定提交，未把尚在推进的全量验收列为实现缺失。前三轮的具体反例已有对应修复及公共 CLI 测试。

1. **P1：非特定前缀的范围外身份反证漏检。** `identity_catalog.py:141–158,177–178`。夹具 `title="Raw rice grain"`、`description=["The grain in this bag is quinoa."]`：legacy 不读取此非固定前缀陈述；新版 `grain_crops` 不返回 A 外 quinoa，混合检查又要求 blend／contains 等词，故最终 `included/not_disclosed`。草案 `scope-rule-revision-draft-20261012.md:13` 要求“未解决的关键身份……反证时仍待裁决”；L31 不要求字段以特定前缀开头。建议：直接本品身份的范围外反证也参与一致性判断，保留原文并待裁决；纯配餐／过敏原不得因此成为身份。

2. **P2：否定成分被拼成添加成分。** `identity_catalog.py:52–71,171–172`。夹具 `title="Raw rice kernels"`、`features=["Ingredients: Rice. No sugar."]`：active 配料续接 `No sugar`，随后 sugar 被判为实际 A 外添加，结果 `excluded/declared_outside_scope`。草案 L29：“否定声明……不能拼成商品身份或配料”；L30 要求依据语义划分声明范围。建议：保留否定声明但不把否定对象当组成项，仍完整保留真正的 `Rice. Salt.` 连续配料。

3. **P2：整字段遗留反证使纯配餐继续阻断。** `identity_catalog.py:119–122,133–137,177–178`。夹具 `title="Raw rice grain"`、`description=["This product is raw rice grain. Serve with wheat bread."]`：legacy 以整字段的 bread 生成 `field_form_conflict`；因首句不是上下文，all-context 条件不清除该反证。新版虽跳过 Serve 子句，最终仍 pending。草案 L19 允许明确本品身份／形态相互支持，L29 要求配餐“不能拼成商品身份或配料”。建议：按已划分的本品／用途子句重建反证，保留真实片／粉冲突，不能沿用整字段误命中。

两份新增独立 oracle 未导入生产模块；来源、摘要、逐行旧新迁移、字面依据、评论原字节／父商品、零评论及 SQL 条件历史对账未发现新增 Spec 缺口。未发现未请求的模块扩展或研究阈值冻结。代表案例对齐不等于全体语义正确，脚本已明确限制并输出新入选抽查材料。

汇总：Spec 3 项发现（P1 1 项、P2 2 项）；最严重为范围外直接身份反证造成错误入选。具体反例均待主代理通过公共 CLI 验证和 TDD 修复，未宣称本审查执行了测试。
