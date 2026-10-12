# Spec 复审：规则修订第三轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；固定目标：`020b0f3fbc7056c2a2489e1008f15cba3f3f54cc`。只读静态审查，未运行 Python／Conda。原 making、wheat for baking 与 Store in 的具体反例已修复，并有公共 CLI 对照；下列仍属同一上下文／形态要求的未完整闭合。

1. **P1：首个用途位置仍截掉后续独立本品事实。** `identity_catalog.py:125, 132–136`：夹具 `title="Raw rice grain"`、`description=["Perfect for dinner; this product is wheat."]`。字段未按分号划分独立陈述，`context_start=0` 将整片段清空，分号后的 wheat 身份反证不再检查；legacy 的 `missing_composition` 最终被 L176–177 放行。草案 `scope-rule-revision-draft-20261012.md:13` 要求关键身份反证待裁决，L29 要求用途与本品身份分别保存。建议：按有据的陈述边界划分语义作用域，保留用途之前及之后的独立本品陈述；配料解析继续保留完整列表，不随身份分句删组件。

2. **P1：明确 Store dry／Keep dry 指令仍提供形态。** `identity_catalog.py:26, 157–160, 176–177`：夹具 `title="Arborio Rice"`、`description=["Store dry."]` 或 `["Keep dry."]`。storage 正则未覆盖这些明确储存指令，`dry` 被加入 forms，最终 `included/not_disclosed`。草案 L19 要求直接描述售卖对象的 A 内形态；储存要求不能证明售卖形态。`Store dry` 已是既有配置中的成分结束前缀，修正其上下文角色不改变研究范围。建议：统一已有存储指令识别，验证储存句不供形态、真正 uncooked/raw 本品陈述仍可取证。

新增 `verify_scope_revision.py` 和 `verify_revision_reviews.py`：已静态核查全源 EOF、逐行来源、旧新迁移、字面证据、摘要及旧材料保护，以及评论逐字节／父商品提取、零评论保留、SQL 去重损失与严格早于目标的历史对账；未发现额外实质 Spec 缺口。脚本独立于生产模块，未冻结清洗、截断、资格或充分性参数。未执行的正式验收不算缺陷。

汇总：Spec 2 项 P1，均为此前同一语义要求的剩余反例；无新范围或研究参数要求。
