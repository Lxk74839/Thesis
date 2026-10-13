# grain-A-1.1.12 全源后的语义抽核拒绝

完整603,274行EOF、1530／568180／33564集合及逐商品迁移、原文引用独立对账通过；这不代表语义验收通过。根代理逐批阅读了data/diagnostics/grain-A-1.1.12-semantic-sample.json全部74条记录的标题、类别、features、description和details：各粮种成分未知集合按父商品SHA排序取最多5条，共61条，加全部13条来源单粮种声明。不是概率抽样，不估计总体误差率，也不宣称穷尽人工裁决。

发现3个明确的误入／缺少本品形态证据对象：

| 父商品／源行 | 原始证据 | 当前错误与应有处理 |
|---|---|---|
| B009SOYHEO／308010 | 标题Lemons Naturally Preserved；描述“Also great for preserved lemon martinis, stews, poultry dishes and couscous, rice and grain dishes.” | 配餐用途中的rice和grain被拼成谷物身份／形态。原售卖对象是腌柠檬，应按A外对象排除；配餐不提供粒状谷物证据。 |
| B000WG7SZC／113334 | 标题Bob's Red Mill Scottish Oatmeal；features说品牌“offers the widest diversity of whole grains”，以及“USDA guidelines recommend eating at least 3 servings of whole grains every day.” | 品牌产品线及通用膳食建议给出了whole grains词，没有说明本商品A内形态；其余本品字段未给出明确形态，保留待裁决，不推定真实是粉／碎粒。 |
| B07RY1P81L／267574 | 标题Fruit Rainbow Popcorn；描述“the flavors of grape, lemon, orange, blue raspberry and cherry in a light, crunchy coating.” | 直接本品水果风味涂层是A外调味证据，不需要先推造完整配料表；应排除，保留文字及来源声明边界。 |

其他71条未发现明确偏离已确认证据口径的事项；这不是全部1517个未知成分对象的逐个人工背书。诸如有原粮身份／片状／粒状声明而未披露完整配料的记录保持未知，不据外部猜测补造加工、配料或供应链事实。

grain-A-1.1.12拒绝验收，未运行其评论提取。config、catalog record、catalog／audit／migration／pending、独立check和完整语义样本共8个组件已在grain-A-1.1.12-rejection.json保存SHA-256；旧统计、原文和失败定位保留。下一候选为独立grain-A-1.1.13，仅修正已定位销售对象、用途、品牌／营养语义；A范围及工单06参数不变。
