# 工单 04／05 补充诊断：证据门槛、名称与最小修订依据

日期：2026-10-12。状态：**研究事实核查与修订建议，尚未批准实施**。本记录采用 mattpocock-skills 的 research 技能，仅静态读取项目文件和官方／第一方资料，不执行项目代码、Conda 或测试，不修改正式配置、目录、评论提取结果、规格或原材料。数量来自已有验收记录，新增分层统计由本轮独立诊断提供。

## 1. 已批准文字与当前硬门槛的区别

| 依据 | 实际文字／行为 | 证据边界 |
| --- | --- | --- |
| [范围草案第 7 行](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/product-scope-proposal.md:7) | “单一真谷物原粮及未调味干制初加工颗粒／片”；明确列出混粮、调味、熟制等排除范围 | 明确批准研究对象边界；没有规定每条对象都必须出现完整 Ingredients 声明 |
| [草案第 25 行](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/product-scope-proposal.md:25) | 标题、描述、features、details 中明确陈述的商品身份／配料确定粮种和形态；categories 辅助 | 允许多种来源字段提供商品身份，不允许仅凭类别或关键词纳入 |
| [草案第 26–29 行起](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/product-scope-proposal.md:26) | “形态与成分保持可核实”；歧义待裁决，不自行假定成分；实质冲突隔离 | 支持保守处理未知，但没有明文把“商品身份可确认、配料未披露”与“商品身份不能确认”合为一个状态 |
| [配置第 39 行](C:/Users/Kane/Documents/CodexProject/Thesis/config/grain-A-v1.json:39) | `Identity/form and explicit complete single-grain composition declaration must agree, with no unresolved counter-evidence.` | 当前实现明确把完整单粮种声明设为统一入选条件；第 41 行规定未知成分待裁决 |
| [实现第 180 行](C:/Users/Kane/Documents/CodexProject/Thesis/catalog.py:180) | 前序判断通过后，无已识别声明即 `missing_composition`；存在未解析声明或粮种不一致即 `unresolved_composition`，最终才 `included` | 这是实现对“可核实”的更严格操作化，不应回溯声称用户单独批准过这个具体字段门槛 |

判断：严格门槛有保护未知信息的理由；但批准的对象边界与“必须具有完整配料披露”的数据可用性条件不是同一件事。当前没有充分依据称其必然违反原范围，也没有依据把它称为用户明文要求。调整证明负担应作为本轮待确认修订，保留旧版及旧验收。

依据读取时 Git HEAD 为 `fb5eff2d09bca20381529a5da5dac9c479a28acf`。范围草案 SHA-256 为 `334b2ac524fe6d8f3a90ec2b7cc66eb75d2e1aa9b32242733d4d7d9e7badd94a`；配置为 `6148cc25f327d81423aa6aef16708a1ed973b46a36a806e8e06fd9fca24816f9`；`catalog.py` 为 `477d1418ab4a5e75fbf089c8cb77807428d6e0d5ba8cf23252c7d90f914d2c15`；规格为 `2fa128e9a1d692468d56ad22035e25332573289be0e4d6f4c25821df0ed6f976`。

## 2. 门槛影响：已知数量及不能据此推出的结论

以下为 [grain-A-1.0.6 记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/catalog/grain-A-1.0.6.json)及[独立对账](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/catalog-04-check.json)中现有事实，主理由互斥，并非新的商品裁决。

| 现有主理由 | 全量商品数 | 旧机械 A 候选中商品数 | 含义 |
| --- | ---: | ---: | --- |
| `missing_composition` | 3,953 | 3,474 | 有粮种及形态线索、未命中前序反证后，被“未识别完整声明”门槛挡住 |
| `unresolved_composition` | 216 | 173 | 已识别成分文字，但有未解析部分或与身份不一致；不能直接改成成分已知 |
| `composition_declaration_conflict` | 53 | 45 | 多个声明的粮种集合不一致；必须保留冲突 |
| 正式入选 | 13 | 12 | 现有严格条件下入选；另外 1 个不在旧机械集合中 |
| 全部待裁决 | 56,209 | 5,175 | 还包括弱身份、形态、加工、类别与字段冲突，不可全归因于成分缺失 |

3,953 是当前控制流中直接进入成分缺失主理由的集合，不等于“3,953 个已证明单粮种、未调味、可立即纳入商品”。例如粮种尚未在细粒度上区分、多个粮种标题或隐含加工歧义仍需逐记录核查。旧机械候选的 3,474 也不等于修订后的入选增量。理由顺序会遮住次要问题，因此本轮分层应另外保存多重证据标记，并保留原主理由。

“字段没有披露配料”与“解析器漏掉已有配料”必须分开统计。当前解析器仅识别配置中的声明前缀，以及 `details.Ingredients`／`details.Ingredient` 两个专用键；未命中并不能证明所有原始字段都没有成分信息。见[配置第 34 行](C:/Users/Kane/Documents/CodexProject/Thesis/config/grain-A-v1.json:34)、[实现第 85 行](C:/Users/Kane/Documents/CodexProject/Thesis/catalog.py:85)。

## 3. 名称与形态的第一方核查

名称事实只帮助识别元数据所售对象，不证明任一 Amazon 商品的配方、食用用途或真实供应链。

| 名称 | 可证事实与来源 | 当前配置／推荐边界 |
| --- | --- | --- |
| `poha`、`Avalakki` | CSIR-CFTRI 的原研究摘要明确把两者用于 rice flakes；同时描述稻谷经处理压片的过程。[CFTRI 原研究记录](https://ir.cftri.res.in/6762/) | `poha` 目前只是发现词，并在 `ambiguous_forms` 中。建议把确认售卖的干米片与调味／即食 poha 分开；名称本身不证明无调味。官方另有由米片和其他原料制成的 ready mix，说明处理语境不能丢弃。[CFTRI 即食混合物技术](https://cftri.res.in/hweb1/technologies/CP/iti.pdf) |
| `jasmine rice` | USDA 的稻米类型表将 jasmine 与 basmati 列为芳香稻米。[USDA ERS 稻米说明](https://ers.usda.gov/topics/crops/rice/rice-sector-at-a-glance) | 配置已有 `rice`，因此完整短语 `jasmine rice` 并非完全漏识别；单独 `jasmine` 目前为发现词且仍可能多义。已确认元数据售卖稻米时可用完整名称映射，不由 jasmine 单词推断米、产地、品种纯度或认证 |
| `ragi`、`bajra`、`jowar` | FAO 表列 ragi 为 finger millet（Eleusine coracana），bajra 为 pearl millet（Pennisetum glaucum），jowar 为 sorghum（Sorghum bicolor）。[FAO 粮种与常用名称表](https://www.fao.org/4/T0818e/T0818E01.htm) | 当前均已配置，不能一概声称别名遗漏。但 ragi 与 bajra 是不同粮种，现配置合在 `millet` 一组；同现不能因为组数为 1 就证明单粮种。需保留细粒度身份及混粮线索，不把整个 millet 组当作同义词集合 |
| `job's tears`／`job’s tears`、`adlay`、`Coix` | Kew 接受 Coix lacryma-jobi，分类为 Poaceae；Kew 名称服务和 NLM 名称表把 Job's tears／adlay 关联至该对象。[Kew 植物分类](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:30100521-2)、[Kew 名称关联](https://mpns.science.kew.org/mpns-portal/drugDetail?drugName=job%27s+tears)、[NLM 名称表](https://meshb.nlm.nih.gov/record/ui?ui=D031742) | 当前直撇号在正式别名，曲撇号只在发现词；这是可以定位的文字变体差异，诊断应检查是否实际造成漏判。名称还可出现在药用、种植或其他用途记录中，不能仅凭植物身份纳入食用干颗粒范围；也不能将 `pearl barley` 自动全映射为 Coix |
| `dalia`／`daliya` | 印度食品加工部所属 NIFTEM 的 Dalia 材料描述碎小麦／粗碎谷粒；印度政府食谱也明确将 dalia 与 broken wheat 对应，并另列粥中的豆、奶等配料。[NIFTEM 处理材料第 7–8 页](https://niftem.ac.in/newsite/pmfme/wp-content/uploads/2022/07/daliaprocessing.pdf#page=7)、[政府 Dalia 食谱](https://goacivilsupplies.gov.in/wp-content/uploads/2025/10/Dalia-Porridge.pdf) | 当前未列这些词。建议先作为有依据的碎小麦发现线索；只有元数据明确售卖单一干碎小麦才能确认身份。不得把任何 dalia 粥、甜食、速食混合料都归入 A。NIFTEM 材料也有宽泛的名词和加工描述，不宜据此把 dalia、bulgur、couscous 当作完全可互换的同义词 |

CFTRI 也区分未食用的颗粒／片与由同粮种制成的零食、粉、饮品、调味片；例如 ragi 可以脱壳为颗粒，也可以加工成面条或饮品，jowar flakes 亦可以做调味即食零食。植物别名正确不会消除商品形态差别。[CFTRI 粮种加工技术](https://www.cftri.res.in/Millets/)

这里提出的是批准粮种内的名称及语义完善，不提出加入粉类、伪谷物、豆类、熟制或调味产品。

## 4. Amazon 元数据的能力边界

官方定义 `title` 为商品名，`features` 为项目式特征，`description` 为描述，`categories` 为层级类别，`details` 为包含材料、品牌、尺寸等的字典；没有单列必填、完整且已核验的食品配料字段。评论中的 `parent_asin` 应用来查找商品元数据，不能用变体 `asin` 冒充父商品或批次。[Amazon Reviews'23 官方字段说明](https://amazon-reviews-2023.github.io/main.html#data-fields)

官方说明数据于 2023 年收集，价格定义为抓取时的值；元数据字段表没有提供逐商品有效期或历史配方版本字段。**推断／限制：**无法仅凭这一元数据对象证明商品在每条评论发生时使用相同配方，也无法由来源字段定义证明商家陈述为实际真实成分或已核验供应链事实。全文获取、校验和完整扫描可证明本地文件完整，不能提高某条陈述的真实性等级。[Amazon Reviews'23 数据与字段说明](https://amazon-reviews-2023.github.io/main.html)

已有规格也明确“真实元数据中的商家陈述仍是来源陈述；它不会自动成为已核验供应链事实”。见[规格第 96 行](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/spec.md:96)。

## 5. 推荐的最小区分，供用户确认

以下是研究建议，**不是已冻结规则**。不新增真实事实、不扩大 A、不以评论或模型效果裁决商品。

| 层次 | 正向证据与状态 | 对未知及反证的处理 |
| --- | --- | --- |
| 商品身份／形态 | 保存元数据中直接说明所售粮种和 A 内干颗粒／片形态的原句及出处；区别售卖对象、用途、食谱、过敏原和否定。类别仅辅助。名称映射附上述第一方依据 | 身份可确认，不等于配方可确认。类别与正文、多个粮种、加工状态等关键矛盾未解时仍待裁决。没有反证不是正向证明；同族 millet 粮种不能塌缩为单一成分 |
| 成分披露 | 原完整声明可记为 `declared_single_grain`，明确表示“来源声称”，保留全文与关联位置；存在成分信息但无法完整解析记为 `unresolved`；完全未披露记为 `not_disclosed` | 不把 `not_disclosed` 改为单一配料、不写“无添加／未调味”真实事实。冲突、混粮、调味及熟制证据继续保留，能明确排除的按 A 排除；存在实质歧义仍待裁决 |
| 可用商品目录 | 建议将“售卖身份和 A 内形态明确，但成分未披露”的对象列为**身份已确认、成分未知**的独立状态，而非与身份不明混在一起；是否允许该状态进入下一版用于真实评论提取的目录，应由用户确认 | 这会调整证明负担，不能通过改名绕过确认。若进入目录，目录不能再被描述为“所有商品真实完整配方均证实单粮种”；严格完整声明子集保留可复核标记。若仍要求配方完整作统一准入条件，则继续保留当前门槛，并如实报告可用性局限 |
| 供应链声明核验 | SIM 批次与父商品相连；针对具体 SIM 声明检查材料是否绑定同一对象、权限、时间、版本、摘要、撤销及冲突；各项具体标准留在 D7 等相应工单确认 | 商品身份目录不是供应链合格集合。真实元数据缺失的配方、产地、检测、温控等不补造为真实事实。SIM 事实明确标记，仅评价受控模拟材料及声明；真实评论始终评价父商品 |

最小规则草案可以表达为：**商品身份和范围内形态的准入，与成分披露和声明核验状态分别记录；完整单粮种声明不再默认是每个身份目录条目的必要字段。实际混合／调味／熟制及未解决关键冲突仍按 A 处理。未知字段不被生成器补成真实属性，也不在核验中视为满足未知声明。**

为保护论文结论，若采用该修订，应同时明确：父商品目录是依据来源所售身份形成的研究目录，不能证明物理配方和真实供应链；严格声明子集可以做透明分层诊断，但不因评论数量决定保留谁。正常 SIM 场景仅能证明经批准模拟协议所需声明，不能用于“验证”未披露的真实配方。

## 6. 待确认事项与实施前验收建议

1. 是否采用上述身份目录／成分状态拆分，并允许身份明确、成分未知但无未解决范围反证的对象用于下一版全部评论提取。
2. poha／flattened 等词是否改为按“实际售卖干片”语义裁决，保留预处理、调味和即食反证；曲撇号、dalia 及确证别名只修正批准粮种内的发现与身份解析。
3. 是否把 millet 的已知不同粮种映射分别保留，避免把 ragi 与 bajra 混称同一粮种；不得因单一上位类别而忽略混粮。
4. 确认后以新版本执行公共入口 TDD、固定基线 Standards／Spec 审查、旧新目录逐商品迁移原因对账，再完整提取评论和重报用户历史覆盖。现有 `grain-A-1.0.6`、验收记录及原稿保留；D2–D12 未决参数不由本诊断冻结。

建议验收包括：每个身份已确认但成分未知对象保留全部来源、原文、反证及未知标记；混粮／调味／熟制／冲突夹具仍被阻断；曲撇号及字段解析修复不覆盖原对象；用户数、历史深度和独立样本充分性另报告，不从可能扩大的商品数量直接推断。实际增量与历史改善目前尚未重跑，不能填写预测为结果。

## 7. 20 个代表记录的完整文本静态语义核查

状态：**`proposed_only`，未改正式裁决**。于 2026-10-12 逐条读取了指定记录的完整 `title`、全部 `features`、全部 `description`、全部 `details` 与 `categories`，仅这些字段用于以下判断；没有使用评论数量、评分、价格、模型表现、图片或视频。所有自由文本均已读完，以下引文是依据摘录，不是将摘录当成完整记录。空数组／空对象也明确计入核查。

样本来源为 [representative-records.json](C:/Users/Kane/Documents/CodexProject/Thesis/data/diagnostics/usability-04-05-draft-01/representative-records.json)，SHA-256 `8d0f432fcff6699e50411524968a736950f5be7025c717f27d60b4abab7187a1`。原元数据 SHA-256 仍为 `ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`。样本文件保留每条完整元数据、全源行号和行摘要。B00GO8T49A 在请求中重复，仅计算一次，另核查 B0C1MM67QJ，共 **20 个唯一父商品**。

这 20 条来自完整 41 条代表集合：该集合由各旧理由首行、两条 SHA-256 排序样本及具名案例去重组成；并非这 20 条全部为 hash-selected。以下数量**仅描述这 20 条**，不能外推全部 56,209 条待裁决商品，也不能给出总体比例或修订后入选数量。为便于对账，每条指定一个互斥“主分组”；具有清楚类别矛盾且售卖对象也不在 A 的条目，主分组保留真实字段冲突，另外明确记录范围外证据。

| `proposed_only` 主分组 | 本样本数 | 父商品 |
| --- | ---: | --- |
| 身份形态明确、成分未知 | 1 | B07K6THHFC |
| 可核实解析／语义遗漏 | 1 | B0C1MM67QJ |
| 实际非 A 或混合／熟制商品 | 13 | B09LPKJFSH、B00INBVK5C、B00KA8R6I6、B07PXBNL92、B0040PSQFW、B00GO8T49A、B00CQRIVX8、B00355CC1M、B008040JWM、B077HTZ3WL、B005Y2BNPK、B07D6SRT34、B08LCK7VRG |
| 真实字段冲突 | 2 | B00ITTYJG0、B07WFR4WJ4 |
| 不足以判断 A 的准入 | 3 | B083F7F9FT、B08L737QS1、B086KYRW35 |
| 合计 | **20** | 不包括重复请求的额外计数 |

“不足以判断”包括商品身份已知、但 A 的干制形态或既有预处理约定未解除的情况，不等于每条商品名都无法识别。数量没有当作新的正式标签。

1. **B09LPKJFSH，原始第 45,260 行；原理由 `weak_identity`。** 标题为 `Sour Cream Powder by Hoosier Hill Farm, 2LB (Pack of 1)`；features 与描述重复明确 sour cream powder、加冷水复水、用于蘸酱／烘焙，类别为 `Condensed & Powdered Milk / Powdered`。商品身份为酸奶油粉，非 A。反证核查：`wheat products` 出现在同设施加工的过敏原警告中，不是所售小麦；`100% real sour cream` 陈述原料／品质，没有给出粉末的完整配料表。**成分状态：源声明基料为酸奶油并含 milk，完整配方未披露。主分组：实际非 A。**

2. **B00INBVK5C，第 136,737 行；`weak_identity`。** 标题为 `Perky's Crunchy Flax Cereal (Pack of 4)`，features 明确 `Sweetened with fruit juice and Honey`，类别为 `Muesli & Granola Cereals / Granola`。所售为甜味亚麻籽谷物成品，不是 A 内单粮种原粮或干片。描述 `Product contain No: Wheat, Dairy...` 是否定，不是小麦身份；`100% natural` 是品质宣传，不能当成完整单粮种声明。**成分状态：果汁、蜂蜜甜味配料已被来源提及，完整列表未知。主分组：实际非 A。**

3. **B00KA8R6I6，第 134,969 行；`ambiguous_processing_or_mix`。** 标题直接为 `Rice Select Royal Blend, Whole Grain Texmati Brown & Wild Rice with Soft Wheat & Rye Berries...`；features、description 空；details 的 Variety 也列 `Wheat,Rye Berries,Whole Grain`，类别为干粮米类。售卖米、小麦和黑麦混粮，包装数量不是混粮原因。**成分状态：多粮种售卖配方已明确，完整比例与全部配料未披露。主分组：实际混合非 A。** 无需借助评论或等到 Ingredients 字段才能识别这一明确排除证据。

4. **B083F7F9FT，第 505,091 行；`ambiguous_processing_or_mix`。** 标题为 `Mahatma Parboiled Medium Grain Rice ~ 16 oz`；features 空；完整描述说明选用 medium grain rice、用于 paella／Spanish recipes，类别为 `Dried Grains & Rice / White`。售卖中粒预处理米，做 paella 是用途，不证明包内已加配料或已制成 paella。0 cholesterol、gluten-free、fat-free、sodium-free 和 Non-GMO 等没有披露完整成分。**成分状态：未披露。主分组：不足以判断 A 的准入。** 原因是批准草案把造成歧义的加工预处理留待裁决；本核查不能静默批准 parboiled，也不能把它说成已熟制即食米或混粮。身份和颗粒形态有清楚来源依据，待解决的是加工边界和披露状态。

5. **B07PXBNL92，第 121,281 行；`category_form_conflict`。** 标题为 `Nateavia Matcha Genmaicha - Organic Japanese fine sencha leaves, toasted brown rice and Matcha...`；描述明确这是 green tea，并列 `Ingredients: Japanese Organic green tea, Japanese Organic roasted rice, and Japanese Organic matcha` 及冲泡 Directions；类别为 `Beverages / Tea / Green / Matcha`。文本和类别一致指向混合茶饮材料，属于非 A，不是真实 grain／tea 字段矛盾。`100% AUTHENTIC JAPANESE ORIGIN` 是来源宣传；`100% Pure`、认证、无添加甜味宣传不消除其本来多原料属性。冲泡时可加糖／蜂蜜是用途，也不应加到本品成分表。**成分状态：来源提供茶、米、抹茶配料声明。主分组：实际混合饮品非 A。**

6. **B0040PSQFW，第 315,995 行；`category_form_conflict`。** 标题为 `Libby's Gourmet Whole Kernel White Corn, 15 oz. Cans (Pack of 12)`；features 空；描述明言 `complete new line of extra-fancy canned vegetables` 和 `extra-special sweet corn`；类别为 `Canned, Jarred & Packaged Foods / Vegetables / Corn`。这是罐装蔬菜玉米，不是已证实干玉米原粒；标题中的 kernel 不能覆盖描述。仅凭罐装不能排除所有商品，但本条有明确 canned vegetables 身份。描述中其他蔬菜和品牌历史不是本品配料。**成分状态：玉米身份被说明，完整配料未披露。主分组：实际非 A。** 类别没有与这个商品身份矛盾。

7. **B00ITTYJG0，第 103,805 行；`category_identity_conflict`。** 标题为 `Pure Living Liv Organic Sprouted Buckwheat Flour - 24 oz`，描述再次明确 `Sprouted Whole Grain Buckwheat Flour`；details 的 `Item Form: Raw` 不会把 flour 变成原粒。类别末级却是 `Wheat Flours & Meals`，与 buckwheat 身份构成真实粮种矛盾；不是仅有关键词造成的冲突。**成分状态：完整配料未知。主分组：真实字段冲突。** 同时，明确售卖荞麦粉的正向身份本身已提供 A 外的伪谷物和粉类证据；保留该事实与类别反证，不静默把类别改成荞麦，也不写成正式排除裁决。

8. **B00GO8T49A，第 496,514 行；`category_identity_conflict`。** 标题为 `Jelly Belly Gourmet Candy Corn - 2 Bags of 25 Packs`；features 一贯说明 creamy vanilla Candy Corn、小袋糖果和聚会用途；details 的 Item Form 为 `Jelly`，类别为 `Candy & Chocolate / Jelly Beans`。所售是糖果，`Candy Corn` 不是售卖玉米干粒，`Jelly Beans` 也不是食用豆粮身份。类别和完整文本相容，原粮种冲突属于语义误读。**成分状态：完整列表未披露，不假定其一定无玉米原料。主分组：实际非 A。**

9. **B00CQRIVX8，第 168,099 行；`field_identity_conflict`。** 标题为 `Jelly Belly, Sport Beans Extreme Assorted 1 oz, 24 Bags`；首条 features 的 `This is a 24 count case... Sport Beans` 与完整描述所说 `jelly beans`、`candies`、caffeine、B/C vitamins、electrolytes 一致，类别为 `Candy & Chocolate / Jelly Beans`，Item Form 为 `Jelly`。`Beans` 在这里是糖果名称，不是另一粮种声明；没有可见的谷物身份冲突。**成分状态：部分功能配料被来源提及，完整列表未知。主分组：实际非 A。**

10. **B07WFR4WJ4，第 13,890 行；`field_identity_conflict`。** 标题为 `Zatarain's Red Bean Seasoning, 2.4 oz (Pack of 12)`；features、Product Description 指向 red pepper、garlic、natural smoke flavor 调料，并要求 `Just add red beans...serve over rice`。这说明售卖调料，而豆和米由使用者加入；品牌历史中的 rice dinner mixes／pasta 等不是本商品身份。类别却是 `Packaged Meals & Side Dishes / Rice Dishes / Seasoned Rice`，与调料包售卖对象存在真实类别不符。**成分状态：来源列出部分调料组成，完整列表未披露。主分组：真实字段冲突。** 同时记录 A 外调料身份；原 `field_identity_conflict` 不能解释为存在两个相互矛盾的谷物实体声明。

11. **B00355CC1M，第 187,574 行；`field_form_conflict`。** 标题为 `Marsden & Bathe Amaretto Flavor--2 ounces`；描述完整说明瓶装 professional grade flavor，并有 `Ingredients: Natural and artificial amaretto flavor, water, alcohol, propylene glycol, malic acid, citric acid, sodium bonzoate`。用于 cookies／cakes 是用途，may contain traces of wheat 是共用设备警告，不是所售谷物。`This is a professional grade flavor` 与整段描述一致，不能将后面的烘焙用途词转成 grain／糕点形态矛盾。**成分状态：来源提供非 A 配料列表。主分组：实际非 A。**

12. **B008040JWM，第 401,209 行；`field_form_conflict`。** 标题为 `Oasis Supply Sugar Decorations, Lady-Bugs, 12 Count`；features 与描述说明糖制装饰、食用颜色、egg whites；`This product is free of Gluten, Wheat, Milk...` 是否定粮种／过敏原，不是正向小麦／milk 身份。类别为 `Frosting, Icing & Decorations / Icing Decorations`，与售卖对象一致；free-of 列表不含 egg，故与 `Contains Egg Whites` 也不构成所列字段的直接矛盾。**成分状态：糖、颜色和蛋白被来源提及，完整列表未知。主分组：实际非 A。**

13. **B077HTZ3WL，第 498,068 行；`composition_declaration_conflict`。** 标题为 `Local Hive from L.R Rice, Raw Honey, Pure and Unfiltered, Amber, 16oz`；完整 features／description 均为蜂蜜；`Great Grandpa Rice`、`L.R Rice Local Hive`、Manufacturer `Rice's Honey, LLC` 交叉说明 Rice 在这些位置是家族／品牌名。`100% PURE`、`100% pure, 100% honey` 与蜂蜜身份不矛盾；营养、质量检验和慈善宣传不是成分，也不是已核验真实供应链材料。**成分状态：来源声称纯蜂蜜无增减，不是谷物配方声明。主分组：实际非 A。** 原声明冲突不应被当成米和蜂蜜两种真实原料的冲突。

14. **B005Y2BNPK，第 441,959 行；`missing_composition`。** 标题为 `Kim Chee Fried Rice Sauce (pkg)`，features、description 空；details 仅尺寸和 UPC；类别为 `Sauces, Gravies & Marinades / Sauces / Barbecue`。售卖对象是 sauce；`Fried Rice` 在该复合名称中说明酱料使用对象，不足以把所售酱料认成米粒。**成分状态：未披露。主分组：实际非 A。** 这是不能将全部 `missing_composition` 直接提升为 A 的具体反例。

15. **B07K6THHFC，第 561,586 行；`missing_composition`。** 标题为 `Blue Elephant Royal Thai Cuisine, Thai Premium Jasmine Rice, All-Natural, Gluten Free, 17.6oz`；features 明确 `Aromatic Thai Long Grain Rice`、`Contains 17.6 oz of uncooked rice`；类别为 `Dried Grains & Rice / Jasmine`。描述 pairing with curry sauces 是配餐用途，不表明本品已经混有咖喱；全部 fields 未发现完整配料表。**成分状态：未披露完整成分；All-Natural、gluten-free 不能填补。主分组：身份形态明确、成分未知。** 来源还声称泰国产，但这只是来源陈述，不能作为真实产地核验证明。

16. **B07D6SRT34，第 204,242 行；`form_not_verified`。** 标题为 `BOBOS OAT BARS Blueberry Lemon Poppyseed Toaster, 2.5 OZ`；features 明确 `On-The-Go Snack`、`Handmade Baked Goods`，描述说 toaster pastry，类别为 `Toaster Pastries`。完整文本足以识别烘焙零食，非 A；`Simple, Wholesome Organic Ingredients` 不是完整配料列表。**成分状态：口味／原料名有提及，完整列表未知。主分组：实际非 A。** 不能因标题有 oat 而退回“可能是原粮”。

17. **B08L737QS1，第 533,306 行；`form_not_verified`。** 标题为 `Bakery On Main Organic Oats & Happiness Almond & Vanilla 12’s`；features、description、categories 全空，details 只有尺寸和 UPC。可见 oats 和 almond／vanilla 口味或配料线索，但没有说明售卖形态；不能证明是原粮、干片、成品或纯谷物。**成分状态：未披露完整成分，有可能实质调味／混合的反证线索。主分组：不足以判断。** 保留待裁决，不以没有完整 Ingredients 反向猜测“单一未调味燕麦”，也不凭口味名称补造全部配方。

18. **B08LCK7VRG，第 337,476 行；`unresolved_composition`。** 标题为 `AoNori Goma Furikake Rice Seasoning (No Salt, No MSG, Gluten Free)...`；features 明确 `Use as topping for steamed rice, noodles...` 与 `Ingredients: Sesame seeds, Seaweed`，description 空、details 空；类别为 `Dried Seaweed & Nori`。售卖调料，不是大米；米、面条等是用途。成分列表不是未解析的稻米配方，而是该调料的来源声明；No salt／MSG 也不代表产品为纯米。**成分状态：来源提供芝麻与海藻列表。主分组：实际非 A。**

19. **B086KYRW35，第 538,370 行；`unresolved_composition`。** 完整标题为 `100% Italian Arborio Rice Vacuumed Packed 2.2 Lb Chef Selection | Perfect Rice For Risotto | Recipe Included For Easy Preparation | Risotto Rice (Pack of 1)`；features、description、categories 空，details 仅品牌、重量、尺寸、计量。`100% Italian` 修饰产地／来源，不是完整成分；`For Risotto` 和 recipe 是用途，不能证明包内为已调味 risotto。售卖 Arborio 稻米身份明确，但仅有真空包装／重量不能独立确认干粮还是预熟米。**成分状态：未披露，原 `unresolved_composition` 可能源于把标题百分比当成配料声明。主分组：不足以判断 A 的准入。** 保留形态和来源陈述的限制；不补写 dry、uncooked、无调味或真实意大利产地。

20. **B0C1MM67QJ，第 1,961 行；`category_identity_conflict`。** 标题为 `Aduna Organic Fonio Super-Grain... Single Resealable Pouch 1 x 2.2lb`；features 原句 `Nothing else is added, just 100% pure organic fonio grain. Prewashed...` 是明确售卖 fonio 及无其他添加的来源声明；`Cooks in 3 minutes...a great alternative rice, quinoa or couscous` 是食用准备及替代用途，不是多个粮种配方。类别末级 `Millet` 属上位名称：FAO 在同页将 fonio 列为其他 millets，故不能仅凭 `fonio` 与 `millet` 被配置成不同键就认定真实身份矛盾。[FAO 谷物说明](https://www.fao.org/4/T0818e/T0818E01.htm) **成分状态：来源明确声称仅有 fonio，未独立验证真实配方。主分组：可核实解析／语义遗漏。** 应修正声明语义和类别层级判定，而不是把未知当已知；USDA／Soil Association、农户关系等宣传仍不自动成为真实核验事实。

### 这 20 条对最小修订的具体要求

- 取消统一完整成分字段门槛之前，必须先正确识别售卖中心：Rice Sauce、Rice Seasoning、Candy Corn、Sport Beans、Rice 家族蜂蜜等不能进入谷物身份目录。
- 配方用途、烹调搭配、品牌历史、共用设备过敏原和 free-of 否定，要保留为原文及各自语义角色，不得拼成配料列表或谷物身份冲突。
- `100%` 必须看它修饰的是来源、品质、保证还是完整成分。Aduna 的明确“没有其他添加，仅 fonio”与 `100% Italian`、`100% natural`、`100% authentic Japanese origin` 不是同类证据。
- 类别冲突应比较层级与实际对象；Millet 可以是 fonio 的上位类，而 Wheat Flours & Meals 与明确 Buckwheat Flour 是实质差异。不能用配置键不同代替真实矛盾。
- 元数据不足时保留不足：没有自由文本的 almond／vanilla 燕麦条目，以及没有干粮状态说明的 Arborio 条目，不能因期望提高用户历史覆盖被升格。
- 以上均为修订建议和样本核查，不是新版本执行；没有重跑正式 04／05 或冻结工单 06 规则。
