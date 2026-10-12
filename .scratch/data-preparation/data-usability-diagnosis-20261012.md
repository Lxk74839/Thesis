# 工单 04／05：数据可用性补充诊断与修订建议

状态：**诊断已完成；建议供审核，未生成或生效新的正式规则。** 规格正文已确认，未决规则与参数尚未冻结。本轮不确认工单 06，不修改原稿、旧范围、旧目录、评论提取或验收记录。

核心发现：现行实现把“来源售卖身份／形态明确”和“具有完整单粮种组成声明”绑为同一准入条件。后者确实限制了可用性；同时，待裁决集合存在用途、品牌、过敏原、宣传和类别层级的误读。因此不建议直接放行所有缺成分声明的记录。推荐把身份准入、成分披露和供应链声明核验分别记录，修订正式执行必须先获确认。

## 对照批准范围与现行实现

[已批准 A 草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/product-scope-proposal.md)要求单一真谷物原粮／未调味干制初加工颗粒／片；以标题、features、description、details 的实际售卖身份及成分证据判断，类别辅助，歧义及关键冲突保留待裁决。它要求证据可核实，**没有逐商品明文要求必须具有一个完整配料声明字段**。

现行 [config/grain-A-v1.json](C:/Users/Kane/Documents/CodexProject/Thesis/config/grain-A-v1.json) 的 policy.include 为：`Identity/form and explicit complete single-grain composition declaration must agree, with no unresolved counter-evidence.`；unknown_composition 为 pending。[catalog.py 第 180 行](C:/Users/Kane/Documents/CodexProject/Thesis/catalog.py:180)在其他检查后，只要没有已识别 composition 就返回 missing_composition；第 182 行又要求组成全部解析且粮种一致。其他更早的拒绝分支会遮住后续成分问题，所以 missing_composition 不是所有受该门槛影响对象的总数。

这是一项比草案文字更严格的实现性解释，之前没有把“完整声明逐条必需”作为独立研究选择向用户说明。保守处理未知有依据，但这个实现把配料披露可得性变成了统一选择条件。正式修订须明确改变证明条件，不能把调整说成只修一个无关 bug，也不能因此声称原先批准了扩展 A。

[Amazon Reviews'23 官方字段说明](https://amazon-reviews-2023.github.io/main.html#data-fields)只提供通用 title、features、description、categories 和 details 等字段，没有保证必填的完整食品配料表。**据此作出的限制判断：**来源没有披露完整配方，不等于所售对象无法识别；即使来源提供完整声明，也不能仅凭商品元数据独立验证真实配方或供应链。

## 全量影响：计数与含义分开

通过 Thesis Python 对原始元数据 **603,274 行扫描至 EOF**，同时对齐现行逐商品审计与待裁决记录；13 入选、547,052 排除、56,209 待裁决全部与旧验收一致。全量 SHA-256、逐样本原始行 SHA-256 和路径保留在[本轮诊断摘要](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/usability-04-05-draft-01.json)。

| 现行互斥待裁决理由 | 数量 | 本轮解释 |
| --- | ---: | --- |
| weak_identity | 36,738 | 弱线索；不能等同于实际商品身份均不明，含用途／过敏原误命中 |
| category_form_conflict | 7,403 | 类别／形态信号；含确为 A 外成品的记录，不都是实质矛盾 |
| ambiguous_processing_or_mix | 4,007 | 加工／组合信号；干米片、预处理歧义与真正混合品混在一起 |
| missing_composition | 3,953 | 该分支因未识别完整成分声明阻断；不表示售卖对象已逐条证实符合 A |
| form_not_verified | 2,990 | 形态未被现行解析确认；含有效原粮描述遗漏，也含零食和用品 |
| category_identity_conflict | 702 | 需区分上位类别、实质粮种冲突和商品名误读 |
| unresolved_composition | 216 | 需区分实际不完整组成、宣传／用途误作组成及别名遗漏 |
| field_form_conflict | 76 | 需回查原句是否真正陈述本品形态 |
| field_identity_conflict | 71 | 需回查原句是否真正陈述本品身份 |
| composition_declaration_conflict | 53 | 需区分实质配料冲突与品牌／百分比宣传误读 |
| **合计** | **56,209** | 这是旧实现理由计数，不是新语义裁决的总体数量 |

合并旧理由得到四个**诊断工作队列**：缺声明 3,953；组成解释未决 216；加工或字段冲突信号 12,312；身份／形态弱证据 39,728。它们只是排查入口，不能直接冒充用户要求的四类语义结论。

门槛影响的更具体事实如下：

- 旧草案 5,372 个机械 A 候选中，3,474 个落入 missing_composition，另有 173 个 unresolved_composition；最终其中 12 个入选，另有 1 个正式入选商品在旧机械集合外。机械候选不是正式资格，不据此补入商品。
- 全部 3,953 个 missing_composition 中，555 个在文字中有 ingredient／contains only 等发现词，3,398 个没有这些发现词；**两组都不能据词直接认定完整声明是否存在**。该分支没有命中本轮定义的 ingredient／composition 类 details 键。
- 在 3,953 个中，434 个标题有 sauce、tray、paper、pudding 等 A 外对象词线索，45 个现行 crop 为 null。两项可能重叠，并非自动排除数量。原记录已经证实其中有 Fried Rice Sauce，不能全体放行。
- **1,367 个优先语义核查线索**满足：按现行 grain 词族只命中一个族、标题有 whole／raw／pearled／rolled／grain 长短规格等物理形态词、且没有本查询 A 外对象词。这个条件仍可能误读用途，也不能保证配方、食用等级或无关键反证；不是新增入选数、上界、下界或用户覆盖预测。
- 全部 Grocery 元数据中仅 332 条具有上述配料／材料类 details 键，118,382 条文字有成分发现词。前者只统计键存在，后者只统计文字发现；数据包括大量非谷物及非食品对象，不能用它们推断粮食商品完整配料披露率。

交叉信号、确切词表、原始行定位与判断限制均由[只读诊断查询](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/audit_data_usability.py)记录；它不调用正式筛选实现，也不是新增公共准备入口。

## 四类语义复核：41 条代表记录

每个旧待裁决理由取原始首行和 parent_asin 的 SHA-256 字典序最小两条，再补充具名问题记录并去重，共 41 个父商品。逐条读取 title、全部 features、description、details 与 categories；商品判断不使用评分、评论数、价格或模型表现。这是确定性的**非概率案例检查**，目的在定位不同机制；不能据它估算总体比例。

| 本轮语义主分组，仅对这 41 条 | 数量 | 建议处理依据 |
| --- | ---: | --- |
| 身份与 A 内形态明确，但完整成分未披露 | **5** | 元数据直接说明本品米粒／米片／燕麦等；建议修订后保留身份并标成分未知，不宣称已证明真实无添加 |
| 可核实别名、文本或类别层级解释遗漏 | **4** | 对照原句和确证名称／类别关系修正；不依据期待增加用户数放行 |
| 实际 A 外／混合成品或关键冲突 | **29** | 主分组中 24 条有明确 A 外对象／混合／成品，5 条以关键字段冲突或食用定位歧义为主；其他字段问题仍全部保留 |
| 证据不足或加工边界尚未解除 | **3** | 包括未说明形态和预处理边界；继续待裁决，不把未知补成干粮或未调味 |
| **合计** | **41** | 全部为 proposed_only，不改变旧正式决定 |

其中主分组不代表所有问题互斥，例如 Chipped Beef Gravy 的 Tomatoes 类别异常也保留，Popcorn Trays 的不规范类别也保留；两者售卖对象明确 A 外，因此主分组不将它们称作谷物身份未知。

其余 **56,168 条**已完成全量来源对齐、旧理由及交叉信号诊断，**尚未逐条完成这四类的语义复核**。本轮没有把旧程序标签包装成全部商品的语义真值；四类总体精确数量仍不能报告。正式规则确认后，必须在新全量审计中报告可复核的实际分类与迁移数量。

41 条逐条依据、主分组、原理由、原始完整记录及反证引用见[案例核查表](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/usability-case-review-20261012.md)及[结构化复核记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/usability-case-review-20261012.json)。完整原始对象保留在 data/diagnostics/usability-04-05-draft-01/representative-records.json，不覆盖、不改写来源。

## 代表性原始依据与反例

以下是原句摘录，**不是以摘录代替完整对象核查**。每个行号指完整官方元数据 gzip 解压后的 1-based 行；该文件 SHA-256 为 `ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`。每条完整对象和旧 counter_evidence 均保留在样本文件；行 SHA-256 见结构化复核记录。

| 父商品／原行 | 原始字段文字 | 判断及不能忽略的限制 |
| --- | --- | --- |
| B07K6THHFC／561,586 | features：`Contains 17.6 oz of uncooked rice` | 未熟米粒形态明确；咖喱为配餐用途，完整成分未知 |
| B0BYLK9168／13 | title：`TAJ Indian Poha Powa Flattened Rice (Thick, 4-Pounds)` | 米片售卖身份明确；名称不证明完整真实配方或无添加 |
| B087C4WM17／110,043 | features：`Ingredients: Pearled Raw Barnyard Millet` | 来源明确单一谷物声明和颗粒形态；现行形态／成分修饰解析遗漏，筛选及健康宣传仍不作核验证据 |
| B0019L8I58／140,996 | features：`INGREDIENTS: HATO MUGI`；title 同列 `Hato Mugi (Job'S Tears)` | 别名与 whole grain 描述可交叉核查；brown rice 是配餐用途，不能加进配料 |
| B0C1MM67QJ／1,961 | features：`Nothing else is added, just 100% pure organic fonio grain.`；末级类别 `Millet` | 有明确来源声明；fonio／millet 是具体与上位类别关系，不能仅凭配置键不同制造冲突 |
| B088PZLRK7／5,817 | features 含 `100% PREMIUM QUALITY` | 品质宣传不是配料声明；mix、porridge 等使用语境不能变成真实复合配方 |
| B00KA8R6I6／134,969 | title：`Whole Grain Texmati Brown & Wild Rice with Soft Wheat & Rye Berries` | 元数据直接说明多个粮种，即使缺 Ingredients 也有 A 外依据 |
| B005Y2BNPK／441,959 | title：`Kim Chee Fried Rice Sauce (pkg)` | 所售酱料；旧 missing_composition 不能视为通过了身份核查 |
| B077HTZ3WL／498,068 | title：`Local Hive from L.R Rice, Raw Honey, Pure and Unfiltered, Amber, 16oz` | Rice 是品牌／家族，来源全文佐证；蜂蜜不是米粒，百分比蜂蜜声明不构成米配料矛盾 |
| B0BWMCLXRL／37,450 | title 同列 `Flattened Rice`；features：`PREMIUM Gourmet Food Grade Flour` | 片／粉关键冲突真实存在，不能把 Flour 静默当作模板错误删除 |
| B00JM1DP32／33,250 | title：`GERBS Brown Teff Grain`；类别：`Buckwheat` | 保留标题／类别冲突；空 features／description 无法解决，不静默选一边 |
| B08L737QS1／533,306 | title：`Bakery On Main Organic Oats & Happiness Almond & Vanilla 12’s`；features／description／categories 均空 | 形态不足，存在口味／配料线索；不得推为纯燕麦干片 |

名称与处理事实的独立依据见[第一方来源研究记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/scope-evidence-research-20261012.md)。[CFTRI](https://ir.cftri.res.in/6762/)将 Poha／Avalakki 对应米片，同时说明其加工；这能解释名称与形态，不能证明这条商品未调味或真实批次采用何工艺。[FAO](https://www.fao.org/4/T0818e/T0818E01.htm)区分 ragi、bajra 等不同 millet 粮种，并将 fonio 列为其他 millets；上位类别不能拿来证明混合产品只有一个粮种。

## 最小修订建议与审核范围

完整可审正文见[最小规则修订草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/scope-rule-revision-draft-20261012.md)。建议允许“来源售卖身份和 A 内形态明确、完整成分未知、无未解决关键反证”的商品进入身份目录，并明确标记成分状态；保留完整声明子集。身份判断仍需正向证据，现行缺声明集合不批量升格。

同时只修正在本轮证实的售卖对象语义、百分比作用域、非特定前缀的形态证据、确证别名和类别层级问题；混合、调味、熟制、粉类及真实冲突不放行。预处理尚有歧义的 parboiled 等继续待裁决，不通过本草案顺带确认。

供应链核验必须另有具体声明对应材料，目录及来源宣传不提供核验通过标签。缺失的真实成分、加工和供应链经历保持未知；SIM 事实单列，不用模拟材料证明未知的真实配方。评论仍关联父商品，不关联为模拟批次真实评价。正常／异常场景协议、清洗与用户资格等参数继续在相应工单确认。

替代是保留完整声明统一门槛、仅修确定解析错误；会保持更窄的来源声明子集，但继续受披露缺失选择条件限制。**本轮不承诺任何修订后的入选数或用户历史增长。** 需要用户确认上述证明条件的调整后，才能产生可信的新全量结果。

## 工单 05 的现有覆盖及本轮限制

现有已验收版本仍是 grain-A-1.0.6／review-diagnostics-1.0.0：**13 商品、260 条原始评论、256 个唯一平台账号**。3 条完全重复的条件去重后为 257 条评论，账号仍 256；没有执行正式清洗。

原始交互下 252 个账号仅 1 条评论、4 个有 2 条；按严格时间先后与不同父商品衡量，255 个没有先前不同商品历史，仅 1 个有 1 个。旧稿“最新评价评分至少 4”的条件诊断有 181 个潜在账号，其中 180 个无先前正向商品、1 个有 1 个。**这不是已批准资格阈值，也不是已证明独立样本充分。** 平台账号是可计数单位，不能自动证明自然人独立性；重复场景不增加独立用户。

这些只引用旧验收记录，未对拟议目录重新提取评论；商品诊断和修订建议完全没有使用这些数量决定谁入选。新版本确认后才能完整重扫评论、重新报告历史深度和损失原因，再在对应工单论证独立样本充分性。

## 复现、独立核查与保留记录

本轮诊断版本：`usability-04-05-draft-01`。仅新增诊断代码、摘要、案例记录、研究记录与两份审核文档；无新增依赖。项目 Python 命令显式 `conda run -p` 指向 Thesis，实际解释器为 `C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis\python.exe`，Python 3.13.16。

```powershell
$env:TMP = 'C:\Users\Kane\Documents\CodexProject\Thesis\.tmp'
$env:TEMP = $env:TMP
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python .scratch\data-preparation\diagnostics\audit_data_usability.py
```

[可复核 notebook](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/usability-diagnosis-20261012.ipynb)保存关键 Python 计数和核查方法；不引入另一个正式数据准备入口。全量 profile 与完整案例原始对象位于 Git 排除的 data/diagnostics/ 中，版本管理只保留方法、来源定位、必要证据摘录和摘要。[独立核查记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/usability-04-05-draft-01-check.json)对账原始 EOF、56209 个 profile、41 个案例、字节摘要及保护文件。

已验收 Git 基线保持 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；正式配置与代码、规格、范围草案、目录及评论记录、04／05 独立验收与 Standards／Spec 审查记录均未改。原稿及既有研究等 **26 份原材料 SHA-256 与基线一致**。

本轮没有实施规则修订，因此没有声称新正式版本通过 TDD 或新一轮 Standards／Spec 审查。待用户审核修订草案后，再固定审查基线，按 mattpocock-skills 逐个行为 TDD、两轴审查、修复、提交并全量重跑 04／05；旧版本与原稿继续保留。
