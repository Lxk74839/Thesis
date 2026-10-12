# 工单 04：正式入选逐商品语义复核

2026-10-12，依据原始元数据本体、成分及形态复核全部 13 个自动入选对象。未使用评论、评分、热度或旧目录决定商品去留；本表是验收核查，不是筛选白名单。来源为工单 02 完整快照 `ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`，正式规则 grain-A-1.0.6。

| parent_asin | 原始行 | 售卖形态与成分依据 | 结论 |
| --- | ---: | --- | --- |
| B09S5HJV3W | 3391 | Yellow Corn Grits；features[3] 为 Ingredients: Corn | 干制玉米碎粒，符合 A |
| B01BCJ2M0S | 91104 | Matta Broken Rice；features[3] 为 Ingredients: Rice | 碎稻米，符合 A |
| B0B53M8WS2 | 155547 | Calrose Rice；features[2] 为 INGREDIENTS - milled rice | 碾米颗粒，符合 A |
| B089N9636M | 186797 | Calrose Brown Rice；features[2] 为 Ingredients: Brown rice. | 糙稻米，符合 A |
| B0014GZCQQ | 250435 | Carnaroli Long Grain Rice；features[0] 明确 Contains only carnaroli long grain rice | 单一稻米，多包装仍符合 A |
| B005HVDZS6 | 257226 | Jasmine Rice；description[0] 首句 100% Jasmine Rice，后文明确 dry Jasmine rice 的加水烹调说明 | 是需烹调的干米；标题 Microwaveable 指烹调方式，未证明是即食熟饭，符合 A |
| B00CQAYHQ0 | 259071 | Basmati White Rice；features[3] 为 Ingredients: Basmati Rice | 单一稻米，符合 A |
| B01K9F6QQ2 | 381172 | Organic Spelt Berries；features[4] 为 Ingredients: Organic Spelt Wheat | 斯佩尔特小麦粒，符合 A |
| B0078DQPZG | 412956 | Basmati White Rice；features[3] 为 Ingredients: Basmati Rice | 单一稻米，符合 A |
| B0861CPXR2 | 501711 | Jasmine Rice；description[0] 为 Ingredient: jasmine rice | 单一稻米，多包装仍符合 A |
| B00CYV2DV2 | 149283 | Organic Kamut Flakes；description[0] 尾部 Ingredients: Organic Rolled Kamut (wheat) Grain | 卡姆小麦压片，明确加水煮制说明；配餐／食谱及共线设备过敏原说明不是额外配料，符合 A |
| B005IPSNMY | 193824 | Yellow Popcorn Kernels、Unpopped 类别；description[0] 后段 INGREDIENTS: Yellow Popcorn | 密封罐包装的未爆玉米粒，Ready to Make 而非即食爆米花，符合 A |
| B07CGS1MRR | 309415 | Calrose Rice；description[0] 中段 Ingredients: Milled Rice，details.Item Form 为 Grain | 需加水烹调的碾米颗粒，多包装仍符合 A |

预发布 1.0.0 的品质百分比错误已通过真实记录定位并转成公共入口回归夹具，该版本拒绝验收。`100% whole grain`、`100% Organic` 等不足以穷尽配方，不作为单一成分的充分依据。食品熟制／混合等关键身份与类别矛盾继续隔离；标题外的用途说明不直接当作售卖食品。

其余待裁决对象保留完整原始对象和来源引用，本轮没有宣称全部完成独立语义裁决。独立程序只复核逐行对账、证据原文、来源定位、全部入选对象及摘要，不导入生产筛选器；不能把它称作所有 603,274 个对象的独立人工分类。

第二轮修复从全字段逐句发现明确成分声明，以上四个后段成分商品因此新入选。B00CYV2DV2 描述首段有 Peanut Butter Bars 食谱标题，但完整上下文持续说明干制 Kamut flakes 的烹调、配餐与使用方法，并在结尾明确单一成分；这里对首段的食谱用途解释属于基于上下文的判断，不是额外配料证据。全部新增对象再次只读检查原始身份、成分、类别及反证后记录，未查看评论数量来裁决。

第二轮 Spec 复审纠正 B001QHAJES：标题与成分为大麦，末级类别为 Oatmeal，属于未解决的身份／类别矛盾。1.0.3 的语义核查遗漏该反证；1.0.4 保存原始矛盾并转入待裁决，不再纳入正式目录。其余三个后段成分新入选对象按原始上下文复核，以上表格为当前正式入选集合。

1.0.5 完整处理 features／description 的成分续行及未知后句，明确烹调／储存说明才终止当前声明，后续新声明仍被核查。完整来源重跑后入选集合仍为以上 13 个，所有证据原文及计数重新独立核对。

1.0.6 保留专用成分字段中无标记续行的配料列表关系；同分组多组件不能当作重复完整声明。全量重跑的 13 个入选对象未改变，未读取评论量或模型表现。
