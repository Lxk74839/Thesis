# grain-A-1.1.13 全源后的语义抽核拒绝

完整603,274行扫描至gzip EOF，1538入选／568190排除／33546待裁决，逐商品迁移与原文引用独立对账通过。根代理逐批阅读了该版语义样本全部75条完整标题、类别、features、description及details：62条按粮种分层的成分未知商品与全部13条来源单粮种声明。该确定性样本不估计总体错误率，也不代表全部商品经过人工裁决。

发现两处有原文依据的错误：

| 父商品／源行 | 原文证据 | 错误及处理 |
|---|---|---|
| B07Z5HBY2J／497683 | 标题“Deiman Artificial Food Flavoring Corn Arte pan (4 fl.oz.)”；描述“STORAGE Original container tightly capped, in a cool, dry place” | 售卖对象为玉米香精，属于A外对象；储存说明的dry还被误用为售卖形态。应排除香精，储存说明不得补出谷物形态。 |
| B00PIOZCKQ／375351 | 标题“Organic Hulled Millet Grain … Little Millet Rice”；features“GREAT FOR VEGAN: Our organic barley is great to add to any vegan or vegetarian meal” | 功能标题后的本商品barley声明被用途边界隐藏，导致漏记与millet的关键身份冲突。应保留双方原文并待裁决，不猜测哪一字段真实。 |

其余73条未发现明确偏离已确认A范围及证据规则的事项。完整配料未披露、自然风味、用于烹调以及未经独立核验的属性声明不被补造为真实成分、实际熟制或供应链事实。

1.1.13拒绝验收，未运行其评论提取。配置、目录记录、catalog／audit／migration／pending、独立check及原文样本共8组件的SHA-256保存在grain-A-1.1.13-rejection.json；历史产物不覆盖。独立候选1.1.14仅修复上述售卖对象、储存与功能标题边界，工单06参数仍待确认。
