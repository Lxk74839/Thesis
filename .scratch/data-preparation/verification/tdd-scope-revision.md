# 新版 04／05：逐行为 TDD 实际记录

公共 seam：prepare_data.py CLI 的 catalog／review_extract，沿用用户确认；固定基线 fb5eff2d09bca20381529a5da5dac9c479a28acf。全部命令使用 `conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -m unittest ...`。不从生产函数内部取预期值。

| 行为／测试 | 实际 Red | 最小 Green |
| --- | --- | --- |
| admits_explicit_grain_with_unknown_composition | 原目录空，预期 RAW／not_disclosed，断言失败 | 独立身份规则路由；明确形态且仅缺声明可入选；单项通过 |
| does_not_infer_form_from_category_or_ingredients | Arborio＋配料＋类别被纳入，预期形态未明待裁决 | 独立正向形态词与依据；类别、包重、仅粮种配料不补形态；两项通过 |
| uses_direct_fields_without_fixed_prefix | uncooked rice 非固定前缀的商品未入选 | 有直接粮种／形态陈述的字段参与判断，配餐句不参与；单项通过 |
| recognizes_the_sold_object_before_grain_words | 酱料／托盘／蜂蜜／starter 被误列待裁决或入选 | 先识别标题实际商品中心并记录完整原句，不能因粮种名称纳入；单项通过 |
| separates_marketing_percentages_from_composition | Premium／Italian 被误当完整组成，变成 unresolved | 有据品质／来源百分比保持非成分角色，真实纯粮声明另记；单项通过 |
| keeps_ingredient_continuations_but_not_cooking_directions | Salt 续行、烹调句、声明冲突都误列 unresolved | 独立披露解释保留续行和未知，明确烹调边界；混合／真实冲突阻断；单项通过 |
| resolves_known_names_without_collapsing_millet_species | Hato Mugi、Barnyard、Fonio 漏解，Ragi/Bajra 混粮未区分 | 确证别名、完整原句、上位类别与不同粮种分别解释；长别名优先完整匹配；单项通过 |
| admits_dry_flakes_but_keeps_processing_counterevidence | 干片仍被 blanket poha/flattened 阻断，调味未明确排除 | 干片、片／粉冲突、parboiled 待决及实际调味分别处理；单项通过 |
| retains_real_counterevidence_but_ignores_context_roles | 设施／配餐误作形态冲突，食用／饲料反证被放行 | 逐句区分语义角色；显式否定不作正向身份，真实字段／食用定位冲突保留；单项通过 |
| blocks_explicit_mixtures_and_partial_composition | 明确米／麦混粮误 pending、部分配料误成未知、粉类被配料未决覆盖 | 标题明确多粮种及本品新增配料阻断；部分声明不当完整声明，A 外形态保留；单项通过 |
| records_every_old_new_decision_and_preserves_old_artifacts | CLI 不接受 previous-catalog-record，无法产生迁移产物 | 旧审计摘要验证与逐行对齐、全量旧新状态及理由记录；旧产物字节保持；单项通过 |

首轮全套 59 项回归中发现既有新版烹调边界测试失败：逐句反证检测把 Cooking instructions／Add oil 当作油类形态。该既有失败即 Red；补齐明确烹调／营养角色，单项重新 Green，未放宽真实配料续行。

实际 41 条原记录通过 CLI 复现时发现 7 个不符项，尚未生成正式全量版本。针对机制逐项修复：品牌产品线及 not sticky 质地描述误作反证，新增公共夹具实际 Red 后修正角色和否定作用域，单项 Green。

Bird Seed and Feed 含 making 用途文字时被误跳过，公共夹具 Red；先保存实质食用定位反证再记录用途角色，Green。

真实部分配料的 ingredients like／sweetened with 被错当未披露，公共夹具 Red；保留明确添加配料与部分声明状态，不将纯粮部分陈述当完整，Green。

调料包与 Seasoned Rice 类别的真实矛盾被 A 外对象捷径忽略，公共夹具 Red；保留具体商品类别反证，茶／米词的假矛盾仍区分，Green。

明确罐装蔬菜与单纯金属罐包装需区分。初始夹具 Corn Cans 已被旧标题规则捕获，实际为绿，不能当作 Red；已撤回新增逻辑，把夹具调整为真实结构 Corn, 15 oz Cans，重新观察到 Red，再实现直接售卖形态识别后 Green。前者按售卖形态排除，后者不靠包装改变原粮身份。

标题 alternative to 被误作售卖混粮，公共夹具 Red；只读取实际售卖段，同时在明确 millet 列举上下文辨认 Foxtail／Kodo 等多个粮种，Green。

同粮种但 Rice 与 Rice＋Salt 的多条声明被当作一个配方，公共夹具 Red；对实际声明包含的粮种及其他成分分别对账，保持冲突，Green。

review_extract 复用行为补充公共入口回归：新身份目录保留完整成分未知、零评论商品，末尾／低评分／空文本原字节均提取，且不按变体关联。已有评论实现本身通过此测试，无须新增实现，也不声称观察到 Red。

第一轮独立审查：Standards 0 项；Spec 4 项 P1，尚未全量生成。均通过公共 CLI 逐项观察 Red 并修复：No Raw Rice Grain 否定误入选；This product is wheat 不重复形态词的直接身份冲突；真实混粮与 perfect for 同句；Apple Cinnamon 本品风味误作未知纯粮。用途仅在局部分句生效，食谱仍不充当配料。另在第三项中追加 rice/wheat 实际混粮反例，观察到待裁决误覆盖排除的 Red 后修复。全部单项 Green，第二轮全套 71 项通过（24.353 秒），见 scope-revision-tests-round2.txt。旧配置／既有行为仍通过。
