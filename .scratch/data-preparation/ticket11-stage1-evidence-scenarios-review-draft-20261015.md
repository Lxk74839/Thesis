# 工单11第一阶段异常场景协议及实施合同合并审核稿

日期：2026-10-15（Asia/Shanghai）。状态：**待一次集中确认；本稿不是正式配置、实施授权或场景接受记录。**

固定基线：2e6594e5d207f4f1798639dad652a9d140f17ef8。正常基准：sim-normal-1.0.0。推荐确认本稿第14节 J1—J8 后，再归档授权、按TDD实施、以该固定基线双轴审查并独立验收。本轮只交付本文件，不关闭工单11。

核心建议是：保留正常基准原字节，在独立版本路径形成16个自包含材料视图；使用固定哈希顺序选取150个父商品并跨视图复用；保留R1作历史检验语义对照，新增R5必要条款并组成R1 AND R5，验证当前零售材料过期对资格的影响。每种视图只构造一次，无模型运行或统计权重默认值。

论文题目保持“一种基于区块链与多智能体技术的农产品可信推荐方法”。保留全链路证据管理与多智能体推荐双模块，以及需求解析、推荐管理、用户画像、农产品画像、生命周期追溯、推荐依据核验六角色。

## 1. 依据和本轮完成标准

已只读读取AGENTS.md及docs/agents的工单、标签和领域约定；[必读研究草案](../../research/数据修复方案与验收草案_20261010.md)、[修订论文初稿](../../manuscript/论文初稿_表达与实验结构修订版_20261010.docx)、[正式spec](spec.md)、[09协议确认](issues/09-evidence-protocol.md)及其[原审核稿](ticket09-stage1-sim-evidence-request-review-draft-20261015.md)、[10最终接受记录](ticket10-acceptance-sim-normal-1.0.0.md)、[11](issues/11-evidence-scenarios.md)和[12](issues/12-evaluation-sample-design.md)。核对10的正式配置、主记录、接受记录、六个稳定组件及08接受说明，只为确定本次增量；不重新全面审查06—10。

初稿§3.2的“相关范围完整才可Supported”、§3.5的必要条件资格门禁和§4.2的配对任务约束继续适用。研究草案不替代正式spec；旧文档中的历史“待确认/未生成”措辞以09确认和10最终接受记录为准。

已检查本会话已安装插件及可用Skill。采用mattpocock-skills:codebase-design界定小型Interface及外部测试Seam，采用mattpocock-skills:research要求的后台原始来源复核，结论合并在本文件第13节。读取DOCX只提取原文，不修改或重新排版。TDD与code-review在确认后实施阶段使用，本轮不冒称完成实现审查。

本稿的完成标准是：每项场景能追溯到具体原件改动并手算四态；参数足以直接落成配置；公共入口、输出、独立参考、测试及文件范围一并明确；所有需要实施前决策的内容集中在J1—J8。与工单12有关的统计和模型参数保持明确未启用，不阻断离线材料组件。

### 1.1 继承事实和精确基准绑定

| 项目 | 已接受事实及本次处理 |
|---|---|
| 商品和正常SIM | 1,494父商品、1,494业务批次、8,964事件、11,952材料、22,410接收登记；R1全量Supported |
| 08根任务与分组 | 1,603个账户/根任务，开发320、测试1,283；1,845条历史正文；候选引用共2,393,008，每任务1,488—1,493 |
| 身份和评论 | 候选业务键为(parent_asin, sim_batch_id)；真实评论和偏好目标只归父商品，不分配给SIM批次 |
| 时间 | τ=1791417600000（2026-10-08 00:00 UTC），封存=1791375000000；真实历史截断T独立保留 |
| 运行与充分性 | 08工具仍为空；模型未运行、账本未部署、联合包未构建、样本充分性待判定；既有未知暴露继续未知 |

本轮实读并核对以下SHA-256；确认后配置直接绑定这些已有文件，不重新生成正常基准：

| 文件 | SHA-256 |
|---|---|
| records/sim/grain-A-1.1.15-sim-normal-1.0.0.json | 8694d35a342f6c198bc1db1a0d2ee4b5cad8e09a17e13aed72dacd23eb907715 |
| records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json | 831c951af0e09f0d041354579d0fa3713cb3deeb52c8328fe8574e347a0a338c |
| config/sim-normal-1.0.0.json | f58de2f0de17eff32ce461184c28a879560f1d97cfbc8836c2be391cd4572ba3 |

正常主记录已经绑定六组件、目录和09协议。09归档版本继续为sim-evidence-protocol-1.0.0；本次仅拟新增场景实施合同sim-scenarios-1.0.0。批准后新增确认记录及本稿实际摘要，既有协议/接受记录不回写。

## 2. 必要请求和四态合同

### 2.1 两个确定的请求profile

| profile | 必要条款和参数 | 最小组合及范围 |
|---|---|---|
| R1_SIM_Q1 | 该候选在基准inspection事件的指定采样，对SIM-Q1的报告结论为pass；source=experiment_design；time_scope=sampling_event | 同父商品、批次、inspection事件、sample_id的inspection_sample与inspection_report；请求项目集合须被报告test_scope覆盖 |
| R1_AND_R5_SIM_Q1_ON_SALE | 上述R1，AND该候选在固定τ的零售status=on_sale；两条均source=experiment_design | R1组合，加同父商品/批次/retail事件的retail_status，且valid_from_ms ≤ τ < valid_to_ms |

R5仅要求在售状态，不新增库存阈值、食品阈值、采样新鲜度或当前品质保证。请求按候选解析各自既有inspection/retail事件和采样，不指定某个留出目标。可读设计文本固定为“按已有历史偏好排序，仅考虑指定采样的SIM-Q1报告结论为pass且在SIM核验时点有有效在售记录的候选”。偏好推断不由本工单重做。

本组件对两个profile均生成离线参考。**推荐后续联合任务统一使用R1_AND_R5，16视图内请求字节相同；R1是组件语义对照，不另复制真实用户根任务。** R5单条在组合参考中保留声明状态，足以单独验收到期语义；不增加第三类用户任务。工单12确定主比较、统计与预算，13才实际接入08根任务。如后续改变请求适用范围，须显式升合同，不能在配对内换请求。

### 2.2 继承09的判定顺序

先检查来源与签发/读取权限、精确原文摘要、对象/事件/采样绑定、时间、登记与版本，之后才能用内容组成支持或否定证据。R1的正反双方都必须有完整采样绑定、SIM-Q1范围和合法检测时间；报告中的fail是原始事实，场景名称或计划中的“否定”不是证据。

对声明c，s/r分别表示至少存在一套完整可采用的支持/否定组合；complete表示相关授权快照的登记枚举、版本/撤销处理和必要原件核验完成。完整性分别记录enumeration_complete、required_reads_complete及version_checks_complete，便于区分读完后拒绝与尚未取得。

| 条件 | 声明状态 |
|---|---|
| s=1且r=1 | Conflict，另记完成性 |
| s=0且r=1 | Refuted，另记完成性 |
| s=1且r=0且complete=true | Supported |
| 其余 | Pending |

候选按必要声明合并：Conflict优先，其次Refuted，再是全部Supported，其他Pending。只有全部必要声明Supported才入合格集合。无合格候选允许空结果；一般偏好和基础分不能补缺口。R0无必要条件时另记筛选不适用，本轮不把它混成有证据的Supported。

缺原件/权限受限使必要读取未完成；摘要不符或错配在取得后可完成拒绝检查，但没有因此形成否定。任何无效材料都只影响实际依赖它的声明；若仍有其他完整有效组合，需据剩余组合判断。运行中的预算中断与离线参考完成审计分开，不能将模型漏读变成参考答案。

## 3. 时间、版本和授权的具体实施规则

### 3.1 历史材料与当前材料

R1的inspection_sample与inspection_report继续使用historical_fact，不加TTL。不改变采样、检测项目、事件发生时间或真实历史T来制造到期。其他非零售历史材料也不加TTL。

零售原件的正常区间是[1791374400000, 1791504000000)。到期视图只把选中对象的valid_to_ms改为τ=1791417600000，并更新该原件的模拟登记摘要；起点、观察、签发、status及τ不变。减少的是原区间末端24小时，不是把核验时点移到另一日。区间仍合法，签发早于结束。

因此，到期视图中R1仍Supported；R5因τ恰等于排他上界而无有效当前支持，组合请求为Pending。不相关零售到期不能让R1 Pending。若另有有效的当前停售原件，才可能否定R5；本次到期构造没有该原件。

### 3.2 新增记录的固定时间

| 新增事实/记录 | 固定毫秒UTC |
|---|---:|
| 第二谱系报告或同谱系v2签发 | 1791372000000（2026-10-07 11:20 UTC） |
| 上述报告接收登记 | 1791372060000 |
| 撤销/替代动作签发及业务生效 | 1791372120000 |
| 动作接收登记 | 1791372180000 |
| 全视图封存和τ | 继承1791375000000及1791417600000 |

新增报告仍引用原采样，test_started_at_ms=1791108000000、test_completed_at_ms=1791189000000、sampled_at_ms=1791105300000；不晚于签发，事件及主体绑定不变。新增登记与动作均在封存前，生效不晚于τ。τ、封存不随视图改变。快照后/尚未生效的边界仅在微型验收例覆盖，不另增加全量视图。

### 3.3 谱系、替代和撤销

- 同一evidence_id的v2只有在对象/声明范围不变、签发者获权、原文及接收登记有效，并有明确supersedes(v1)动作时，才是合法头版本。单纯版本号更大或时间更晚不能替代。
- 旧v1原件和登记保留。头版本已合法确立后，即使头原件缺失、摘要不符、被撤销或读取失败，也不能自动恢复旧pass；排除当前谱系后再看其他谱系。
- 两个不同evidence_id、无替代关系且各自可采用的报告，是两条独立证据谱系。若它们和同一有效sample共同对相同项目给出pass/fail，则为Conflict；不能跨谱系按版本号、较新时间或多数票取胜。
- 本次“独立谱系”仅指业务报告身份和修订链不同，不指现实机构、采样或生成过程统计独立。两报告可由同一获权SIM签发者出具。
- 撤销只作用于明确的id/version，由该谱系签发者发起、SIM-REGISTRY收录；不撤销整个谱系，不改成fail。非法/未授权动作不能撤掉合法原件；歧义或断裂的版本链属于可采用性问题，不直接构成内容Conflict。
- 只使用当前快照截止内且对τ生效的已接收记录；未来登记不改旧快照。快照外发布复查和模型预算仍归后续任务。

### 3.4 主体和权限清单

新增模拟签发者：**0**。沿用10的8个签发主体；检验报告均由SIM-LAB签发，sample由SIM-SAMPLER签发，零售由SIM-RETAIL签发，登记由SIM-REGISTRY完成。SIM-VERIFIER仍是离线读取主体。

新增签发种类、事件创建或跨谱系状态变更权限：**0**。10策略已经按kind授权，并未授权“一份报告的结论覆盖全部谱系”；本稿明确允许SIM-LAB为同一采样出具第二个不同身份的inspection_report，只用于谱系冲突实验。其ID另见第6节，不挤占正常谱系的ID。它不是新增独立机构背书。

新增状态动作仅把09/10已有issuer_own_lineage_only语义具体化为supersedes/revokes原件及登记格式。SIM-LAB只能处理自己签发的材料，SIM-REGISTRY只收录；其他签发者不得替SIM-LAB更正。没有真实签名或密码身份认证。

权限视图仅收紧读取：从基础策略派生单独policy，列出SIM-VERIFIER对选中inspection_report/v1的拒读键；allowlist、其他对象/种类及状态权限不变。新增宽授权：**0**。模型不能自选principal、快照或评价角色。若未来要用SIM-LAB-B等主体，本稿没有批准它，须另改合同。

## 4. 完整场景矩阵

本表V编号和中文名仅供准备/审核侧，不进入模型可见名称、ID、路径或错误文本。每行从正常基准独立分支，**不串行累积上一行扰动**。S是第5节固定150父商品；非S对象保留正常材料。除表内事实改动及必要的登记摘要、序号、外层manifest/snapshot派生更新外，其他内容不变。

共同不变量：父商品/批次业务键，六事件及前驱，真实评论归属，采样对象与时点（错配行明确例外），历史/候选/请求/基础分数不改。下表M为目标报告，A为其采样绑定，R为零售材料。S/Rf/P/C分别表示Supported/Refuted/Pending/Conflict；它们是文档手算期望，不是生成器字段。

| 视图及原始基准 | 具体改动 | 保持不变 | 从实际材料推导：R1 / R1 AND R5 |
|---|---|---|---|
| V00 正常：A+M/pass和有效R | 不改原件、原登记或基础权限；新增场景容器 | 正常五个事实/策略文件原字节，历史无TTL | 正向组合完整、范围处理完成；S / S |
| V01 必要材料缺失：M已登记且可取得 | 只移除S对象的M原件行，保留其接收登记 | A、登记摘要、R及其他材料 | 登记不能替代原文，M读不到，无完整正反组合；P / P |
| V02 对象错配：M及索引均属当前对象 | 把S对象M的parent/batch/event/sample改为配对供体对象，重算原件登记摘要；索引仍声明原目标对象 | 原目标候选、A、M的报告身份/签发者/项目/结论、其他材料 | 摘要吻合但索引/原件对象不合；不得拼接供体sample；P / P |
| V03 摘要不符：M/pass与登记一致 | M的conclusion从pass改fail，刻意保留旧登记摘要 | 完整对象/采样/时间、A和R | fail原件摘要失败，不可采用；s=r=0；P / P |
| V04 登记异常：M与接收索引签发者一致 | 只将S对象M登记行issuer_id从SIM-LAB改成SIM-RETAIL | M/pass精确字节及摘要字段、A、R、真正签发者 | 索引签发身份与原件及获权kind不合；登记无效，不是内容反证；P / P |
| V05 有效否定：M/pass | 在独立实验分支把M/v1结论改fail，匹配更新该模拟接收登记摘要 | M身份、合法SIM-LAB、对象/事件/sample/项目/检测时间及A/R | 完整A+可采用fail，且无有效pass；Rf / Rf |
| V06 有效冲突：A+正常M/pass | 新增SIM-LAB另一evidence_id的fail/v1及合法接收登记；无supersedes | 原M/pass及其登记、A、R、全部业务身份 | 同一A分别组成完整正反组合，两个谱系仍有效；C / C |
| V07 过期：R区间覆盖τ | R的valid_to从1791504000000缩至τ，匹配更新登记摘要 | R的on_sale/起点/观察/签发、A/M历史、τ | R1不依赖R，仍S；R5区间不覆盖τ，无反证，组合P；S / P |
| V08 撤销：M是有效头v1 | 新增获权revokes(M,v1)动作及接收登记，在封存前收录、τ前生效 | M及A/R原字节、旧登记、其他谱系为空 | 当前M被排除，撤销不等于fail；P / P |
| V09 合法新版本为fail：M/v1 pass | 增加同id的v2/fail、接收登记与合法supersedes(v1)动作/登记 | v1全部字节、采样绑定及检测项目/时间、R | 头v2有效否定，v1已被替代，不能制造正反冲突；Rf / Rf |
| V10 合法新版本仍pass：M/v1 pass | 同V09但v2结论仍pass | v1、采样/项目/时间、R | 头v2提供支持；更新本身不必改变资格；S / S |
| V11 读取权限：M本可读 | 派生策略仅拒SIM-VERIFIER读取S对象M/v1 | 所有原件及接收登记、其他读取授权 | 必要槽位不可得，参考也不能越权补pass；P / P |
| V12 无关变化：采收产区为SIM-AREA-01 | S对象harvest_record的origin_area_id改SIM-AREA-02并更新登记摘要 | 采收对象/事件、A/M/R及两profile的全部必要依赖 | 两请求都不要求产区，不影响任何必要组合；S / S |
| V13 分离组合：正常150对象 | S前75做V01，后75做V06；对象不重叠 | 其余对象和各自未涉及材料 | 前75 P、后75 C；两profile相同 |
| V14 同对象组合：正常S对象 | 对S同时做V06及V07 | 原pass报告/A、τ、非依赖材料 | R1=C、R5=P；候选按优先级C；C / C |
| V15 同对象组合：正常S对象 | 对S同时做V09及V07 | v1及A、τ、其他原件 | R1=Rf、R5=P；候选Rf；Rf / Rf |

V05、V02、V03、V07、V12对v1的改写是**彼此隔离的反事实世界**，不是声称在同一实际登记历史里偷偷改写旧版。正常v1字节仍保存在正常基准；每个分支有自己的材料、模拟登记与快照身份。V09/V10才模拟同一世界内真实的合法修订过程，必须保留v1并追加v2和动作。材料读取和缓存键必须含snapshot_id，禁止仅凭evidence_id/version跨分支复用。

V05与V03刻意只相差登记摘要是否与fail原件相符；V06与V09刻意区分“另一个身份的有效反证”和“同一身份的授权替代”。这些配对用于检测资格是否真正来自完整绑定及版本事实。

## 5. 一套可直接实施的推荐参数

以下均是成本和可核查性驱动的**工程选择**，不是文献强制值或统计最优值。推荐一次批准整套，之后不再为基本比例、时间、种子或测试入口逐轮补配置。

| 配置项 | 推荐值 |
|---|---|
| schema_version / version / profile | sim-scenarios-config-1.0.0 / sim-scenarios-1.0.0 / paired_evidence_views_v1 |
| 基础字节合同 | 继承sim-jsonl-utf8-lf-1.0.0；新增字段严格整数，bool不能代替整数 |
| normal_binding | 第1.1节正常主记录、接受记录、配置的路径与实际SHA；六组件按正常主记录继续核对 |
| protocol_binding | 原09归档版本、草案与确认记录原摘要；不改原件 |
| approval_binding | 确认后新增ticket11-implementation-authorization-20261015.md，绑定用户确认和本稿实际SHA；这是确认归档的机械取值，不是另一轮参数决策 |
| request_profiles | 第2节两个profile、固定谓词/时间/事件选择；后续每根任务推荐使用R1_AND_R5 |
| 视图/重复 | V00—V15，共16；每视图1次，额外随机复本0，模型重复0 |
| 选择比例与取整 | numerator=1，denominator=10；m=ceil(N/10)，N=1494时m=150，实际10.04016% |
| 选择算法与种子 | sha256-order-v1，seed为ASCII十进制字符串20261015；不用语言内置hash或随机库shuffle |
| 跨视图关系 | 全部原子视图复用S；组合只按第4节规定分离或重叠；不另抽对象 |
| 扰动强度 | 每选中对象每原子操作恰1材料槽位/1登记身份字段/1读取拒绝，或1追加谱系/1追加版本/1撤销；没有额外噪声 |
| 组合 | 仅V13两组75、V14同150、V15同150；不做全因子笛卡尔积或随效果追加组合 |
| 时间/TTL | 固定继承τ/封存及第3.2节新时间；唯一到期改动为第3.1节；历史TTL=null（不启用） |
| 来源和权限 | 新签发者0、宽授权0；沿用8主体，第二报告仍SIM-LAB，拒读只收紧选中报告 |
| 存储 | 自包含完整快照，不做增量overlay、硬链接或junction；对象业务身份复用，文件分别写入独立版本 |
| 发布 | 新目录预构造、核对后发布，最后独占创建主记录；一致复用，否则拒绝覆盖 |
| 权重/模型/统计 | 不设置正式权重、K、基础评分算法、融合参数、模型预算或充分性阈值；状态为未定，不默认为0 |

### 5.1 扰动对象和错配供体的精确算法

输入只能是正常包全部父商品/批次的已接受投影、协议和本稿配置。对每个父商品p计算：

    h(p) = SHA256(UTF8("Thesis|ticket11|select|v1") || NUL || UTF8("20261015") || NUL || UTF8(p))

按h的32字节无符号升序排序，碰撞时按p的UTF-8字节升序。得到p[0..N-1]；S=p[0..m-1]。V13前floor(m/2)缺失、其余冲突；正式m=150时各75。V02中第k个选中对象的供体是p[m+k]，k从0开始；供体与S不重叠且各使用一次。要求N≥2m；正式基准满足，小夹具也须满足，不静默循环选回自身。

供体只提供parent/batch/inspection event/sample四个键；供体的原件、候选身份和采样报告不被改写，也不把它的有效材料加入原对象的组合。若选中对象恰是某用户留出目标，那是固定算法的自然交集，不能重抽或避让。

文档独立SHA核算的微型选择黄金向量如下，N=3、m=1，S应为PX3，供体为PX2：

| p | h(p) |
|---|---|
| PX3 | 6c9821f8a0d49b4b3808ab56d68c79a45b2112fb38cb735217ed52a30056f47c |
| PX2 | 777d578715dfa5c960f82ad7ac60a6e12d5ebbfae37e7f6a1f03881b245b63d4 |
| PX1 | e545cdd709a370b539fe4d5709cc7a70ca5ecb7618fe0dbd3d2334571139a8dd |

这些值在实现前用系统SHA-256核算，不从未来生产输出反存为期望。小夹具不是实际用户或统计样本。

### 5.2 数量、共享和存储影响

| 量 | 预计数及含义 |
|---|---:|
| 业务父商品/批次 | 仍1,494 / 1,494，没有新增真实对象 |
| 16视图批次/事件序列化行 | 23,904 / 143,424，是复制行，不是新增业务身份 |
| 全部材料行 | 191,832：16×11,952，V01减150，V06/09/10/14/15各加150，V13减75加75 |
| 基础对象接收登记行 | 359,385：16×22,410，新增报告接收共825 |
| 变更动作原件/对应接收登记 | 各600：V08/09/10/15各150 |
| 总接收登记行 | 359,985，含上述600动作登记 |
| 原子操作作用次数 | 2,250个选中对象—视图位置，共2,550次原子操作；V13每对象1操作，V14/V15每对象2操作；不据此增加样本数 |
| 离线候选参考行 | 16×2×1,494=47,808，含必要声明推导，不是用户实验运行数 |
| 后续按推荐组合请求接入全部根任务 | 16×1,603=25,648个用户—视图关联；开发5,120、测试20,528；本工单不实际生成联合关联 |
| 后续候选逻辑引用 | 16×2,393,008=38,288,128，可引用08既有候选数组，不按视图重复展开保存 |

正常六组件现有实际字节合计27,987,126（26.6906 MiB）；按16份完整复制基数估计447,794,016字节（427.0497 MiB）。新增/删去材料、动作、派生快照及策略使实际值略有变化，实施时据实计数，不能把此估算写成实产字节。

若47,808条参考连同定位平均约4 KiB，参考约186.75 MiB；全组件加参考和必要审计预计约0.6—0.7 GiB，临时构造和最终目录并存时建议预留2 GiB可用空间。这是规划估算，不截断参考轨迹以强行守住4 KiB，也不以空间估算代替实际门禁报告。无新依赖、无模型调用、无账本交易。

采用完整快照的理由是当前数据仅约27 MB，额外约0.4 GiB可以换取直接读取、精确字节复核和较小的实现范围；overlay虽然更省磁盘，但需要额外合并、回退和路径解析逻辑，本次不推荐。16视图、10%和1次构造用于覆盖机制并控制成本；没有进行强度搜索，不声称覆盖全部异常分布。

所有用户共享同一组商品材料视图。对某根任务实际受影响候选为C∩S，不为了凑每用户150再抽；按现有候选规模，其大小介于144—150，实际值由后续合法候选计算并记录。共享snapshot、batch、evidence、扰动集合及生成版本须保留给工单12处理相关性；同一账户场景复制后独立账户仍1,603。

### 5.3 确认后配置的封闭字段

正式配置恰含下表13个顶层键。固定profile只实现本稿这套构造，不开放任意扰动脚本或隐藏覆盖选项。下表的派生摘要在确认归档时计算，不再产生新的研究决策。

| 键 | 类型及完整取值规则 |
|---|---|
| schema_version | 字符串sim-scenarios-config-1.0.0 |
| version | 字符串sim-scenarios-1.0.0 |
| profile | 字符串paired_evidence_views_v1 |
| byte_contract | 字符串sim-jsonl-utf8-lf-1.0.0 |
| normal_binding | 对象，恰含record/acceptance/config；各恰含path/sha256，值为第1.1节三个绑定 |
| protocol_binding | 对象，与正常正式配置的protocol_binding逐字段完全相同 |
| approval_binding | 对象，恰含draft_path/draft_sha256/record_path/record_sha256；draft为本文件，record为本目录ticket11-implementation-authorization-20261015.md，摘要取确认归档实际字节 |
| request_profile_ids | 字符串数组，顺序恰为R1_SIM_Q1、R1_AND_R5_SIM_Q1_ON_SALE；请求具体字段固定为第6.3节 |
| selection | 对象，恰含population=baseline_parent_asin、algorithm=sha256-order-v1、seed字符串20261015、numerator整数1、denominator整数10、rounding=ceil、donor_rule=next_disjoint_block、shared_set布尔true |
| view_ids | 字符串数组，顺序恰为V00至V15；V名只在管理配置/私有计划中，公开事实索引使用第6.1节q_身份 |
| clock | 对象，恰含verify_at_ms=1791417600000、sealed_at_ms=1791375000000、new_report_issued_at_ms=1791372000000、new_report_registered_at_ms=1791372060000、action_issued_at_ms=1791372120000、action_effective_from_ms=1791372120000、action_registered_at_ms=1791372180000、expired_retail_valid_to_ms=1791417600000；均为严格整数，并与基准及第3节校对 |
| identity | 对象，恰含new_issuers空数组、additional_report_slot=record-2、status_change_authority=issuer_own_lineage_only、read_principal_id=SIM-VERIFIER、registrar_id=SIM-REGISTRY |
| publication | 对象，恰含layout=self_contained_full_views_v1、repeat_count整数1、extra_replicates整数0、overwrite布尔false；其他存储/路径规则固定见第6/9节 |

selection只在已绑定基准父商品上运算；V13的二分、V14/V15叠加和各原子改动固定在profile中，不再另设比例/强度开关。历史TTL不配置成数值；没有预算、权重或模型字段。全部未知键、值域变化、重复ID/数组项和类型错配均拒绝，不能因配置文件存在而视为已获批准。

## 6. 产物、字段和精确字节合同

### 6.1 独立版本布局

拟写入以下新路径，确认前均不创建：

    config/sim-scenarios-1.0.0.json
    data/sim-scenarios/grain-A-1.1.15/sim-scenarios-1.0.0/
      manifest.json
      requests.jsonl
      view-index.jsonl
      views/<opaque-view-id>/
        batches.jsonl
        events.jsonl
        materials.jsonl
        registrations.jsonl
        change-actions.jsonl
        policy.json
        snapshot.json
      private/mutation-plan.jsonl
    records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json
    data/sim-reference/grain-A-1.1.15/sim-scenarios-1.0.0/scenario-reference-1.0.0/
      reference.jsonl
      check.json

“可供公共Interface验收的产物”不等于可供模型浏览的文件。完整容器及管理manifest不挂给模型；未来工具只按当前任务、请求和权限提供必要事实。mutation-plan和参考不列入模型输入清单。

opaque-view-id取q_加SHA256，域为Thesis|ticket11|view|v1，NUL分隔种子20261015和两位十进制视图序号00—15；不含场景名、四态、是否选中或目标。该ID只在准备侧和宿主审计侧使用。view-index记录视图ID、snapshot路径/摘要及base_snapshot_id，不含可读异常名；中文名和V编号只放私有计划。两个profile共享同一物理材料视图，不复制材料。

### 6.2 记录形状和新增身份

既有批次、事件及未改原件直接复制精确字节；基础材料沿用sim-material-1.0.0，基础接收登记沿用sim-registration-1.0.0。正常ID不重编号。材料在一个视图内以(evidence_id, version)唯一，跨实验分支的物理定位必须加snapshot_id；保留同批次的业务身份不等于可以混读两个分支。

新增第二谱系报告仍使用inspection_report的原字段及SIM-LAB，evidence_id为d_加SHA256，输入UTF-8串为Thesis-SIM-1:evidence后NUL，再依次NUL分隔batch_id、inspection_report、SIM-LAB、record-2。record-2是无结论含义的发行槽位，ID不包含fail、Conflict、场景号或目标。它与正常报告ID不同。v2复用正常报告evidence_id，只把version设2；其业务事实除结论和签发时间外继承原报告。

新增变更原件schema_version=sim-change-action-1.0.0，封闭字段如下：

| 字段 | 类型/固定规则 |
|---|---|
| source、schema_version、action_id | SIM、上述版本、a_加SHA256不透明ID |
| action_type | revokes或supersedes |
| target_kind、target_id、target_version | material、目标evidence_id、严格正整数；supersedes指向新头v2，revokes指向被撤销v1 |
| supersedes_version | supersedes时为1；revokes时为null，不用缺键表示 |
| parent_asin、sim_batch_id、event_id | 与目标报告及当前对象完全一致 |
| issuer_id | SIM-LAB；必须同时是该谱系原签发者 |
| issued_at_ms、effective_from_ms | 均为1791372120000，严格非负整数 |

动作ID输入为Thesis-SIM-1:change_action后NUL，再NUL分隔target_id、target_version十进制、action_type、effective_from_ms十进制。它是业务动作身份，不含期望四态；原件不含自身摘要或接收回执。

每个动作另有一条接收登记，schema_version=sim-scenario-registration-1.0.0，沿用基础登记字段，target_kind=change_action、target_id=action_id、version=1；content_sha256为动作原件精确字节摘要；对象键与动作一致、issuer_id=SIM-LAB、registrar_id=SIM-REGISTRY、receipt_status=accepted、registered_at_ms=1791372180000。动作原文和登记分开，避免摘要自包含。

新增材料接收登记仍沿用基础结构，version分别1或2，registered_at_ms=1791372060000。全部新registration_id继续按10的Thesis-SIM-1:registration域，NUL分隔target_kind/target_id/version计算g_摘要。登记sequence在每视图内按registered_at_ms、target_kind秩(batch/event/material/change_action=0/1/2/3)、target_id UTF-8字节、version排序后从1连续赋值。受追加影响的序号重排属于该分支快照派生元数据，不改正常包原登记。

V11唯一派生policy使用schema_version=sim-scenario-policy-1.0.0，保留基础策略字段及allowlist，另有base_policy_sha256和read_denials。每条拒读恰含principal_id=SIM-VERIFIER、target_kind=material、target_id、version=1，按目标ID排序；派生policy_id取p_加上述策略内容（不含policy_id）的SHA256。其他15视图policy字节直接复制基础策略。

### 6.3 请求、快照和清单

requests.jsonl恰两行，schema_version=sim-scenario-request-1.0.0。每行包含profile_id、source=experiment_design、固定design_text、necessary_clauses、preference_policy=inherit_root_history；必要条款各含clause_id、predicate、parameters、object_scope、time_scope、evidence_profile_id。R1参数固定SIM-Q1/pass、baseline_inspection_event/sampling_event；R5参数固定on_sale、baseline_retail_event、固定τ及半开区间规则。只支持AND，不新增任意规则语言；没有目标ID或预算默认值。

R1单独设计文本固定为“按已有历史偏好排序，仅考虑指定采样的SIM-Q1报告结论为pass的候选”；组合文本用第2.1节原句。R1的necessary_clauses仅[c1]，组合为[c1,c2]，逐字段合同如下：

| 条款 | 封闭字段值 |
|---|---|
| c1 | clause_id=c1；source=experiment_design；predicate=inspection_report_conclusion；parameters恰含required_conclusion=pass、required_test_scope=[SIM-Q1]；object_scope恰含candidate=current、event_selection=baseline_inspection_event、sample_binding=event_sample_id；time_scope恰含mode=sampling_event、ttl_ms=null；evidence_profile_id=inspection_sample_report_v1 |
| c2 | clause_id=c2；source=experiment_design；predicate=retail_status；parameters恰含required_status=on_sale；object_scope恰含candidate=current、event_selection=baseline_retail_event、sample_binding=null；time_scope恰含mode=current_assertion、verify_at_ms=1791417600000、interval_rule=from_inclusive_to_exclusive；evidence_profile_id=retail_current_status_v1 |

所有上述枚举为字符串，null为JSON null。event_sample_id指已绑定inspection事件的采样身份；同一声明的正反组合必须匹配这个身份，不能任取同商品另一采样。R1项目要求为集合包含，未知项目不自动通过；本稿全部原件仍只有SIM-Q1。

snapshot.json使用sim-scenario-snapshot-1.0.0，含source、catalog_version、scenario_version、base_sim_version、base_snapshot_id、protocol_version、policy_id、sealed_at_ms、verify_at_ms、cutoff_sequence、request_profiles及其文件摘要、components和snapshot_id。components恰列本视图除snapshot外的6文件，各含bytes/records/sha256。cutoff_sequence是封存时已接收登记的截止序号，本次全量视图均涵盖本视图全部登记。未来登记测试可存完整历史，但必须排在cutoff之后且不进入可见集合。

snapshot_id为n_加SHA256，输入域Thesis-SIM-1:scenario_snapshot、NUL及不含snapshot_id的快照紧凑JSON字节；其内容不包含私有计划、预期四态或参考答案。manifest列requests、view-index及16个快照/事实组件，记录真实计数和摘要，不含自身摘要；私有计划在主记录的单独audit_private节绑定，不进入公共事实manifest或参考稳定行的输入摘要。

全新记录采用UTF-8无BOM、递归键排序、紧凑JSON、严格整数、无重复键/非有限数及未知字段；JSONL每行结尾单LF。原件摘要不含LF；文件摘要含实际全部字节。materials按父ID UTF-8、10既有kind顺序、evidence_id UTF-8、version排序；动作按action_id排序；不把异常、选中对象或fail材料移到文件前部。空动作文件为0字节、records=0的合法组件。batch/events复制文件不重排。

private/mutation-plan.jsonl记录base与view绑定、原子操作、选中对象/供体、改动前后原文/登记定位和摘要、共享集合ID及版本；不写生成器计算的expected_status或合格集合。它用于检查是否按合同构造，与语义参考严格分工。管理员核对构造计划不等于从计划生成参考答案。

## 7. 场景包完整性与模拟证据异常必须分开

外层发布完整性检查的是：配置/授权/基准绑定、全部所列文件存在、真实bytes/records/hash一致、闭合schema、路径安全、视图清单完整、复制身份不被改写、实际改动与批准范围一致。**它不要求每条模拟证据都可采用或每个候选Supported。**

例如V01的materials文件是完整发布的文件，行数如实少150；模拟接收登记指向拿不到的原件。V03的外层文件摘要必须匹配实际fail字节，而模拟登记内仍保留旧pass摘要。V04外层如实保护身份错误的登记。上述可以是发布完整的场景包，同时包含不可采用证据。模型得到的是按权限读取的实际事实/技术观察。

实施中意外丢了整份组件、文件被截断、发布后少一行而未同步manifest、路径越界或清单摘要不符，属于场景包自身损坏，S1/S2必须失败，不能给所有候选补Pending，更不能Refuted。合法模拟异常允许存在于内层业务记录；外层完整性不能被“这可能是异常场景”豁免。

工单10的prepare_normal/verify_sim10只适用于正常profile。它们可用于既有正常基准的已接受事实，**不能在16视图上当作异常判定器**。正常核查失败不是四态映射。本次独立参考须实现第2—4节已批准语义，允许读到真实缺失、矛盾、撤销和权限事实，重新计算声明，不调用正常检查器再翻译失败码。

## 8. 与08根任务、用户组和基础分数的衔接

11产出的是材料视图库及请求合同，不修改08模型目录、tasks schema、身份密钥或固定试制请求，不给08旧会话注册工具。正式联合任务须等12确定正式设计，再由13生成新的manifest及真实受限会话。

推荐联合衔接键是(root_task_id, scenario_version, snapshot_id, request_profile_id)。root_task_id直接引用preference-task-1.0.1，不重新哈希账户、不造新用户；原分组只在受信任侧继承，同根全部16视图同组。批次映射来自正常包，历史评论仍不附批次标签。

同根配对必须以摘要验证以下字段完全一致：允许历史H、已见集合、完整候选C及顺序、白名单目录投影、原始与结构化请求、基础分数向量及生成版本、输出规模、模型/工具版本、预算和失败计费规则。基础分数须在材料扰动之外生成一次并共享，本工单不选算法或填占位分数。当前基础分数/预算尚未冻结，因此只承诺接入合同，不声称联合配对已经验收。

跨请求profile的R1/R1_AND_R5是离线语义对照，不当作同一请求的反事实差异，更不能用“改了请求后资格变化”代替材料因果检查。同根联合配对只改材料/其权限、版本和快照，不改变请求、历史或候选。未来K/排序和模型失败统计不由本组件提前决定。

生成器不接受08 private/evaluation、原评论库、私有偏好目标、目标评分/正文或模型结果参数，也不读取它们。目录包含某个目标商品本身是完整覆盖所需；知道哪个商品是留出目标则不允许。后续联结器只读取已批准08 model投影和受信任根ID/组别映射，不能以目标是否合格来改S、请求、根任务或分组。

共享关系须记录至view、batch、evidence及S级别；复用材料节省存储和生成成本，不增加独立样本。正式统计权重、用户内汇总、跨用户共享的敏感性分析、样本充分性和模型重复全部留给12。

## 9. 最小公共Interface及输出合同

以下是**拟实施合同，不是当前可运行命令**。生产准备仍只有prepare_data.py，不增加sim_scenarios.py独立CLI。

### 9.1 S1 唯一准备入口增量

新增stage=evidence_scenarios；新增参数--sim-record和--scenario-config，复用--output-root。本阶段三参数必填，其他阶段参数一律拒绝。目录和接受链由sim-record/配置解析，不另要--catalog-record，不收目标/模型结果/expected-status/异常类型参数。

    conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python prepare_data.py --stage evidence_scenarios --sim-record records/sim/grain-A-1.1.15-sim-normal-1.0.0.json --scenario-config config/sim-scenarios-1.0.0.json --output-root .

所有路径相对固定Thesis根解析；output-root必须项目内。source、config、临时、最终及失败明细路径均检查全部祖先的symlink/junction/reparse和越界；拒绝任何正式正常目录、已有场景版本或原研究材料作为覆盖目标。基准只读输入，不能“修复”其文件。沿用已验证的路径约束做法，只作必要复用，不借机重构旧模块。

成功退出0；stdout返回与新主记录相同的JSON，至少包含：

| 字段组 | 必需内容 |
|---|---|
| 身份和状态 | schema_version=sim-scenario-record-1.0.0、stage=evidence_scenarios、status=evidence_scenarios_prepared、catalog_version、scenario_version、protocol_version、profile |
| 输入绑定 | normal主/接受/配置、09归档、本次批准合同和正式scenario-config的path/bytes/sha256 |
| 生产追踪 | prepare_data.py/sim_scenarios.py摘要、固定候选Git SHA及工作树状态、Thesis运行时；实际时间不进入稳定组件 |
| components | 每个公开事实文件及manifest的相对生成root路径、bytes/records/sha256；audit_private单列计划绑定 |
| counts | business_parents/batches、views、profiles、序列化batch/event/material/registration/action行数；不能把复制行计业务数 |
| 状态边界 | independent_acceptance=pending_separate_record；formal_package_status=not_built；sample_sufficiency=not_determined；model_execution_status=not_run；ledger_deployment_status=not_deployed |

生成器不输出私有gold四态或候选合格集合。实际独立参考是S2产物，不回填生产器当答案。

失败退出2，无成功主记录或accepted记录。stdout恰含stage、status=evidence_scenarios_incomplete、error.code；稳定原因码限定invalid_arguments、unapproved_protocol、invalid_config、invalid_path、invalid_baseline、construction_mismatch、publication_incomplete、output_conflict。不回显材料内容、真实账户、私有路径或堆栈。外部I/O失败归publication_incomplete，基准摘要/接受链不符归invalid_baseline；细节只在项目私有审计侧留档。模型接口不直接转发此管理错误。

新鲜root先在项目.tmp独立暂存并完整核对，再发布版本目录，最后独占写主记录。相同输入/配置/代码及全部输出字节才一致复用，返回原主记录而不更新时间。任一不符或已有半发布版本均output_conflict，保留现场，不覆写或自动续拼；后续修订使用新版本。

### 9.2 S2 独立参考入口

独立验收程序拟为.scratch/data-preparation/diagnostics/verify_sim11.py，只承担验收取证，不是第二个准备器：

    conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python .scratch/data-preparation/diagnostics/verify_sim11.py --record records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json --audit-root <项目内新空私有目录>

仅两个参数；record按固定records/sim-scenarios布局确定生成root，组件路径不得越界，不能扫描邻近目录猜输入。audit-root新鲜、项目内且不覆盖基准/场景。没有--scenario-type、--plan、--expected-status或生产结果参数。

程序验证外层公开事实完整性后，对16×2×1494组合从实际原文、登记、动作、权限、请求、时间和快照重推。输入允许读正常接受链以确认基准，不读私有mutation-plan、不导入sim_normal/sim_scenarios等生产模块或生产核验函数，不调用模型。不使用V编号/名称决定支撑或状态。

成功退出0并写reference.jsonl和check.json，表示**参考计算及其输入审计完成**；包含Pending/Refuted/Conflict不导致退出失败。包损坏、无法读取必要容器、规则/结构不支持等退出2，写失败check，不能伪造完整参考或accepted记录。必要原件在完整容器里确实缺失，是可重推的业务事实；容器本身丢失则是运行失败。

reference每行封闭字段：schema_version=sim-scenario-reference-1.0.0、view_id、snapshot_id、request_profile_id、parent_asin、sim_batch_id、clauses、candidate_state、eligible、reference_rule_version=scenario-reference-1.0.0、public_fact_manifest_sha256。clauses逐项保存clause_id、s/r、完成性三项、adopted/rejected原件与登记/动作定位、原件/登记摘要、JSON pointer、对象/采样/时间/权限检查、版本头选择和组合推导。不包含偏好目标或评分。eligible仅在全部必要声明Supported时true。

稳定参考按view_id/profile_id/parent UTF-8顺序写，状态和合格集合仅私有。check另存实际计数、外层完整性、拒绝原因汇总、程序摘要/规则版本及运行追踪；运行时间不混入稳定参考。私有名称改写不应改变public_fact_manifest_sha256或稳定参考。

### 9.3 模型侧事实合同与本次未实施项

本次不实现list_evidence/read_evidence或真实推荐会话分派。保留09已批准方向：宿主固定当前任务、候选、请求、权限和快照，模型只能列举相关登记和读获准原件；不能读管理容器或切换范围。13接入时必须实际验收，不能把11离线隔离说明当作工具权限通过。

可见事实只包含source=SIM、实际对象/事件/采样/项目/结论/时间、合法相关登记和版本动作，以及真实的读取/完整性技术观察。不可见项包括V编号/中文名、view目录、共享snapshot的管理标识、S/供体映射、全局行数/全局截止序号、参考状态、合格集合和私有路径。宿主日志保留真实snapshot绑定，模型无需选择它。

原件/动作业务ID使用相同不透明前缀与摘要长度；候选沿08顺序，相关记录按evidence_id UTF-8与版本排序，不按状态或是否扰动排序。正常/异常视图都使用同一消息形状和SIM披露。未知/无权请求在确认授权前不检查资源存在性，统一access_denied；获权范围内确实缺原文可报告unavailable。技术失败词不得加入“正确答案Pending”等解释。

## 10. 外部测试边界和人工验收案例

### 10.1 测试边界

S1测试通过子进程调用唯一prepare_data.py，观察退出码/stdout/正式文件/保留字节和路径副作用；S2通过独立脚本的外部调用观察参考/check。测试不导入生产私有函数、不mock内部合作者，也不为了方便测试新增通用四态生产入口。

微型测试输入使用受信任、文档预先给定的PX对象和合成接受链；与真实正式路径隔离。错误基准必须拒绝；合法小夹具通过同样绑定合同，N≥2m，不能用生产CLI隐藏开关跳过摘要/授权。真实1494目录最终仍全量验收，不能以微型通过替代。每次TDD只选一个外部行为RED→最小GREEN，不提前横向写完全部测试。

### 10.2 关键手算例

例中PX1/BX1/EX1/SX1只是文档内合成对象；时间和项目使用第3节具体值，主体为既有SIM-SAMPLER、SIM-LAB、SIM-RETAIL、SIM-REGISTRY。A有效、M/pass可采用、R覆盖τ且on_sale为共同基准。

| 例 | 实际原文/登记/权限变化 | 应推导结果 |
|---|---|---|
| H01 | A+M/pass，相关范围全部完成 | R1 s=1/r=0/complete=true，Supported |
| H02 | M内容fail，但登记仍为pass摘要 | M拒绝；R1 s=r=0，Pending，不是Refuted |
| H03 | M/fail与登记摘要一致，全部采样/项目/授权/时间绑定完整 | s=0/r=1，Refuted |
| H04 | H03但去掉A，或M.sample_id换为另一采样 | 无完整否定组合，Pending |
| H05 | M/pass加第二evidence_id的合法fail；共用有效A，无替代关系 | s=r=1，Conflict |
| H06 | H05但第二谱系无签发权、摘要不符或不属同一项目/对象 | 第二报告排除，原M仍有效且处理完全部相关记录时Supported |
| H07 | 同id/v2 fail+合法supersedes，旧pass保留 | Refuted，不能因旧版pass制造Conflict |
| H08 | H07但已确立头v2原文缺失/损坏/撤销/不可读 | 不回退v1；没有其他完整组合时Pending |
| H09 | 后来v2和动作的收录在快照截止后，或业务生效晚于τ | 当前快照仍用合法v1 pass；Supported |
| H10 | 非原签发者发起撤销 | 动作无效，不撤掉M；范围处理完成时Supported，另记录拒绝 |
| H11 | 同id/version有两个不同接收摘要，无法确立可采用头 | 该谱系拒绝，不能仅靠登记矛盾判内容Conflict；无其他组合则Pending |
| H12 | R的valid_to=τ；其他完全正常 | R1 Supported；R5 Pending；组合Pending |
| H13 | 固定τ，四个R区间分别为[τ,τ+2)、[τ−2,τ+1)、[τ−2,τ)、[τ−2,τ−1)，单位毫秒；原件/事件/登记/封存时间采用下段具体夹具 | 单条R5依次Supported、Supported、Pending、Pending；分别检查起点、终点前1毫秒、终点及终点后1毫秒 |
| H14 | 所有历史材料保持合法，较晚τ下R已到期 | R1不因年龄变化Pending；R5须按显式区间重算 |
| H15 | 已取得正向组合，仍有相关分页未完成/必要读取未完成 | 仅有正证仍Pending；已见有效反证时另按09四态规则，不假装完整 |
| H16 | 同对象R1 Conflict、R5 Pending；或R1 Refuted、R5 Pending | 候选分别Conflict、Refuted |
| H17 | 只改不被两请求依赖的采收产区，或在R1下只改零售有效期 | 相关资格不变，不跨声明传播 |
| H18 | 外层manifest未更新而删原件行/改文件字节/丢组件 | S1/S2外层失败，无成功参考，不是商品Refuted |

H13是独立S2语义夹具：τ仍为1791417600000，retail事件起止、observed_at_ms、issued_at_ms、registered_at_ms及sealed_at_ms统一取τ−2；相关对象、权限和登记摘要均正确，current_assertion允许预先签发的适用区间。四个区间均满足from<to，所有已发生事实/签发/收录不晚于τ；此例不使用正常10核查器，也不计入正式16视图。H14同样是请求语义小例，不混入16视图的同τ配对。

### 10.3 应覆盖的公共验收行为

| 编号 | 外部行为和必须观察的结果 |
|---|---|
| A01 参数/类型 | 三参数必填、其他阶段参数拒绝；未批准合同、未知字段、重复键、非法整数/bool/非有限数拒绝，无成功发布 |
| A02 基准和只读 | 正常主/接受/配置及六组件摘要绑定，拒绝被损坏/未接受基准；正常原件、论文和既有接受记录字节不变 |
| A03 选择与复用集合 | PX黄金向量、ceil取整、供体非自身/非S、V13分割；真实N=1494得到m=150，所有原子视图同S |
| A04 构造范围 | 全16视图逐对象对比正常，只允许第4节改动与规定派生元数据；父商品/批次/事件/评论归属不变 |
| A05 可采用性 | H01—H06：无效fail不作反证，否定/冲突双侧采样/授权/时间绑定完整，其他有效组合可保留支持 |
| A06 时间/请求 | V07及H12—H14，R1无TTL、组合到期Pending，半开端点和合法签发/收录时间逐项核对 |
| A07 状态历史 | H07—H11：合法替代/独立谱系区分、头失效不回退、快照后变化不回写、未授权动作不生效 |
| A08 权限 | V11仅收紧明确报告；独立参考按同读取范围，不能用评估权限补支持；没有新增签发或宽授权 |
| A09 完整性/聚合 | H15/H16；拒绝提前Supported，Conflict/Refuted聚合优先级准确，合法空合格集合可表示 |
| A10 无关对照 | V12两profile资格逐候选不变；V07的R1逐候选不变，不只比较总数 |
| A11 包与证据分离 | H18必须失败；V01/03/04等内层异常的外层完整性通过，四态另算，不能调用正常核查结果映射 |
| A12 隔离与无暗码 | 生成器输入依赖及实际输出无目标/模型结果；改变私有哨兵不影响稳定材料；私有标签重命名不改独立参考；ID/排序/错误白名单无答案标记 |
| A13 参考独立性 | S2不导入生产模块、不读取计划/gold；H01—H18期望在实现前固定；人为改实际事实后参考依规则变化，仅改私有名称参考不变 |
| A14 全量数量/四态 | 实际行数按5.2核对；47,808参考全量重推，逐对象结果与下表相符；不以抽样替代 |
| A15 复现/复用 | 两个新空root稳定组件、snapshot、参考逐字节一致；旧主记录一致复用不改字节，变依赖/代码/配置/输出拒绝覆盖 |
| A16 路径/失败 | source/output/暂存/失败明细/审计根的junction及逃逸拒绝，0额外越界写入；半发布失败保留现场 |
| A17 接入合同 | 11不改08 schema、工具或分组；用无真实标签的公开夹具检查未来同根引用和字段等同性，不伪称已完成13真实接入 |
| A18 接受门禁 | prepared、参考计算完成和accepted分离；全量/复现/保护/外部测试/两轴无阻塞后才单独接受，充分性和联合包仍未通过 |

### 10.4 正式基准上的可核算四态总数

每格均按全1494对象，列出的其他状态数为0；未选中1344对象始终Supported。这是场景构造合同的预期，不允许S2按表造答案。独立参考完成后，由验收者另按私有构造计划和本表逐对象核对。

| 视图 | R1分布 | R1 AND R5分布 |
|---|---|---|
| V00 | S1494 | S1494 |
| V01/V02/V03/V04 | 各S1344/P150 | 各S1344/P150 |
| V05 | S1344/Rf150 | S1344/Rf150 |
| V06 | S1344/C150 | S1344/C150 |
| V07 | S1494 | S1344/P150 |
| V08 | S1344/P150 | S1344/P150 |
| V09 | S1344/Rf150 | S1344/Rf150 |
| V10 | S1494 | S1494 |
| V11 | S1344/P150 | S1344/P150 |
| V12 | S1494 | S1494 |
| V13 | S1344/P75/C75 | S1344/P75/C75 |
| V14 | S1344/C150 | S1344/C150 |
| V15 | S1344/Rf150 | S1344/Rf150 |

## 11. 确认后允许的最小修改范围

| 路径 | 允许目的 |
|---|---|
| prepare_data.py | 仅新增evidence_scenarios分派及两个参数、本阶段参数/退出合同；旧阶段语义不改 |
| 新sim_scenarios.py | 固定16视图构造、外层校验、稳定发布/复用；无独立CLI，无通用推理/规则引擎 |
| 新config/sim-scenarios-1.0.0.json | 只在确认归档后落成本稿完整参数与基准绑定 |
| 新tests/test_sim_scenarios.py | 经S1/S2外部Seam逐行为TDD；不导入生产内部实现求期望 |
| 新diagnostics/verify_sim11.py及verification/ticket11-* | 独立原件/登记/请求/权限/时间/版本参考、全量和复现/保护、TDD及两轴证据 |
| 新docs/data-sources/evidence-scenarios.md | 公共合同与场景组件边界，不修改正常接受说明 |
| 第6节data/records新路径 | 稳定视图、私有计划、独立参考和单独接受记录 |
| 新ticket11实施授权、工单11、map；必要spec确认追加 | 确认后记录本次具体批准及结果，不重写09/10原历史和接受结论 |
| .gitattributes中本审核稿/新增授权的精确路径 | 仅在确认归档时固定被摘要文件字节；不批量改现有规则或换行 |

不修改sim_normal.py、verify_sim10.py、08会话/白名单、06清洗、07分组、已有config/data/records版本、研究草案或论文。无需创建GLOSSARY/ADR占位文件。标准库足够，新增依赖0；使用已存在的C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis，Python3.13.16。项目代码、测试和验收显式conda run -p上述Thesis；涉及Conda的执行顺序进行，避免10记录中的共享TMP启动冲突。

## 12. 实施顺序、独立接受和停止边界

1. 本次仅写本审核稿。用户集中确认J1—J8后，先冻结本稿字节/摘要和确认归档，再写正式配置；原09/10文件继续只读。
2. 记录上游、正常包、论文、现有接受记录保护摘要。固定比较起点始终为2e6594e5d207f4f1798639dad652a9d140f17ef8，不移动到修订提交。
3. 按mattpocock-skills:TDD在S1/S2逐个行为RED→最小GREEN，保存实际失败/通过证据；通过新增行为及现有适用公共回归。基线已有226项通过，后续总数据实报告，不预言新增数量或运行时间。
4. 固定完整候选代码状态，用两个独立代理分别做Standards/Spec审查，比较范围为git diff 2e6594e5d207f4f1798639dad652a9d140f17ef8 HEAD。Standards依据AGENTS和项目约束；Spec依据正式spec、09归档、10接受边界及获批本稿。只审本工单diff，不全面重审06—10。
5. 发现阻塞则在本稿范围内作必要修复、行为测试和定向复审，仍使用相同比较起点；越出批准合同的实质决策另报告，不静默扩权/换请求/改样本。没有预先授权覆盖失败产物或删除证据。
6. 从明确提交状态以唯一CLI生成16视图；独立S2全量重推，验收者核对手算例、实际构造diff和全量结果，不从计划拷贝参考。新空root复现、旧版本保护、一致复用及路径失败核对均须实际完成。
7. 只有以上门禁全部通过才独占写records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json。接受记录另绑定配置/批准、主记录、事实manifest、独立程序/参考/check、外部测试、两轴候选/报告、复现和保护的真实摘要；不回写prepared主记录。接受只意味着异常场景组件通过，不意味着模型、账本、统计充分性或正式联合包通过。
8. 工单12随后处理正式权重、主要比较、K、基础分数/融合、预算/重试/计费、用户内汇总和共享相关性、样本量依据。工单13真实接入08根任务及受限工具。本稿已给两者可直接引用的材料与请求合同，未完成事项不能记为已通过。

## 13. 原始依据复核与本地规则边界

2026-10-15已浏览09使用的以下两个W3C固定版本相关章节；未新增来源、扩展综述或重新审查06—10。两页公开可读。

| 原始依据 | 本次核实的支持范围 | 本项目不能冒称为标准规定的内容 |
|---|---|---|
| [PROV-DM，2013-04-30固定版](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)，§5.1.1、§5.1.8、§5.2.2 | 实体具有固定方面；失效表达实体停止可用；修订是从原实体产生修订实体的派生关系。 | 未规定本项目签发权限、业务头版本、自动替代优先级或Conflict四态。 |
| [VC Data Model 2.0，2025-05-15固定版](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)，§2、§4.9、§4.10、附录A.7 | 区分凭证核验与声明真实性；有效期及撤销状态可以显式表示。A.7为非规范说明，指出过期凭证仍可能有次要用途。 | 未给食品材料统一TTL；§4.9未给本项目整数毫秒的比较公式，不能称W3C强制半开区间。 |

据此继承并明确以下**项目语义及工程选择**，不是两项标准替本项目给出的答案：

1. **R1历史采样事实不加TTL。** 09/10已把R1定义为指定采样及报告的历史结论，不能把材料年龄改写为当前品质。到期资格实验必须采用有显式有效区间、又属于请求必要依赖的当前材料，例如启用R5或R1 AND R5；不相关零售材料到期不影响R1。[VC DM 2.0，§2与A.7](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)
2. **半开区间是本地合同。** 继续使用09的`valid_from_ms ≤ τ < valid_to_ms`，单列起点、终点前1毫秒、终点和终点后1毫秒案例。§4.9用“停止有效的时点”和“信息有效的最晚时点”描述`validUntil`；本稿不把它转述成W3C明定的排他端点。[VC DM 2.0，§4.9](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)
3. **修订关系与独立谱系分开。** 同对象、同声明范围内，经获权主体登记的显式修订链，按本地快照/生效规则选择头版本并保留旧记录。两个无替代关系的谱系，只有在各自对象、采样、权限、时间及原件完整性均可采用，且正反组合都能推出同一命题的相反结论时，才按本地规则构成Conflict；不靠时间较新或跨谱系版本号消解。[PROV-DM，§5.2.2](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)
4. **失效/撤销移除采用资格，不自动生成内容反证。** 排除后只有支持/否定证据都不足才为Pending；另有有效反证时才可能Refuted。PROV的失效只借鉴到业务断言的可用性，不能把仍需审计的原件字节视为“已失效后还能继续使用”的同一PROV实体，也不能推导历史事件未发生。[PROV-DM，§5.1.8](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)、[VC DM 2.0，§2与§4.10](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)

本次复核未得到场景数量、抽取比例、扰动强度、模拟机构独立性、统一有效天数或统计权重的数值依据；这些参数须在本稿中作为有理由的工程建议集中确认，不得包装成文献强制值。
## 14. 一次集中确认点与本轮自检

请对下面J1—J8一次确认，或按编号提出修改。各项都对应本稿已给出的具体规则；没有另留“实施前再补一轮比例/种子/公共接口”的步骤。

| 编号 | 本次需要批准的完整内容 |
|---|---|
| J1 | 第2—3节请求和时间合同：R1历史无TTL；启用R5并组成R1_AND_R5；固定τ/封存/新记录时间；后续联合根任务推荐使用组合请求，R1仅离线语义对照 |
| J2 | 第4节V00—V15矩阵及5.1算法：16视图、同一S、ceil(10%)=150、种子20261015/sha256-order-v1、错配供体、3种组合、1次构造无随机复本 |
| J3 | 第3.3—3.4/6.2节版本与身份：合法替代和独立谱系分开、头失效不回退；第二报告由现有SIM-LAB签发；新增签发者/宽授权均0；仅V11收紧读取 |
| J4 | 第5.2/6—7节数量及存储/格式：自包含快照、约427 MiB复制基数、预计含参考0.6—0.7 GiB；新动作/登记/策略/请求/快照字段及外层完整性和内层异常分离 |
| J5 | 第8—9节Interface和隔离：唯一prepare_data新增stage及两参数、S1/S2返回/错误/发布/复用合同；独立参考不读计划/生产状态；08不改、工具真实接入留13 |
| J6 | 第10节S1/S2测试Seam、H01—H18、A01—A18及全量分布：语义、时间、版本、权限、无关性、隔离、复现、路径和损坏行为全部纳入验收 |
| J7 | 第11—12节允许文件范围、Thesis/标准库、确认归档→TDD→固定2e6594e双轴独立审查→独立全量接受流程 |
| J8 | 后续边界：正式统计权重、样本充分性、基础分/融合/K与模型预算留12，真实根任务与工具接入留13；场景复制不增加独立账户，不启动正式比较 |

可接受的集中答复是“确认J1—J8，按稿进入实施”，也可给出具体编号修改。本轮到此停止，不自动据“稿件已完成”视为授权。

本轮自检：

- 已读取要求材料并继承已验收结论；12类要求全部列入矩阵，合法版本两方向及三个组合另列，共16视图。
- 已给请求/时间/对象选择/比例/次数/强度/种子/重复/共享/数量/存储、公共输出、独立参考、测试与修改范围；工程数值明确不冒充文献要求。
- 已用文档内SHA向量和独立算术核对选择示例、各项行数和存储估算；这些是草案核算，不是实现测试或场景实产。
- 本轮只新增本文件；未落盘正式配置、修改生产代码、写测试、生成批量场景、运行模型或账本。未读取逐账户私有偏好目标或模型结果。
- 交付前21/21个明确保护文件SHA-256及字节数一致，包括论文/研究草案、spec、09—12工单、10接受链、正常六组件和生产入口；Git既有跟踪文件无修改。16个矩阵视图、18个人工例、18项验收行为和8项确认均齐全，8处本地链接全部可定位。

**停止在J1—J8一次集中确认点。**
