# 方案 A 商品范围与正式目录

2026-10-12，用户确认方案 A 及身份／成分证据、排除、待裁决与元数据冲突原则。规格正文已确认，未决规则与参数尚未冻结；这里只确定 D1 和 D3 的元数据冲突子项。评论清洗、时间截断、用户资格、模型字段白名单与样本充分性仍未冻结。

## 范围协议

可版本管理的配置为 [grain-A-v1.json](C:/Users/Kane/Documents/CodexProject/Thesis/config/grain-A-v1.json)，规则版本 **grain-A-1.0.3**，SHA-256 `48ee8f469e4d09b4d77b47626fa59c9af25121334af6d8f4b73732216c6b6b31`。范围是真谷物原粮及未调味干制初加工颗粒／片；普通同粮种多包装保留。粉、伪谷物、豆类、明确复合食品、熟饭、即食成品、零食、面包面条、饮品、提取物、饲料与种植种子不入选。

粮种分组包含 rice、wheat、barley、oats、rye、corn、millet、sorghum、teff、fonio、triticale、coix；分组名称不证明混合配料属于单一粮种或品种。名称使用及真／伪谷物边界依据 [USDA SR28](https://www.ars.usda.gov/ARSUserFiles/80400535/Data/SR/sr28/sr28_doc.pdf#page=87)；bajra、ragi、jowar 对应关系由 [FAO 粮种说明](https://www.fao.org/4/T0818e/T0818E01.htm)核查，fonio、teff 与 Job’s tears 亦见 [FAO 粟类说明](https://www.fao.org/millets-2023/about/)。FAO 的较宽统计范围不替代用户批准的 A。

关键词只用于发现线索。入选必须有可定位的售卖对象、形态和完整单粮种成分证据，并且没有未解决反证。明确的 Ingredients／contains only／纯谷物完整声明可以提供依据；`100% whole grain`、`100% Organic` 等品质陈述不能证明配方完整。用途、配餐与否定词不代替商品身份。类别仅为辅助线索；单独类别、poha／jasmine 等歧义名称、未知成分、预处理／营养强化、同分组多组件或字段矛盾保留待裁决。

完全重复父商品对象合并引用；非相同父商品对象全部隔离，不按评论数、评分或文件顺序挑一个。先完整发现父商品冲突，再分类，所以后段冲突不会留下早段入选副本。来源对象不改写。每行均保存原始行号、SHA-256、规则版本、理由，以及发现、身份、形态、成分或反证的字段原文；待裁决集合保留完整对象。

## 完整扫描结果

输入为完整元数据，SHA-256 `ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`。两次读取均到 gzip EOF；与来源记录核对 **603,274 行／父商品**，父商品重复与冲突均为 0。

| 决定 | 父商品数 |
| --- | ---: |
| 正式入选 | **14** |
| 排除 | **547,604** |
| 待裁决 | **55,656** |
| 合计 | **603,274** |

排除中 318,393 个是“未找到范围证据”，不能说已经证明全部不属于禾本科。互斥主理由完整分布见版本记录，弱身份、缺失成分、未知成分、形态未核实、加工／混合歧义、类别及字段矛盾均保留待裁决；全部证据在原始引用中保留。

1.0.0、1.0.1 和 1.0.2 均标记 rejected_pre_release，不用于后续提取。前两版曾误用品质百分比或漏记歧义线索；第三版在 Spec 审查发现同字段后段声明和否定／范围外身份处理不充分。1.0.3 逐句检查成分与明确身份，矛盾声明保留待裁决，烹调或配餐说明仍不充当商品成分。修正及全部 14 个入选对象的语义复核仅依据元数据，没有使用评论数量或模型表现。

完整机械候选 A 5,372 是旧诊断的线索数，不是入选数量。逐父商品交叉表和理由分布见 [独立对账](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/catalog-04-check.json)：旧候选中入选 12、待裁决 5,175、排除 185；另有 2 个不在旧机械集合中、但在完整来源中具备明确成分与形态的对象入选，总数为 14。主要差异是成分缺失、加工／混合歧义、形态未明与矛盾，另有零食等误命中。全部入选对象另作 [逐商品语义复核](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/catalog-04-semantic.md)。未知商品没有因样本不足被补入。

## 产物与复现

[目录摘要及版本记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/catalog/grain-A-1.0.3.json)保存输入、规则及生成器摘要，生成时间，目录、全量行级审计和待裁决集合的相对路径与 SHA-256。它们均在 Git 排除的 data/catalog/grain-A-1.0.3/ 下：

- catalog.jsonl：14 个入选父商品、原始对象和全部来源引用；SHA-256 `aa438781459c6794f2fe24d3cef94d8f251101c097f85e0f9ebd573cebe1c9c1`。
- audit.jsonl：603,274 行逐商品决定；SHA-256 `ccb1e9388eb67122cd168719c4ef3c46deb18a20a51f63a4fdec9d619d55bbdc`。
- pending.jsonl：55,656 个待裁决原始对象；SHA-256 `d02336ffa545aaf77fb3477e7c2d44f2135ce1b8ca1259a7cb65a7d2bb8ef0e4`。

```powershell
$env:TMP = 'C:\Users\Kane\Documents\CodexProject\Thesis\.tmp'
$env:TEMP = $env:TMP
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage catalog --metadata-record records/sources/amazon-2023-grocery-metadata.json --scope-config config/grain-A-v1.json --output-root .
```

同一版本改变来源或规则时拒绝覆盖，必须使用新版本；相同输入产物摘要可复现。独立检查不导入生产筛选器，逐行核对对象、原文位置、摘要和候选去向，另校验 26 份原材料及已确认规格。程序对账不等同于 603,274 个对象全部人工裁决。

没有评论的商品仍由相同规则保留，公共入口末尾夹具明确验证 rating_number 为 0 的商品入选。实际无评论数量在工单 05 通过完整评论源核对；目录阶段不读取评论源。当前目录原始自由文本与采集时聚合字段未作为模型输入发布，正式联合包与样本充分性尚未验收。
