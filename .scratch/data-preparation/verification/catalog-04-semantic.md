# 工单 04：正式入选逐商品语义复核

2026-10-12，依据原始元数据本体、成分及形态复核全部 10 个自动入选对象。未使用评论、评分、热度或旧目录决定商品去留；本表是验收核查，不是筛选白名单。来源为工单 02 完整快照 `ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`，正式规则 grain-A-1.0.2。

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

预发布 1.0.0 的品质百分比错误已通过真实记录定位并转成公共入口回归夹具，该版本拒绝验收。`100% whole grain`、`100% Organic` 等不足以穷尽配方，不作为单一成分的充分依据。食品熟制／混合等关键身份与类别矛盾继续隔离；标题外的用途说明不直接当作售卖食品。

其余待裁决对象保留完整原始对象和来源引用，本轮没有宣称全部完成独立语义裁决。独立程序只复核逐行对账、证据原文、来源定位、全部入选对象及摘要，不导入生产筛选器；不能把它称作所有 603,274 个对象的独立人工分类。
