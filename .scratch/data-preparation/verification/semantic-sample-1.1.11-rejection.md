# 1.1.11 全源后的元数据语义抽查与拒绝依据

1.1.11 已读到603,274行末尾；独立全源数量、迁移、870,774处字面引用和摘要对账通过。此成功只证明记录和来源的可追溯性，不证明每条语义判定正确。根代理按最终样本读取全部74条完整 title／categories／features／description／details，不读取评论数量、评分或模型效果；样本为各粮种成分未知入选中的最低父商品SHA最多5条，加所有13条来源单粮声明，非概率样本，不估计总体准确率。

四条实际元数据更正如下。全部原对象仍在 data/diagnostics/grain-A-1.1.11-semantic-sample.json，行号定位原始完整元数据；新的版本不得覆盖该文件。

| 父商品／原始行 | 原文及关键字段 | 1.1.11问题 | 新版预期及依据 |
|---|---|---|---|
| B00CR3TZHW／84482 | Nagatanien Otona-no-Furikake Dried Rice Seasoning；features Dried Rice Seasoning；Item Form Powder | 品名的连字符 no 被当英文否定，截掉售卖对象；随后 dried rice 误补身份 | excluded；本品是调味料，不能因米词和 dried 入选。否定词须是实际语言词，连字符专名片段不供否定 |
| B07577CSJC／193193 | Steel Cut Oats；Item Form Flaked | 只确认两方各有A内词，遗漏明确形态矛盾 | pending；钢切与片状两方原文保留，不选择一个字段覆盖另一个 |
| B076SGR756／140306 | White Corn Grits；Item Form Flaked | 同样遗漏碎粒／片状矛盾 | pending；保留关键形态冲突。真实用途或食谱中的另一形态不算售卖冲突 |
| B003I5A5IG／418644 | Heartland Bulgur Wheat；Bulgur wheat is made from whole grain wheat | generic whole grain 遮住有依据的预处理含义 | pending；按已确认的预处理歧义原则处理，不将名称补成真实批次加工已核实 |

USDA FAS《Grain: World Markets and Trade》2021年4月，第5页的 Global Bulgur Overview 将 bulgur 描述为经过蒸煮、干燥及破碎的小麦。这里只据官方术语解释元数据名称，保留预处理歧义，不声称实测该商品的真实加工或供应链。[实际打开的 USDA 原报告](https://esmis.nal.usda.gov/sites/default/release-files/zs25x844t/jw8286622/sn00bt098/grain.pdf)。NALT词条仅搜索结果可见、打开超时，不把它记为已完整读取的证据。

其余读取案例的售卖谷物及A内形态有直接原文依据，成分未知仍未知；完整单粮声明仅记来源声称。产地、认证、营养和健康宣传没有转成真实核验结果。此抽查不声称其他所有商品已人工裁决。

正式验收拒绝1.1.11，六组件摘要保存在 grain-A-1.1.11-rejection.json；目录、审计、迁移、待决、全源核查和全部旧配置均保留。独立新候选1.1.12按公共入口逐行为 RED→GREEN，继续固定两轴审查与全源重算。工单06研究规则未冻结。
