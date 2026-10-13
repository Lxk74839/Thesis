# grain-A-1.1.14 的全源对账与语义拒绝

603,274行完整gzip EOF、数量1536入／568223排／33515待裁决、逐商品迁移、原文引用及摘要独立核查通过。新分层抽核74条中73条与此前已读原文完全一致，新出现B0166MGHL6／264040明确写Spiced and Infused Popcorn／Chipotle Taco及本品香料组成，原自动判定漏掉该反证。因此拒绝1.1.14，未运行评论提取。

随后只针对入选元数据中的调味、即食和有关售卖对象线索开展定向补查，读取全部75条记录的标题、类别、features、description和details。不是概率抽样，不估计总体错误率；关键词仅用于发现，最终结论来自完整售卖对象及本品字段。

独立结论：[逐商品复核记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/sales-source-review-1.1.14.json)：38个明确A外售卖对象／实际添加或非单纯谷物套装，4个反证未解待裁决，33个保留谷物对照。明确A外例子包括玉米卷／tamales、调味料、肉棒、面包三明治、酒类、香料、实际奶酪／水果／香料添加及谷物附带调料套装。相反，Spicy World品牌、Caramel Type干玉米粒、烹调建议、天然风味和可选涂层不成为实际调味证据。

4个待裁决对象：B00DUW76HU（Microwaveable Kettle Korn且形态来自品牌故事）、B07RY2FFBJ（Kettle Corn甜咸酥脆售卖描述未明确A干粒形态）、B07QJVMD96（Mushroom kernels／Unpopped与Flavor Caramel未解）、B01A5KVADK（燕麦片标题与cheddar-cheese商品feature未解）。不猜测具体真实配方或加工史。

逐商品纠正绑定完整元数据的规范JSON SHA-256，保存来源行号、全部相关原文及结论。仅允许排除或待裁决，不强制入选；任何完整元数据变化重新待裁决。采用规格已经允许的“人工／代理裁决须记录依据并纳入协议版本”，不扩大A范围，不按评论热度决定去留，不改变06研究参数。明确添加声明只标来源声称A外组成，疑义声明保持未决。

另确认两个保留的Bob's Red Mill干玉米粒来源明确说本袋single-ingredient：B07T6BRNVN／168049及B001BKU4GS／479772。仅修正来源披露状态，不将其转换为真实配方已验证；食谱和单独无添加宣传仍不构成完整声明。

配置、目录记录、四份数据、独立QA、分层样本及75条线索原文共9个组件的摘要保存于grain-A-1.1.14-rejection.json。独立下一版1.1.15保留所有历史产物及原稿；其全量目录和评论仍待实际验收。
