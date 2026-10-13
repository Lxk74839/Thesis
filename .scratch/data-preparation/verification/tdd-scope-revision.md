# 新版 04／05：逐行为 TDD 实际记录

公共 seam：prepare_data.py CLI 的 catalog／review_extract，沿用用户确认；固定基线 fb5eff2d09bca20381529a5da5dac9c479a28acf。全部命令使用 `conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -m unittest ...`。不从生产函数内部取预期值。

| 行为／测试 | 实际 Red | 最小 Green |
| --- | --- | --- |
| admits_explicit_grain_with_unknown_composition | 原目录空，预期 RAW／not_disclosed，断言失败 | 独立身份规则路由；明确形态且仅缺声明可入选；单项通过 |
| does_not_infer_form_from_category_or_ingredients | Arborio＋配料＋类别被纳入，预期形态未明待裁决 | 独立正向形态词与依据；类别、包重、仅粮种配料不补形态；两项通过 |
| uses_direct_fields_without_fixed_prefix | uncooked rice 非固定前缀的商品未入选 | 有直接粮种／形态陈述的字段参与判断，配餐句不参与；单项通过 |
| recognizes_the_sold_object_before_grain_words | 酱料／托盘／蜂蜜／starter 被误列待裁决或入选 | 先识别标题实际商品中心并记录完整原句，不能因粮种名称纳入；单项通过 |
| separates_marketing_percentages_from_composition | Premium／Italian 被误当完整组成，变成 unresolved | 有据品质／来源百分比保持非成分角色，真实纯粮声明另记；单项通过 |
| keeps_ingredient_continuations_but_not_cooking_directions | Salt 续行、烹调句、声明冲突都误列 unresolved | 独立披露解释保留续行和未知，明确烹调边界；混合／真实冲突阻断；单项通过 |
| resolves_known_names_without_collapsing_millet_species | Hato Mugi、Barnyard、Fonio 漏解，Ragi/Bajra 混粮未区分 | 确证别名、完整原句、上位类别与不同粮种分别解释；长别名优先完整匹配；单项通过 |
| admits_dry_flakes_but_keeps_processing_counterevidence | 干片仍被 blanket poha/flattened 阻断，调味未明确排除 | 干片、片／粉冲突、parboiled 待决及实际调味分别处理；单项通过 |
| retains_real_counterevidence_but_ignores_context_roles | 设施／配餐误作形态冲突，食用／饲料反证被放行 | 逐句区分语义角色；显式否定不作正向身份，真实字段／食用定位冲突保留；单项通过 |
| blocks_explicit_mixtures_and_partial_composition | 明确米／麦混粮误 pending、部分配料误成未知、粉类被配料未决覆盖 | 标题明确多粮种及本品新增配料阻断；部分声明不当完整声明，A 外形态保留；单项通过 |
| records_every_old_new_decision_and_preserves_old_artifacts | CLI 不接受 previous-catalog-record，无法产生迁移产物 | 旧审计摘要验证与逐行对齐、全量旧新状态及理由记录；旧产物字节保持；单项通过 |

首轮全套 59 项回归中发现既有新版烹调边界测试失败：逐句反证检测把 Cooking instructions／Add oil 当作油类形态。该既有失败即 Red；补齐明确烹调／营养角色，单项重新 Green，未放宽真实配料续行。

实际 41 条原记录通过 CLI 复现时发现 7 个不符项，尚未生成正式全量版本。针对机制逐项修复：品牌产品线及 not sticky 质地描述误作反证，新增公共夹具实际 Red 后修正角色和否定作用域，单项 Green。

Bird Seed and Feed 含 making 用途文字时被误跳过，公共夹具 Red；先保存实质食用定位反证再记录用途角色，Green。

真实部分配料的 ingredients like／sweetened with 被错当未披露，公共夹具 Red；保留明确添加配料与部分声明状态，不将纯粮部分陈述当完整，Green。

调料包与 Seasoned Rice 类别的真实矛盾被 A 外对象捷径忽略，公共夹具 Red；保留具体商品类别反证，茶／米词的假矛盾仍区分，Green。

明确罐装蔬菜与单纯金属罐包装需区分。初始夹具 Corn Cans 已被旧标题规则捕获，实际为绿，不能当作 Red；已撤回新增逻辑，把夹具调整为真实结构 Corn, 15 oz Cans，重新观察到 Red，再实现直接售卖形态识别后 Green。前者按售卖形态排除，后者不靠包装改变原粮身份。

标题 alternative to 被误作售卖混粮，公共夹具 Red；只读取实际售卖段，同时在明确 millet 列举上下文辨认 Foxtail／Kodo 等多个粮种，Green。

同粮种但 Rice 与 Rice＋Salt 的多条声明被当作一个配方，公共夹具 Red；对实际声明包含的粮种及其他成分分别对账，保持冲突，Green。

review_extract 复用行为补充公共入口回归：新身份目录保留完整成分未知、零评论商品，末尾／低评分／空文本原字节均提取，且不按变体关联。已有评论实现本身通过此测试，无须新增实现，也不声称观察到 Red。

第一轮独立审查：Standards 0 项；Spec 4 项 P1，尚未全量生成。均通过公共 CLI 逐项观察 Red 并修复：No Raw Rice Grain 否定误入选；This product is wheat 不重复形态词的直接身份冲突；真实混粮与 perfect for 同句；Apple Cinnamon 本品风味误作未知纯粮。用途仅在局部分句生效，食谱仍不充当配料。另在第三项中追加 rice/wheat 实际混粮反例，观察到待裁决误覆盖排除的 Red 后修复。全部单项 Green，第二轮全套 71 项通过（24.353 秒），见 scope-revision-tests-round2.txt。旧配置／既有行为仍通过。

第二轮审查：Standards 0 项；Spec 2 项 P1。扩充真实混粮 making it perfect for／本品 wheat for baking 夹具，实际 Red；不再枚举连接词，改为语义角色记录开始位置，保留前置本品事实，只把后置用途归为上下文，Green。另增加 Arborio Rice＋Store in a cool, dry place，实际 Red；储存说明保存为上下文，不供销售形态，直接 uncooked rice 仍可供证，Green。全套 72 项通过（25.003 秒），见 scope-revision-tests-round3.txt。两份独立全量验收脚本不导入生产实现，分别核对源原文／旧新审计与 SQL 评论分组／时间／损失，旧验收脚本保持原样。

第三轮审查：Standards 0 项；Spec 2 项 P1。Perfect for dinner; this product is wheat 扩展夹具 Red 后按独立分号句保留事实，Green；Store dry／Keep dry 扩展夹具 Red 后采用存储指令头，Green。重新检查 41 条实际完整原记录，发现 Salt-Free 标题、high starch 质地、带拼写误差 alterative／EASY TO USE 的比较用途和部分配料列表的误解释；分别公共夹具实际 Red→最小 Green。部分配料列表不能按不同完整配方判冲突，但完整纯粮与真实添加声明仍冲突。全套 75 项通过（25.664 秒）。

41 条历史代表记录的旧诊断保留不改写。其中 B08L737QS1 原 U 注释记 Almond & Vanilla 口味／配料线索及形态缺失；新版按明确标题风味组合（与 Apple Cinnamon 同一已确认 A 外原则）排除，不声称补齐完整配方或核实真实配料。独立 oracle 明列这一语义更正，其他 I／P、X、C／U 预期保留。仅代表案例对齐不是总体人工裁决，正式全量和新入选抽查仍需完成。

2026-10-13 继续：第四轮 Standards 0 项；Spec 3 项（P1 1、P2 2）。非固定前缀 quinoa 身份反证、No sugar 否定成分、同字段身份＋Serve 配餐遗留反证，全部逐公共夹具实际 Red→Green。

1.1.0 全源 603,274 行迁移／字面引用／摘要及 76 保护文件通过，但新增入选低 SHA 分层样本揭示品牌目录、否定列表、调味混合、罐装水浸、泛称 Old Fashioned 和植物学干旱描述等误入；拒绝正式验收，保留全部配置／产物／对账，见 grain-A-1.1.0-rejection.json。修订只对元数据证据，不依据评论数量。

独立新配置 grain-A-1.1.1；品牌 inventory／free from、Blended 与后发现身份的类别冲突、We blend 实际添加／Canned in water、inline Ingredients、泛称风格／气候／malt／grain spawn／meal，分别建立公共行为夹具、实际 Red 后做最小修复并 Green。Old-Fashioned Oats 仍按已批准干片，普通金属罐保持可入；malt 等未明预处理保留待决，不扩大 A。全套 83 项通过（31.176 秒），旧 1.1.0 及旧 04／05 保持原字节，下一全量及独立语义复核尚待进行。

第五轮：Standards 0；Spec 3 项 P1，均实际 RED→GREEN。先收集已划分的本品正向陈述，再针对最终身份核对全部字段，消除反证受字段顺序影响；非标题预处理与食用定位保持待裁决；Not only...but... 不截断真正添加项。1.1.1 在停止尝试前已全量结束，未杀进程；41 代表复核因 meal 泛义误判失败，拒绝并保留六摘要。独立新配置 1.1.2，meal 配餐与营养风味隐喻经真实案例 Red→Green，保留真实食用定位矛盾。

明确 A 外形态被后续泛义描述覆盖的问题通过双顺序公共夹具 Red→Green：收集全部明确范围外事实，在声明一致性最终判定前恢复排除；完整声明冲突仍保持待决。全套 86 项通过（29.971 秒），41 完整原例最终一致（9 入选、25 排除、7 待决）；两次失败原例检查另存，不改旧注释。新增 06 数量敏感性脚本仅聚合未批准方案，没有清洗／截断正式视图、用户分组或模型输入，须在全量新版评论独立验收后运行。

第六轮：Standards 0 硬违反／1 轻微幂等清理重复；Spec 1 项 P2。No oil／Not parboiled 被错当肯定反证，公共对照夹具实际 Red→Green；本品 not rice 仍保留身份冲突，真正 Parboiled 不放行。独立1.1.3保留非身份否定原句及角色，删除第二次 X-free 清理。86旧项＋1新项回归全部通过。1.1.2 已全源且独立41／引用／迁移／76保护核对通过，但因语义误待裁决拒绝并保留六摘要。独立验收新增否定子句定位范围核对及所有拒绝版组件摘要复核，未修改旧验证结果。

第七轮：Standards 0；Spec 1 项 P2。This rice is not parboiled／No oil is added to this rice 的公共入口夹具实际 RED（两项错误 pending），按被否定的非身份对象移除肯定判据，同时保存完整原句和语义角色，GREEN。反证控制保留同句真实 contains salt 排除、but is malted 待决，既有 Not rice 和 Not only 不变。1.1.3 已全源结束但因本项拒绝验收，六组件摘要单独保留；未声称其已独立验收。独立 1.1.4 只更正版号与该语义，不批准工单06参数。

1.1.4 全套 88 项公共 CLI 行为测试通过（30.783 秒），见 scope-revision-tests-round8-final.txt。此前同实现使用 1.1.3 夹具的 88 项通过日志亦保留，但不作为新版配置的最终记录。

第八轮：Standards 0；Spec 1 项 P1。Cooked barley kernels／Cooked oat groats 与 Raw 标题＋本品 Cooked 字段的公共夹具实际 RED，分别误入选。独立1.1.5将明确 cooked 售卖形态按既有 A 熟制排除，字段与 Raw 矛盾继续待决；uncooked 和 when cooked 烹调描述仍可入选并保留角色。单项 GREEN。1.1.4 正在扫描时已核实 Thesis 解释器、命令及 PID 后停止本次计算，未覆盖其配置／部分产物；五项现有组件摘要留存，状态 aborted_pre_release，不声称完整扫描或独立验收。

1.1.5 全套 89 项公共入口行为测试通过（31.566 秒），见 scope-revision-tests-round9.txt；没有新增依赖。

第九轮：Standards 0；Spec 1 项 P1。Raw barley kernels; when cooked...; this product is wheat grain 的公共夹具实际 RED（错误 included）；独立1.1.6让标题的每个独立陈述与其他字段一起核对，单个用途句不能遮住下一句反证，GREEN。纯 when cooked 和 for wheat bread 仍按用途保存。1.1.5 未启动全量扫描，保留独立配置摘要并拒绝，未声称有目录或完整验收。标题用途原文角色统一由同一陈述逻辑记录，删去重复记录路径。

新增标题检查后第一次90项回归实际失败1项：同一标题身份引用重复，既有公共角色测试捕获。原测试不改，避免重复引用的最小修复单项GREEN；全套90项最终通过（32.984秒），见 scope-revision-tests-round10-final.txt。失败日志保留，1.1.6 尚待固定复审和全量验收。

第十轮：Standards 0；Spec 2项P1。Not only rice but salt 无Ingredients前缀夹具实际RED→GREEN：直接粮种组成对照保留为A外添加反证，宣传/用途不作配料。再独立验证 No whole grain rice／同形态修饰否定，实际RED→GREEN：否定后的形态不供正向身份；只对被否定粮种检查反证，“本大麦不是米”不作大麦身份冲突。两个行为逐项循环，92项回归通过（34.083秒）。1.1.6已全源结束但因这两项拒绝，六摘要保留，没有声称独立验收。

进一步核对同一否定作用域，Raw与Not raw关键形态矛盾的公共夹具实际RED→GREEN；先收集全部肯定形态，再对照否定，字段顺序两种方向一致，“本品未称rolled而Not rolled”不被误作形态冲突。未开启1.1.7正式扫描，属于同一未冻结实现版本；所有范围、成分真实未知与06未决参数边界不变。

上述追加形态行为后93项通过（31.755秒）。进一步检查同一明确添加与完整披露的交互：专用Ingredients单粮声明与字段Not only添加、标题明确加盐及多粮种组合的公共夹具实际RED→GREEN，保留为成分冲突；已有两项完整声明相冲突也不能被标题A外分支覆盖，追加控制实际RED2→GREEN2。无完整单粮声明的实际加盐仍排除。1.1.7全部94项通过（32.319秒），见 scope-revision-tests-round11-complete.txt；未改变测试接口或研究参数。

第十一轮：Standards 0；Spec指出sugar在outside_objects早退，Raw rice kernels with sugar＋Ingredients Rice的公共夹具实际RED→GREEN；同商品明确添加状态不变成未披露，完整声明矛盾保留conflict，Rice Sauce＋单粮原料对照仍属A外形态而不滥判配方冲突。独立1.1.8全部95项通过（33.486秒），见 scope-revision-tests-round12.txt。1.1.7全源已结束，因本项拒绝且六摘要保留，未声称独立验收。A、论文核心及06未决参数不变。

第十二轮：Standards硬违反0／possible Duplicated Code轻微建议1，已按简洁和最小修改原则评估保留局部更新，处理依据单独记录，不改写发现数。Spec两项分别公共CLI实际RED→GREEN：中文不含／不是不能供肯定粮种身份，其他粮种否定以及非转基因／无添加修饰对照保持正确；范围外Quinoa标题与直接Raw rice字段保留关键身份冲突，两字段依据均留存，Serve with配餐对照仍排除。独立1.1.9不扩展A、不补真实成分，1.1.8已全源但拒绝且六摘要保留，未声称独立验收。全套97项通过（见scope-revision-tests-round13.txt），所有运行显式Thesis，未新增依赖。

第十三轮：Standards硬违反0／新增启发0，历史轻微重复建议1接受登记保留；Spec 1项P2。Contains only rice, no salt完整声明及与Ingredients: Rice的一致声明，通过公共入口实际RED→GREEN；已知否定成分不计作正向组成，原文与声明片段保留，多份签名也使用同一肯定组成解释。No wheat同义控制正确、真实Rice+salt和既有Not only添加仍排除；未知成分文字不因否定处理而改成已知。独立1.1.10，1.1.9全源EOF但拒绝且六摘要保留，没有独立验收声明。全套98项通过（scope-revision-tests-round14.txt）。06诊断追加联合文本条件的聚合数量，仍未批准、未创建正式清洗视图或用户任务。

第十四轮：Standards硬违反0／新增启发0，历史轻微建议1保留；Spec 1项P2。完整声明salt-free被当作实际盐，公共RED→GREEN；再核对同一已支持语义的free from／does not contain，扩展夹具实际RED2→GREEN2。否定原文、完整声明签名一致性和真实添加对照均保留。1.1.10独立原例验收失败于日本精米的煮后质地；公共Cooked texture夹具实际RED→GREEN，仅把明确质地／食用意愿归上下文，This product is freshly cooked rice实际形态仍冲突。1.1.10全源组件及失败QA保留，独立新1.1.11未正式扫描。

41原例全量前回放随后暴露品牌蜂蜜pure and unfiltered被跨位and误当粮种添加；公共RED→GREEN，连接词须位于粮种与新增成分之间，Sugar and Rice实际组合控制仍冲突。41原例重新全部对齐，首轮失败及中间通过记录另存不覆盖。

74条分层完整元数据检查进一步定位真实inline made with加盐／葡萄干、inline made of 100%完整声称、历史southern oatmeal昵称、蔬菜米／菌种售卖对象、Rice Dishes字段／Cold Cereal和Granola类别反证／Muesli歧义，以及pre-gelatinized、机械字段和菌种培养用途。七个新增公共行为逐个实际RED→最小GREEN，食谱、其他真实谷物、明确否定与干制包装对照保留。仅反证定位和成分声明解释更正，不扩展A；类别／预处理不证明实际熟制，保守待裁决。74条按元数据原文作预期，公共入口回放62入选／4排除／8待裁决全部一致，详见semantic-preflight-1.1.11.md。

1.1.11全套108项通过（39.232秒），41原例及74条预检均通过，尚待固定复审及新版全量独立验收。未实施06正式规则、用户划分、模型输入或SIM材料。

第十五轮：Standards硬违反0／新增启发0，历史轻微重复1继续登记保留；Spec 1项P2。同字段第二份made of 100%完整声明被续接进第一份列表，公共RED→GREEN：明确完整声明开启新条目，Rice与Wheat两份保持conflict，一致Rice两份保持来源单粮声明，未标新声明的Salt仍为连续组成而非被截断。全套109项通过（38.474秒），41固定原例及74完整元数据回放再次全部一致；此前回放记录单独另存，不覆盖。独立全源验收还将核对这批有据更正的实际父商品判定与来源声明状态。生产配置1.1.11尚未生成全量产物，不需要将此次未冻结修复伪称另一个已发布数据版本。

第十六轮：Standards硬违反0／新增启发0，历史轻微重复1保留；Spec 1项P2。第二个内联 Product ingredients: 标签被当作续文，公共入口实际 RED→GREEN：明确标签开启独立声明，Rice／Wheat 冲突保留待裁决，两份 Rice 一致，普通 Salt 续文仍排除。随后同一声明边界的 Recipe ingredients: 用途控制实际 RED→GREEN：显式食谱标签结束本品列表，食谱不充当真实组成；没有用途标签的 Salt 仍延续真实配料。两项行为逐个循环，全部111项通过（38.747秒），见 scope-revision-tests-round17.txt。41原例与74完整元数据回放重新通过；此前109项回放另存 preflight-03／sample-02，保留历史。1.1.11仍未正式全源生成，A范围和06未决研究参数保持不变。

第十七轮：Standards硬违反0／新增轻微重复计算1，已按局部保存返回值修复，整理后111项通过；历史状态更新重复1继续评估保留。Spec发现显式食谱结束之后的 made with 文本仍污染前面的完整声明。公共入口实际 RED→GREEN：每份声明保存自身的部分披露状态，不再搜索整个原字段判断或比较完整声明；来源原文和声明片段保留，真正 Made with rice 仍 unresolved，普通 Salt 续文仍排除。全套112项通过（39.135秒），41原例和74条预检再次全部一致；各次回放和审查原报告保留不覆盖。1.1.11仍未启动正式全量扫描，未批准工单06的清洗、资格或充分性参数。

第十八轮固定实现 b3e879a 的 Standards硬违反0／新增启发0（历史1已修复、1评估保留），Spec0。1.1.11随后完整603,274行扫描与独立数量／迁移／870,774引用对账通过，但最终74条完整原文抽查定位四个实际误入／冲突案例，正式拒绝并保留六组件摘要、全源核查及样本；详见 semantic-sample-1.1.11-rejection.md，不将数量通过当语义通过。

独立候选1.1.12：①连字符专名 Otona-no-Furikake 遮住真实米饭调味料，公共 RED→GREEN，实际语言否定与专名分开，普通 No raw rice 仍未决；②Steel Cut／Corn Grits与Item Form Flaked的关键矛盾，公共 RED→GREEN，保留两方引用，rolled/flaked一致及食谱用途对照仍可入；③Bulgur名称的预处理歧义，结合实际USDA报告与元数据，公共 RED→GREEN，真正Raw Cracked Wheat和食谱用途不受影响。不扩A、不补真实加工事实。全套115项通过（42.705秒），41原例和两版已读分层样本的并集回放全部一致，原1.1.11回放不改写。独立验收按明确传入版本读取相应预检原文判定，下一版全源仍待执行。

第19轮因会话中断没有两个完整报告，不记通过，见 scope-revision-round19-interrupted.md。Spec阶段消息定位bulgur只加入标题歧义项、遗漏非标题字段。公共 description／features／details 三种直接陈述实际 RED；加到processing_claims后直接字段正确，但食谱用途对照仍失败。旧判定器留下的反证实际使用 ambiguous_processing_or_mix 原因码；按既有新版分句流程重建该类反证，直接预处理陈述仍pending、已明确用途不供反证，第三次单项GREEN。两次中间失败及116项失败回归日志原样保留，未削弱测试。最终116项通过（38.065秒），41原例和86分层并集重新通过，上一配置摘要的预检另存preflight-01。1.1.12仍未正式全源生成，没有伪增版本或冻结06参数。

第20轮也因会话中断没有最终报告，不记通过。阶段消息两项分别公共 RED→GREEN：Rice Flour 标题与直接米片销售字段的反向冲突保留 pending，专用配料、原料来源和食谱不提供售卖形态；whole grain／whole-grain 与 steel cut／steel-cut 的同义否定统一比较，原文保持原样，未主张的 rolled 否定不制造冲突。全部118项通过（39.829秒），41原例及86分层并集再次一致；旧回放 JSON 另存 preflight-02，旧日志可由固定提交 afc997f 和保留的日志恢复，不覆盖历史 Git 记录。仍为未全源生成的候选1.1.12，未确认06规则。

第21轮两个完整静态报告：Standards硬违反0／新增启发0（历史1已修复、1评估保留）；Spec P1两项、P2一项。三项分别公共 RED→最小GREEN：配料／made from原料形态不能补出售卖形态，直接非标题with salt售卖添加须排除且与完整Rice声明冲突须pending，Cooked rice与明确uncooked售卖字段保持反向关键冲突。食谱、原料与单独Cooked的对照不放行。121项回归失败1项捕获直接添加覆盖已有composition conflict，原测试不改，最小保留conflict修复单项GREEN。再对照直接100% raw rice kernels全商品陈述与Ingredients标签，公共RED→GREEN，形态仅切开明确配料／原料标记，不把百分比本身当配料标签。最终122项通过（41.078秒）。随后41原例回放实际失败3项：宽泛with把品牌／烹调及否定添加误作售卖混合；86分层回放失败1项需要回读原文。此前本段提前记为回放一致是记录错误，已依据实际失败日志纠正，未声称预检通过。上一通过回放另存preflight-03，当前失败回放及日志保留。1.1.12未正式全源生成，修复预检后才固定复审和全源验收。

预检回归修复：品牌、配餐／烹调、明确 no added sugar 与真实 sea salt 添加的公共夹具 RED→GREEN，with 须连接同一直接陈述中的粮种和实际添加项；原文中的否定不变成组成。另一粮种的直接 with 混合独立 RED→GREEN，与 Serve with 对照。B00ID0PB4E 第502360行完整原文重新阅读：标题 Quaker Quick 1 Minute Oats 明确是已有 A 允许的 quick oats 形态，Made from 100% whole grain oats 只提供原料／成分声明。编号标题解释独立 RED→GREEN，形态依据移到标题；没有形态名称的 Arborio Rice＋Made from 100% whole grain rice 仍 pending，不拿原料补售卖形态。首次只加旧判定器 forms 未改新版 identity_forms，单项及125项回归实际失败，日志保留；补到实际使用配置后单项GREEN2。最终125项通过（42.134秒，scope-revision-tests-round22-verified.txt），随后串行执行41原例及86分层回放均退出0／failures=[]。此时才记通过，失败回放另存preflight-failed-04。实际配置摘要684e0978…，identity_catalog.py摘要7f591cfc…；未生成1.1.12全源产物，等待新的固定审查。

第22轮完整复审：Standards硬违反0／新增独立启发0，历史评估保留建议注明最终conflict汇总分支的维护范围；Spec剩余P1两项。分别公共 RED→GREEN：含rice名称的 can be coated／topped 烹调用途切开，不等于 are coated with salt 的真实添加；salt mixed with rice 反向连接仍保存实际混合，食谱与 No salt 对照不误排。126项中间回归及127项最终回归均通过，最终42.474秒（scope-revision-tests-round23-final.txt）。随后41原例与86分层回放再次均退出0／failures=[]，前一通过回放另存preflight-05。当前生产器摘要5197e0d3…，配置684e0978…；1.1.12尚未全源生成，须固定复审通过后再扫描，未确认06参数或样本充分性。

第23轮完整复审：Standards硬违反0／新增启发0，Spec剩余P1一项。明确 sold cooked with salt 不是烹调建议，公共RED→GREEN：撤去无条件 cooked with／combined with 用途捷径，保留显式 When cooked、can/should/to be cooked 和食谱。128项通过，但41原例实际失败1项定位Hato Mugi原文的文化食用习惯 often cooked with brown rice。独立习惯烹调与实际售卖对照RED→GREEN，习惯不能补造本商品已熟制／混粮；失败另存preflight-failed-07。最终129项通过（43.040秒），随后41原例／86分层回放均退出0／failures=[]，生产器f788db3b…、配置684e0978…；旧通过另存preflight-06。仍待固定两轴复审和1.1.12全源及评论独立验收。

第24轮完整复审：Standards硬违反0／新增启发0，Spec P1两项。分别公共RED→GREEN：This product is sold mixed with salt 的直接本商品添加不需要重复粮种名；与完整Ingredients Rice冲突保持pending/conflict，而can be mixed和Recipe不成为真实组成。另项Powder／powdered是既有A粉类排除的字面形态，颗粒标题与Item Form Powder保持pending并保存双字段，明确粉类标题排除，食谱磨粉与Not powder控制保留。130项中间、131项最终回归均通过，最终42.778秒；随后41／86回放退出0、failures=[]，旧回放另存preflight-08。实际生产器bd9e7dd0…、配置2537534e…，仍待固定复审与全源验收，没有确认06参数。

第25轮完整复审：Standards硬违反0／新增启发0，Spec剩余P1一项。not mixed with salt／wheat 否定本商品添加，公共RED→GREEN，整段已知否定混合短语不供肯定成分，保留原句／否定角色；实际mixed with salt仍排除，but contains wheat后面的真实肯定反证继续排除，没有整句截断。132项通过（43.477秒）后，41原例／86分层回放退出0、failures=[]，旧回放另存preflight-09。生产器021606f5…、配置2537534e…；1.1.12仍未正式全源生成，等待新固定复审及来源/评论独立验收。

第26轮完整复审：Standards硬违反0／新增启发0，Spec剩余P1一项。完整Contains only rice, not mixed with salt声明不能把否定项当组成，公共RED→GREEN：肯定组成解释识别相同已知否定混合，原句和declaration_parts不改，与Ingredients Rice签名一致；真正Rice,salt仍排除。133项45.446秒通过后41／86回放均退出0、failures=[]，旧回放另存preflight-10。1.1.12尚未全源生成、06仍待确认；须新固定复审和全量独立验收。
