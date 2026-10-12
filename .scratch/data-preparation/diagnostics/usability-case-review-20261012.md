# 41 条代表原始记录的逐条语义核查

**状态：proposed_only；未改正式商品裁决。** 这不是全量语义裁决或入选预测。

原始样本包含完整元数据及旧决定的全部证据和反证：[完整原始记录](C:/Users/Kane/Documents/CodexProject/Thesis/data/diagnostics/usability-04-05-draft-01/representative-records.json)。源 SHA-256：`ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`。

取样：First source row plus two lexicographically smallest SHA256(parent_asin) values per existing reason, supplemented with named raw examples. Not a probability or complete semantic audit.

每条使用 title、全部 features、description、details 与 categories；评分、评论数、价格和模型结果不用于商品判断。具体引文与上下文见完整源对象；下列完整标题是原文，行号为全源 gzip 解压后的 1-based 行。原句摘录的逐项检查数量：15。

主分组是排查主因，不表示同一对象没有其他问题；全部原始反证仍保留。I=身份和 A 内形态明确，完整成分未披露；P=可核实的别名、文本或类别层级解释遗漏；X=明确 A 外售卖对象、混合或成品；C=真实字段冲突或关键定位歧义；U=证据不足或尚未解决的加工边界。

| 主分组 | 数量 |
| --- | ---: |
| 明确 A 外售卖对象、混合或成品 | 24 |
| 身份和 A 内形态明确，完整成分未披露 | 5 |
| 可核实的别名、文本或类别层级解释遗漏 | 4 |
| 真实字段冲突或关键定位歧义 | 5 |
| 证据不足或尚未解决的加工边界 | 3 |

全部为 41 条非概率案例的数量；剩余 56,168 条没有逐条完成这类语义复核。

## 1. B00KBRUYVM／原行 3

> Chipped Beef and Gravy By Patterson's - Great for Breakfast or Dinner - 8 Ounce Cans - 6 Cans Per Case

- 旧理由：`weak_identity`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：所售 Chipped Beef Gravy；米饭和 grits 为配餐用途。不是谷物原粮；完整配方未知。 Tomatoes 类别异常一并保留；不把不相容类别当作本品谷物证据。
- 原始行 SHA-256：`fa562e4264a1839db49f86c54b13cb9facd007616ea35b0d74948c0a2f06f5d4`。

## 2. B07TTJYHGX／原行 12

> RXBAR, RX A.M. Oats, Variety Pack, 9ct, 2.18oz Cups, 9 Gluten Free Oatmeal Cups

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：RXBAR 多口味燕麦杯；原文明确蛋白、果、坚果及燕麦等。复合即食准备产品，不是单粮种原粮／干片。
- 原始行 SHA-256：`cd84465a974a5db0f20bb04a4cdfd4566374245bc0e36f6406bf9d5cf289b3c4`。

## 3. B0BYLK9168／原行 13

> TAJ Indian Poha Powa Flattened Rice (Thick, 4-Pounds)

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：身份和 A 内形态明确，完整成分未披露；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：标题明确 Poha／Powa／Flattened Rice Thick，类别为干粮米类；压片形态有来源支持。没有完整配料声明；来源所售身份不证明真实无添加。
- 原始行 SHA-256：`072282fea9d9ddb8935262210716ec8e86ce5ebac018ef13719b46d589666460`。

## 4. B0BDV6ZTHR／原行 31

> Purely Elizabeth, Organic Apple Cinnamon, Oatmeal Pouch 10oz (3 Ct.), Gluten-Free, Instant, Non-GMO

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Apple Cinnamon Oatmeal；原文列燕麦、藜麦、苋、果、坚果等，实质复合／调味成品。
- 原始行 SHA-256：`43bb24491ab3fcf2e061d73163d8ca000d095f523953abe31c405a70955f3206`。

## 5. B09S8Q6FG5／原行 69

> Friendly Grains - Crunchy Rollers - Organic Rice Snacks, Crispy Puffed Rice Rolls, Healthy Snack Rolls for Adults and Kids - Apple Cinnamon (4 packs of 6)

- 旧理由：`category_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Apple Cinnamon Crispy Puffed Rice Rolls，类别 Rice Snacks；售卖膨化调味零食，不能以 rice 命中原粒。
- 原始行 SHA-256：`bb50048449bc10b095f47e6a3ee129a689d0955fea4d5c11c769db4c952b5041`。

## 6. B08Q44XV13／原行 258

> [Product of Japan] Japanese Tochihonoka Milled Koshihikari Sushi Rice, White Short Grain (Tochigi Prefecture) 【精米】栃木県産コシヒカリ - 11 Pound / 5KG

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：身份和 A 内形态明确，完整成分未披露；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Milled Koshihikari Sushi Rice／精米；全文明确售卖碾白稻米。食用后 freshly cooked 描述不是出售熟饭；完整配料未知，产地和收获宣传仅为来源声称。
- 原始行 SHA-256：`ce668f398ef8d3ac6d43a7599ffd517309e36ad4d1a481ce06809c8b95eb894a`。

## 7. B00HU6WYJ2／原行 282

> Snappy Maze Craze Combo Movie Popcorn Trays, 50Count

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Snappy Popcorn Trays；所售容器装爆米花、饮料和糖果。品牌种玉米历史不使托盘成为玉米原粒。 Free Sampling 类别不规范且与所售托盘不相容，一并保留。
- 原始行 SHA-256：`a29bea04b52d62fd54caedd87e9c146790d6522df544b136f5a8b5aaa837f502`。

## 8. B09TS94RVG／原行 345

> Bakery On Main Quick Oats - Gluten Free, Non-GMO Project Verified, Kosher, Resealable Bag, 24oz (Pack of 4)

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：身份和 A 内形态明确，完整成分未披露；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Quick Oats，原文明确 whole grain oats；烘焙用途和品牌其他零食不是本品组成。完整配料未披露；不将 gluten-free 等推广为核验事实。
- 原始行 SHA-256：`d9cfcca8e1ce372829432026ccd750c54a65041ff2855a95a9f16c7bf80c0740`。

## 9. B0BMSZCYM7／原行 416

> Himalayan Chef Basmati Rice, Long Grain Rice Fluffy Quick Cooking Aromatic - 10 lbs.

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：身份和 A 内形态明确，完整成分未披露；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Basmati Long Grain Rice；原文为煮米说明，烹调可加入油、黄油和盐是使用步骤。售卖米粒形态明确，完整组成未知。
- 原始行 SHA-256：`10b914158d9be44004d27b57a6c3becd5bda073622b89b735efa742b6e962091`。

## 10. B078RRSYFH／原行 652

> Cloves | Aromatic and Sweet Spice | Rice Pudding | Perfect for Sweet and Salty Dishes 4 oz.

- 旧理由：`unresolved_composition`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：标题中心为 Cloves，Rice Pudding 是用途；100% PURE／SATISFACTION 不构成完整稻米配方。所售香料非 A。
- 原始行 SHA-256：`946d8be5f85a746881c54400cbd97d8b63fb0b578121b97ee0f518774de51fb0`。

## 11. B0C1MM67QJ／原行 1961

> Aduna Organic Fonio Super-Grain | Premium Gluten-Free African Ancient Super-Grain | All Natural, USDA Organic, Non-GMO Fonio Superfood Grain | Single Resealable Pouch 1 x 2.2lb

- 旧理由：`category_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：可核实的别名、文本或类别层级解释遗漏；拟议成分状态：`declared_single_grain`。
- 依据、反证与未知：原文 Nothing else is added, just 100% pure organic fonio grain；食谱替代 rice／quinoa 是用途。FAO 将 fonio 列入其他 millets，末级 Millet 为上位类别，不能只按配置键判冲突。真实配方仍未经独立核验。
- 原始行 SHA-256：`b2cd6570e88332ba94f8282440ad5086c499497a458d42e2b310be854f65467f`。

## 12. B07BXYMNFN／原行 3420

> Colombian Medellin from the Santa Barbara Estate: Supremo Coffee Beans 17/18 (Medium Roast (Full City +), 2.5 pounds Whole Beans)

- 旧理由：`field_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：所售 Colombian Supremo Coffee Beans；This is because 描述种植海拔，beans 指咖啡豆。不是另一个谷物身份声明或真粮种冲突。
- 原始行 SHA-256：`98793883c2a64325461ddea29fed93cfaaebda428d68bd675c9ddbcba6f30a67`。

## 13. B088PZLRK7／原行 5817

> ROM AMERICA Sweet Sticky Glutinous Short Grain Brown Rice for Asian Cooking and Desserts - Risotto, Porridge, Healthy Breakfast Bowl, Soups, Pudding - 현미찹쌀 Hyeonmi Chapssal - 2 Pound (Pack of 1)

- 旧理由：`unresolved_composition`，仍保持原正式 pending。
- 拟议主分组：可核实的别名、文本或类别层级解释遗漏；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Brown Glutinous Short Grain Rice；100% PREMIUM QUALITY 是品质，不是完整成分；mix／porridge／soaking 是烹调用途。售卖米粒明确，误把宣传续接为配料产生 unresolved。
- 原始行 SHA-256：`cc51bb883ea2aa9fd4c76fbdfc7606d6abb7916b5771eb2cacf3b2a4b2910b15`。

## 14. B0C2QMVTW8／原行 6682

> Sunflower Seeds, 18 Pounds - Non-GMO Verified, Kernels, No Shell, Kosher, Raw, Vegan, Sirtfood, Bulk

- 旧理由：`field_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Sunflower Seeds Raw Kernels 是葵花籽，非 A 真谷物。设施 wheat 过敏原警告不是小麦组成，也不是产品形态冲突。
- 原始行 SHA-256：`c7209df34e4dc28cf965c432cad8ac33361bcb2562e681f61140652ab7e9c36c`。

## 15. B018ZORFSW／原行 8788

> 48 Nurses Doctors Edible PREMIUM THICKNESS SWEETENED VANILLA, Wafer Rice Paper Cupcake Toppers/Decorations

- 旧理由：`composition_declaration_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Sweetened Vanilla Wafer Rice Paper Cupcake Toppers 为装饰成品；原配料 potato starch／water／vegetable oil。100% EDIBLE 不是谷物声明。
- 原始行 SHA-256：`611c3f41cb2489ca5037f9ff804f3f2853509372317a78787df63cbb01c8eb07`。

## 16. B07WFR4WJ4／原行 13890

> Zatarain's Red Bean Seasoning, 2.4 oz (Pack of 12)

- 旧理由：`field_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：真实字段冲突或关键定位歧义；拟议成分状态：`unresolved`。
- 依据、反证与未知：售卖 Red Bean Seasoning，Just add red beans／serve over rice 为用途；Seasoned Rice 类别与调料身份确有差异，同时保留明确 A 外调料证据。
- 原始行 SHA-256：`f2839e48eaea4dafd9be7ec79926efe416a676818bce80493e567a236ad03404`。

## 17. B07CVXGQN4／原行 27947

> Manna Millets 5.5 lb - Natural Grains | Hulled Millet | Foxtail, Kodo, Little, Barnyard, Proso (Each 1.1 Pounds) | Finest Gluten-Free Whole Grain, Source of Protein, Low Carb, High Fiber & Diabetic Friendly | Alternative to Rice and Quinoa |

- 旧理由：`category_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Foxtail、Kodo、Little、Barnyard、Proso 五种 millet 组合。上位 millet 不代表同一粮种；分别包装也不是 A 内单粮种父商品。
- 原始行 SHA-256：`06b23dbf9e1845a7c35c8fd22d865d3cccaf5dae60f79e813d9df165f467a993`。

## 18. B09H3TZL9L／原行 29206

> Wira Brand Ragi Tempeh (Tempeh Starter) - 17.6oz (Pack of 1), 1.1 Pound (Pack of 1)

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Ragi Tempeh 是发酵 starter，原文列微生物孢子和米粉载体，不是 finger millet 原粮。不能盲目套 ragi 别名。
- 原始行 SHA-256：`1cee5c9aff023b9be04dff5aa39933fafdab0167bbcc61b1017893426e027959`。

## 19. B00JM1DP32／原行 33250

> GERBS Brown Teff Grain, 64 ounce Bag, Top 14 Food Allergen Free, Non GMO, Vegan, Keto, Paleo Friendly

- 旧理由：`category_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：真实字段冲突或关键定位歧义；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Brown Teff Grain 与 Buckwheat 类别直接矛盾；features／description 均空。不能静默选标题或类别覆盖反证，仍需裁决。
- 原始行 SHA-256：`9f0293540061198de07a4d29adb31796837611f6b372b0072627237c50492197`。

## 20. B0BWMCLXRL／原行 37450

> Rani Poha (Powa) Extra Thick Dagadi-Cut (Flattened Rice) 64oz (4lbs) 1.81kg Bulk~ All Natural, Salt-Free | Vegan | No Colors | Gluten Friendly | Indian Origin

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：真实字段冲突或关键定位歧义；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Poha／Flattened Rice 片状标题与 features 的 Food Grade Flour 矛盾；没有额外证据可把该句当作模板错误删除。保持待裁决。
- 原始行 SHA-256：`5e2134b1afdb37804ef4519e6ffa2b1bab8e4f0f783d7dbb482d0c1733a18a25`。

## 21. B09LPKJFSH／原行 45260

> Sour Cream Powder by Hoosier Hill Farm, 2LB (Pack of 1)

- 旧理由：`weak_identity`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：Sour Cream Powder；wheat products 是同设施警告，所售为乳品粉非 A。基料宣传没有给出完整粉末组成。
- 原始行 SHA-256：`b3f0ece3da72a5e6aaafd496ac5b794feff6a5cae2f3009cda5bad25c2c03ed8`。

## 22. B0BR1CCPC3／原行 83211

> Ramaroma Desi Bajra/Bajri (बाजरी), Kambu, Gluten Free Pearl Millet, Indian Millet, Whole Grain, Chemical Free, All Natural No Mixture, Indian Origin, NON-GMO, Vegan, Organic Bajra Grain 32oz (907g)

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：真实字段冲突或关键定位歧义；拟议成分状态：`unresolved`。
- 依据、反证与未知：Pearl Millet Whole Grain 有食用菜谱，也宣称 Bird Seed and Feed。粮种可识别，但食用／饲料定位存在须裁决的反证；All Natural No Mixture 不补出完整配方和真实食用等级。
- 原始行 SHA-256：`3197e5b61ec72625496d694f677cf123f4494964bc27c944dcc133023ac2a08a`。

## 23. B00ITTYJG0／原行 103805

> Pure Living Liv Organic Sprouted Buckwheat Flour - 24 oz

- 旧理由：`category_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：真实字段冲突或关键定位歧义；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Sprouted Buckwheat Flour 与 Wheat Flours & Meals 类别实质冲突；同时已有 A 外伪谷物和粉类证据。Item Form Raw 不把粉变成原粒。
- 原始行 SHA-256：`ba9ff48e781c9c306334dc8b412342318656840c79ce2b6175d3fd90e5172a44`。

## 24. B087C4WM17／原行 110043

> Bliss Tree - Raw Barnyard Millet - 4lb

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：可核实的别名、文本或类别层级解释遗漏；拟议成分状态：`declared_single_grain`。
- 依据、反证与未知：Ingredients: Pearled Raw Barnyard Millet 明确声称单一来源组成和脱壳颗粒；Barnyard／Raw 修饰词及非前缀形态被现有解析挡住。药效宣传和筛选机器宣传不能充当核验事实。
- 原始行 SHA-256：`78f870c862c153b460aaf39f0abd364b855506033ddaa996fdab3d680d4300dc`。

## 25. B07PXBNL92／原行 121281

> Nateavia Matcha Genmaicha - Organic Japanese fine sencha leaves, toasted brown rice and Matcha - Creamy taste - Authentic Japanese Origin - 80g

- 旧理由：`category_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Genmaicha／Matcha 茶饮，来源给出 green tea、roasted rice、matcha；文本和茶类别相容。冲泡时加糖、蜂蜜是用途，不能改写配料。
- 原始行 SHA-256：`93f3156f909abe788cf29d99f2988bde9276b2c43e58919bcac4404dcde2926c`。

## 26. B00KA8R6I6／原行 134969

> Rice Select Royal Blend, Whole Grain Texmati Brown & Wild Rice with Soft Wheat & Rye Berries, 28-Ounce Jars (Pack of 4)

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Royal Blend 明列 rice、soft wheat、rye berries；无需等待 Ingredients 才能识别多个粮种。完整比例未知。
- 原始行 SHA-256：`43acaa9874a2974b0402b51a1040e8f822297e254fc3858edc9ffa2497f2fd30`。

## 27. B00INBVK5C／原行 136737

> Perky's Crunchy Flax Cereal (Pack of 4)

- 旧理由：`weak_identity`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Crunchy Flax Cereal，由 fruit juice／honey 甜味处理，类别 granola；No Wheat 为否定，非小麦原粮。完整配方仍未知。
- 原始行 SHA-256：`c9c7726773e3314c6ee291e3dbe3d39ed2e0d3a8ab3d0451c57cf884a98dfa33`。

## 28. B0019L8I58／原行 140996

> Gold Mine Hato Mugi (Job'S Tears) - Heirloom Quality - Macrobiotic, Vegan, Raw, Kosher and Gluten-Free - 2.2 Lbs

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：可核实的别名、文本或类别层级解释遗漏；拟议成分状态：`declared_single_grain`。
- 依据、反证与未知：Hato Mugi (Job's Tears)，INGREDIENTS: HATO MUGI；完整原文说明 ancient whole grain。Hato Mugi 别名和非前缀形态遗漏，brown rice 是搭配用途；来源声明不等于真实配方已核验。
- 原始行 SHA-256：`e15bc8576ce39c805c24f06de135f5b5b046ec0dd8d3a15290336e94ed6e5075`。

## 29. B00CQRIVX8／原行 168099

> Jelly Belly, Sport Beans Extreme Assorted 1 oz, 24 Bags

- 旧理由：`field_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：Sport Beans 是含咖啡因、维生素等的糖果，Item Form Jelly／糖果类别相容；beans 不是售卖豆粮或真实谷物冲突。
- 原始行 SHA-256：`d8a24333eee6376a3bc88dab3cee9965788545dcb0f9c712d1d9a9c8bfe8c8ac`。

## 30. B00355CC1M／原行 187574

> Marsden & Bathe Amaretto Flavor--2 ounces

- 旧理由：`field_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Amaretto Flavor 为瓶装香精，原文有非谷物配料列表；cookies／cakes 是用途，wheat traces 是设备警告。
- 原始行 SHA-256：`8b1efc503f7b38a5e0ccf6a8ce718211a654bbd84a015fd0423285f7493a8b32`。

## 31. B07D6SRT34／原行 204242

> BOBOS OAT BARS Blueberry Lemon Poppyseed Toaster, 2.5 OZ

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：Oat Bars／Blueberry Lemon Poppyseed Toaster 为 baked goods／toaster pastry；非原粮，完整成分未知。
- 原始行 SHA-256：`3d99fc037787e331224ebfb76f8fdfebd47efa9a191cdc48e0c7029ad8be4f09`。

## 32. B0040PSQFW／原行 315995

> Libby's Gourmet Whole Kernel White Corn, 15 oz. Cans (Pack of 12)

- 旧理由：`category_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Whole Kernel White Corn Cans；描述明确 canned vegetables，非干玉米原粒。品牌其他蔬菜不是本品配料，完整配方未知。
- 原始行 SHA-256：`6fa2909acfa90965b958f6f778561371f13c8ac5b0690fd798aebe450937b94a`。

## 33. B08LCK7VRG／原行 337476

> AoNori Goma Furikake Rice Seasoning (No Salt, No MSG, Gluten Free), 1.76 Ounces, Product of Japan

- 旧理由：`unresolved_composition`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：Furikake Rice Seasoning，Ingredients: Sesame seeds, Seaweed；steamed rice／noodles 是使用对象。非未解析的稻米配方。
- 原始行 SHA-256：`9a38c1b4c2ec571ef24c8515f81f7224fdad2b2bb41fa333fc664f34b33cdf64`。

## 34. B008040JWM／原行 401209

> Oasis Supply Sugar Decorations, Lady-Bugs, 12 Count

- 旧理由：`field_form_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`unresolved`。
- 依据、反证与未知：Sugar Decorations 为糖制瓢虫装饰，含颜色及蛋白陈述；free of Wheat 等是否定，不是小麦身份冲突。
- 原始行 SHA-256：`ce4fc66c13920f0c84079c58af6beeda13f5daf2141721a43eb296de775b4490`。

## 35. B005Y2BNPK／原行 441959

> Kim Chee Fried Rice Sauce (pkg)

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Kim Chee Fried Rice Sauce；所售 sauce，Rice 是用途修饰。features／description 空，不能取消 missing_composition 后直接纳入米粒。
- 原始行 SHA-256：`fb87223636bcf14da83f3895051b0cca634d6666d4f131eb9199507206da52b5`。

## 36. B00GO8T49A／原行 496514

> Jelly Belly Gourmet Candy Corn - 2 Bags of 25 Packs

- 旧理由：`category_identity_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Candy Corn 是糖果名称，类别 Jelly Beans 与对象相容；不把 Corn／Beans 当作所售粮种，也不假定糖果真实配方无玉米。
- 原始行 SHA-256：`1e015b5a91650dedc88aa51034f6fcd2a79367ad41b88921be636a728d18e452`。

## 37. B077HTZ3WL／原行 498068

> Local Hive from L.R Rice, Raw Honey, Pure and Unfiltered, Amber, 16oz

- 旧理由：`composition_declaration_conflict`，仍保持原正式 pending。
- 拟议主分组：明确 A 外售卖对象、混合或成品；拟议成分状态：`declared_outside_scope`。
- 依据、反证与未知：L.R Rice Raw Honey；Rice 为家族／品牌，原文 Great Grandpa Rice／Rice's Honey, LLC 交叉说明。100% honey 的来源声称不构成真实米／蜂蜜配方冲突。
- 原始行 SHA-256：`8b1948aad6b9e015a702adb93d33f39e04b985c9c2d87400005f26852cd58aab`。

## 38. B083F7F9FT／原行 505091

> Mahatma Parboiled Medium Grain Rice ~ 16 oz

- 旧理由：`ambiguous_processing_or_mix`，仍保持原正式 pending。
- 拟议主分组：证据不足或尚未解决的加工边界；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Parboiled Medium Grain Rice 身份清楚，但批准草案对造成歧义的预处理保留待裁决。paella 为用途；不静默批准预处理边界或称它为熟制即食米。
- 原始行 SHA-256：`57526a2039d18b0a81b86e2f74330a60a5819dfb469277d56bcd4fd9928ae890`。

## 39. B08L737QS1／原行 533306

> Bakery On Main Organic Oats & Happiness Almond & Vanilla 12’s

- 旧理由：`form_not_verified`，仍保持原正式 pending。
- 拟议主分组：证据不足或尚未解决的加工边界；拟议成分状态：`unresolved`。
- 依据、反证与未知：Oats & Happiness Almond & Vanilla；features／description／categories 空，只剩口味或配料线索，形态不明。不得补成纯燕麦干片。
- 原始行 SHA-256：`b1721bf80cfc11ae68fdefffd387f0285d564f76f207fcf03fce1cc37c923e6d`。

## 40. B086KYRW35／原行 538370

> 100% Italian Arborio Rice Vacuumed Packed 2.2 Lb Chef Selection | Perfect Rice For Risotto | Recipe Included For Easy Preparation | Risotto Rice (Pack of 1)

- 旧理由：`unresolved_composition`，仍保持原正式 pending。
- 拟议主分组：证据不足或尚未解决的加工边界；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Arborio Rice 身份明确，100% Italian 指来源，For Risotto 指用途。其余自由文本空，包装和重量不能独立确认 dry／uncooked；形态及成分证据仍不足。
- 原始行 SHA-256：`72bcfc7b5f25daca682289bcae35b3f38d0c5c309c9e5740520dd685d924d38f`。

## 41. B07K6THHFC／原行 561586

> Blue Elephant Royal Thai Cuisine, Thai Premium Jasmine Rice, All-Natural, Gluten Free, 17.6oz

- 旧理由：`missing_composition`，仍保持原正式 pending。
- 拟议主分组：身份和 A 内形态明确，完整成分未披露；拟议成分状态：`not_disclosed`。
- 依据、反证与未知：Jasmine Rice，features 明确 Contains 17.6 oz of uncooked rice；咖喱是配餐用途。粮种形态明确、完整配料未披露，泰国产推广不是真实产地核验。
- 原始行 SHA-256：`3abe86fdf0884d94e56580b79210b993d83a88772088fcd13786aa178a8798af`。

