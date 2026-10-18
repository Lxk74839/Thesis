# 工单12预算子事项：调用编排、模型绑定与T0前置合同

日期：2026-10-18（Asia/Shanghai）。固定基线：`ac4874c7218ea1a795ddf992a9c23d133766a293`。

**状态：只读诊断与待确认合同已交付；本稿不是正式规格、实现授权、预算冻结或T0接受记录。** 推荐先确认有界批处理与供应商适配的离线实施范围，补齐分词和完整消息计数证据，再按原合同授权T0。当前不能宣布64候选容量可行，也不能冻结可执行预算。

本轮完成标准：复用公开原日志分解调用；提出一个最小主案及必要备选；核验当前官方模型资料；按正式规模联合计算调用、token与费用；写清文件、公共验收接口、T0范围及全部待确认项。唯一写入为本目录Markdown。论文、原有接受记录、代码、配置、环境和上游数据保持只读。

## 1 权威依据与继承范围

已读取AGENTS及三份代理约定、研究草案、修订论文DOCX正文；项目无GLOSSARY.md及docs/adr，不补占位文件。已检查可用工具和技能，模型核验使用OpenAI Docs技能、官方模型页、计数/计费/工具文档；没有调用推理、计数或其他供应商API。

| 依据 | 本轮继承的有效结论 |
| --- | --- |
| [F1—F3独立确认](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md)及[71ef5c9正文](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-final-experiment-protocol-review-20261016.md) | 正式两臂、共同信息、固定队列/停止、完整M锚点及三个评分组件、失败与NA、F2统计；F3只是候选值与验证门。正文SHA-256：`d2b22af021b2e3b7a25046927c122ba653fe52691bc90c964b5f5edf6b7da4ca` |
| [13接受](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket13-acceptance-joint-task-package-0.1.0.md)、[14数据验收](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket14-full-data-acceptance-and-sufficiency-20261016.md) | 正式基础分/安全投影/完整C/关联已接受；320开发、1,283测试；每根C为1,488—1,493；n8=1,111、nQ=1,283。人数门已满足，实际精度和整体充分性仍not_determined，不用旧记录的历史待办重开数据工作 |
| [取证接受](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/evidence-forensics/acceptance-20261017.md) | 共同list/read、32分页/批读、原8生产核验与正常v1 Q转换已接受；每项逻辑计数、真实Adapter请求物理计数、共享根账沿用 |
| [运行器接受](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/recommendation-runtime/acceptance-20261017.md)及[原合同](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/recommendation-runtime/spec.md) | 本地协议、六角色、发布与共享账接受；105例、13公开组合和历史失败直接复用。本轮不重跑。真实provider/model/tokenizer/pricing及execution_budget仍未绑定 |

题目、双模块、六角色、真实谷物评论加同商品SIM供应链、父商品层历史及来源披露继续沿用。完整C、账户划分、原S及150扰动对象、K=10、质量α/β/主比较、F2 family与统计不变。预算不能通过调整这些项目降低。

## 2 调用诊断结论

逐条读取最终`micro/v4`的公开`budget.jsonl`，只统计结算观察中的原生请求，不重复统计reserve行或usage累计快照。[证据表、SHA及源码定位](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/evidence.md)区分了实测、静态推导与未知。

现行S/M在非空C、每候选一页登记和一批读取、无额外分页/重试时：

`N = 5 + Σ_i (2 + L_i + B_i + 1) + P + 2f + e + ρ`

其中固定5次为需求、用户画像、初稿、首次核验、最终提交；每候选另有管理dispatch 1次、追溯`L_i+B_i+1`次、农产品画像1次。L/B是该候选模型实际请求的列举页/读取批数，最后的1是收到工具结果后的模型续轮；P是候选分页等额外工具的请求/续轮增量，f∈{0,1}为反馈修订，e为其他实际模型增量，ρ为失败重试/格式修复尝试。不能把工具续轮归入免费宿主工作。

当L=B=1、P=e=ρ=0时，`N=5+5n+2f`。S使用一个会话身份但仍走这些阶段，不能把S改成一次问答。R两个臂模型均为0，实际取证及程序工作照计。

| 路径 | 本轮从旧日志复核的事实 | 推导及限制 |
| --- | --- | --- |
| 必要臂R/S/M单候选 | 模型0/10/10；S/M各有2个工具请求及3次追溯模型调用 | 相同单页/单批假设下，S/M处理10个合格项需55次；不是10候选实测 |
| 质量M四候选/十二候选 | 25/65次；分别8/24个工具请求，12/36次追溯调用 | 64候选为325次基线；加一次反馈2次和共同重试最多2次为329次。只是该路径推导，额外分页/自选查询会再增加 |
| 库存反馈M单候选 | 12次，较相应常规路径增加修订1次、复核1次；两次不是失败重试 | 不能称为自然反馈有效或节约调用 |
| 必要十二对象例 | 方法是R，处理到第10个合格项停止，模型0 | 不是S/M的十候选或十二调用通过证据 |

质量R/S不属于本次正式付费范围；当前代码结构支持同样的静态调用分解，但没有对应自然模型实测。原12次仅能覆盖上述无额外工作的一候选常规路径；不满足两候选15次，更不支持64候选。保留全部反馈和两次失败余量时，12次连一候选的14次包络也容不下。

另一个独立缺口是载荷：质量4/12候选累计合成输入分别2,135,857/29,426,628 UTF-8字节，单轮最大255,844/1,309,117字节。它们不是token。`_context`反复放入已取原文、全C映射、画像/草案和所有既往输出，角色history又持续重发；仅压调用数不能证明累计token可容纳。

## 3 推荐最小收口：显式申请的有界顺序批处理

推荐主案A：**批上限32个顺序候选，64前缀最多两个批；每批管理dispatch、追溯批计划及读后续轮、农产品画像各有独立模型消息。** 这是待确认的新协议；旧接口只有当前候选list/read，无法直接实现该调用量。

### 3.1 批处理的明确权限

新增封闭工具`acquire_batch`，其计划必须由追溯角色实际生成并通过ModelAdapter返回；S由同一单智能体身份生成相同计划。计划绑定当前宿主游标、批次上限、必要主张、允许材料种类/质量依赖、list页数/read批数上限与停止策略，不允许脚本、任意路径、SQL、目标、gold或自选principal/snapshot。页/读上限必须在执行前有具体非负整数，未绑定就拒绝。

宿主只解释已申请的封闭计划：对当前候选依次调用现有E1列举/读取，再用现有生产核验评估；当前范围闭合且允许推进才进入下一候选。模型可以请求合法子范围或继续取证；未完成就保留Pending/Unassessed及未完成终态，不保证任何自然输出都走最省路径。若再请求一次批或补充工具续轮，该调用必须额外入账。

必要臂在第10个合格项处立即停止，**批内也不得预读第11项**；质量臂处理共同固定前缀64后停止。批只是连续操作的封装，不是先读取32个对象再筛选。R沿用确定性规则逐项取证，没有模型授权计划；各方法同工具能力、同上限，但不要求R伪造模型调用。

批工具内部每个list/read/assess/advance都有原操作意图、actor、回执、原子预留和实际结算；模型的批工具请求与这些子回执绑定。一批不能记为一个免费逻辑单位，也不能把内部物理请求合并称为1次。不得为批处理另建一份预算。批结束返回真实字段/原文及逐项回执给请求角色，模型读后续轮仍占1次。

### 3.2 六角色职责与载荷收口

需求解析仍确认批准条款；用户画像仍定位完整获准H的字段/未知项。推荐管理对每批实际dispatch，并产生草案及最终提交；追溯角色生成合法有界取证计划、消费返回事实并说明未闭合处；农产品画像对本批**每个实际评估候选**提供属性/值/单位/引用、未知及适用质量信息；推荐依据核验实际核对整表并给Issue，管理者最多一次修订后再次核验。宿主只做已确认生产评估和门禁，不能代写这些模型输出。

画像可以一次返回多候选，不能用“模型已处理”标记替代逐候选内容。旧协议逐项复制完整assessment/Q的字段改为引用已发出的评估回执并保留应核对的状态/属性；这是公共输出schema变化，须确认。

去除递归`forwards`与重复状态副本；用带来源message/receipt/pointer的精确字段传递，保留事实值、对象、版本、权限和未知，不引入LLM摘要。完整C与b仍全部可访问，不改召回集；H、S及必要信息权限不因角色收窄，S具M信息并集。需要再读原件时走已计量工具，**只给hash或引用不能声称角色已读原文**。每次实际发送仍计算完整payload，不能只计增量或缓存未命中部分。

### 3.3 调用包络与必要备选

在每批一次计划、一次读后完成、没有额外分页续轮的受控路径中：

`N_A(n) = 5 + 4 ceil(n/32) + 2f + ρ + e`。

四个批内调用为dispatch、追溯计划请求、追溯读后续轮、批画像。零候选另有封闭空输入路径，不套用该公式。额外candidate_page、合法追加计划和格式修复均计入e/ρ，不能藏在“批处理”中。

| 方案 | n=4/12/64的正常调用推导 | 64候选且一次反馈+两次重试 | 采用条件 |
| --- | --- | --- | --- |
| A，批32，推荐 | 9 / 9 / 13 | 17（e=0） | T0验证每批载荷、逐项职责及停止；17不是所有自然轨迹上界 |
| B，批16，必要备选 | 9 / 9 / 21 | 25（e=0） | 若批32的单批消息/输出过大而较小批可容纳，再集中采用；不自动切换 |
| 保留现行逐候选接口 | 25 / 65 / 325 | 329，仍未含额外工具续轮 | 不推荐：仅模型时限包络已需14,823秒加本地工作；token上界未知，不能只改调用上限就称可执行 |

13次基础加2次反馈已超过原12；因此主案即使批处理也需显式提出F1/F3修订。把六角色合并成一个供应商请求再按角色标签拆日志，不是本案。

## 4 联合预算候选与最终预留

以下均为**报价和后续T0评估候选，未证明充分、未写入配置**。A/B对R/S/M共用工具、候选和时间上限；R模型/token/模型费用仍为0。

| 维度 | 原F3候选 | 推荐A | 必要备选B | 依据及未决 |
| --- | --- | --- | --- | --- |
| S/M模型调用 | 12 | 17 | 25 | §3公式；反馈及共同两次失败已包含，不再乘重试系数。e>0照计，超限失败 |
| 累计输入/输出 | 96,000 / 12,000 | 192,000 / 24,000 | 384,000 / 48,000 | A为原分配翻倍的工程报价候选，B再翻倍；不是从字节推导的token上界，也没有充分性实测。真实计数不足就判候选不通过 |
| 逻辑工具 | 2,048 | 4,096 | 4,096 | 完整读取公开质量路径推导64候选已2,053；再计最多1,493候选行、反馈2及批包装2约3,550，4,096留546；异常依赖/失败仍待枚举 |
| 物理工具 | 256 | 256 | 256 | 单页单读64候选为128，完整C最多47页合计175、加2次实际重试约177；异常多页/依赖或失败可能增加，不能称全视图上界 |
| 实际候选前缀 | 64 | 64 | 64 | 完整C仍1,488—1,493；必要首10即停，质量固定前缀不改 |
| 失败重试/格式修复 | 2，共享 | 2，共享 | 2，共享 | 模型与工具合用，不各领2次；一次反馈修订不是失败重试 |
| 根时限 | 600秒 | 900秒 | 1,500秒 | A包络16个普通模型尝试×45+final 60+退避3=783，余117秒给普通取证/程序/setup；B为24×45+60+3=1,143，余357秒。非供应商延迟保证 |
| 单模型请求 | 45秒 | 45秒 | 45秒 | 实际timeout取根剩余与本请求限制较小者；Retry-After若不能容纳则停止 |
| 单请求输入/输出候选 | 未绑定 | 96,000 / 8,192 | 96,000 / 8,192 | 都受根剩余及final保护，final改用下行更小上限；小批备选不借模型更大窗口掩盖累计输入 |
| final模型/输入/输出/时间 | ≥1 / 8,000 / 1,500 / 60秒 | 保留该候选 | 保留该候选 | 完成稿已核验后只提交draft标识及绑定摘要；是否足够仍须完整消息计数与T0 |
| final逻辑/物理 | 待闭合 | 1 / 0，条件性提案 | 同A | 当前final程序1逻辑，commit/seal各0；禁止final补证，故E1物理0。若增加别的外部核验依赖，必须重新计量并修订，不能沿用0 |

2,053的推导为`3初始依赖 +64×(15登记+15原件+1评估)+63推进+3提交/核验/final`，与公开4候选133、12候选389一致；不是64对象实跑。新批包装按每批另记1逻辑，子步骤照计。完整C行只有实际通过分页工具返回时按行计，不将已计过的同一返回再计一遍，也不把未来分页调用免费化。

本案不把“取12份相关原件”当作已经验证的优化。R/S/M只要取了15份就计15份；省略任何依赖必须保留完整性证明。4,096/256仍未覆盖未知异常和任意额外请求，T0逐视图核对，超额就报告不可行。

final 60秒进一步要求：最终模型至多45秒，final/commit/seal三个本地阶段各至多5秒并在总60秒内。现代码把每个程序操作预留45秒，**不能只填60秒数字便当闭合**，需在确认后的适配中细分、强制截止并实测。final只有最后1次模型提交，草案核验与反馈必须在普通阶段先完成；未核验成功不进入final。final预留不是额外额度。

每次模型发送前须同时满足：调用、完整输入上界、全部生成输出上限、费用上界、根时间及final剩余。`max_output_tokens=min(8,192,本阶段上界,根输出剩余−受保护final)`；final不超过1,500。单次最大值不能相乘声称所有轮次都可取满；T0必须另外验证整条受控路径及失败包络。未得到有效完整输入上界时禁止真实发送。

## 5 供应商/模型主案与备选

核验日期为2026-10-18；只采用实际打开的官方页面，详见[来源与计费记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/evidence.md)。

**主案：OpenAI直连Responses API，固定`gpt-5.4-mini-2026-03-17`，reasoning.effort=`none`，Standard同步文本请求。** 选择理由是当前官方列明固定日期快照、函数调用和结构化输出，能直接对齐现有消息Seam。价格较低的新模型不自动满足版本复现要求；此选择不是本任务质量或成功率已经验证。[官方模型页](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

| 项 | 主案 | 必要成本备选 |
| --- | --- | --- |
| 精确API ID | `gpt-5.4-mini-2026-03-17`；不用漂移别名 | `gpt-6-luna`；官方当前仅给该ID，未列日期快照，**不可伪造`-2026-xx-xx`版本** |
| 上下文 / 最大生成 | 400,000 / 128,000 | 1,050,000 / 128,000 |
| 函数/结构化输出 | 支持 / 支持 | 支持 / 支持；本案同样用Responses |
| 推理设置 | 明确none；仍核对全部output usage | 明确none；官方默认medium，不能省略该设置 |
| 每百万USD：普通输入 / 缓存输入 / 输出 | 0.75 / 0.075 / 4.50 | 0.10 / 0.01 / 0.50，限本案单轮≤96k的短上下文；新代缓存写入为0.125，不能漏算 |
| 版本/会计缺口 | 有日期快照；本地完整计数和账户实际访问未证实 | 缺日期快照/不可变版本保证；另需cache_write_tokens会计映射。本轮不选为执行绑定 |

备选能力与ID来自[GPT-6 Luna官方页](https://developers.openai.com/api/docs/models/gpt-6-luna)，缓存写入来自[官方缓存说明](https://developers.openai.com/api/docs/guides/prompt-caching)。若采用Luna，先解决固定版本要求，或明确确认改变其复现保证；不得在S/M间混用或中途静默切换。当前最低工作无需第二供应商SDK或转发平台，因此不增加第三供应商备选。

GPT-4.1 Mini与GPT-5.4 Nano虽有低价，但官方已分别公告2027-01-14、2027-04-01下线，故不选为本轮新绑定主案。[官方弃用表](https://developers.openai.com/api/docs/deprecations)

供应商只提供模型推理；本地取证工具继续E1/E2。禁用托管检索、web/file search、代码执行、供应商子代理和自动上下文压缩。本案无托管工具附加费的前提是这些工具确实未启用，本地取证的逻辑/物理/时间仍照计。[官方价格](https://developers.openai.com/api/docs/pricing)

结构化工具采用strict schema；普通角色输出采用Responses的JSON schema格式，二者分开映射。strict只约束格式，不证明事实/引用/资格正确，仍穿原程序门禁。[工具](https://developers.openai.com/api/docs/guides/function-calling)、[结构化输出](https://developers.openai.com/api/docs/guides/structured-outputs)

## 6 分词依赖与完整计数硬缺口

Thesis环境已存在：`C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis`，environment.yml声明Python 3.13.16；本轮只读检查conda-meta和site-packages，未发现tiktoken、tokenizers、transformers、openai、httpx、requests目录。没有运行Python/import probe或安装。

最小依赖提案仅为`tiktoken`及其必要传递依赖、目标encoding资源；HTTP使用标准库且不自带重试，不要求安装OpenAI SDK。**当前官方文档没有替本项目确认兼容Python 3.13/Windows的包版本、wheel摘要或该快照的encoding映射，本合同不编造一个已验证版本。** 这些精确锁项属于待确认附件，未齐不得安装或声称可复现；encoding资源需显式下载/校验，T0内不得懒加载联网。

更关键的是，官方明确：tiktoken可计纯文本；工具/schema和消息角色边界等存在本地不可见开销。`POST /v1/responses/input_tokens`才接受同完整请求并返回准确输入数。[官方计数说明](https://developers.openai.com/api/docs/guides/token-counting)

因此分三个事实：①原日志字节可准确重数；②锁定encoding后可准确数所传文本的分词；③**本地准确数供应商完整消息仍没有已核验方法/上界**。①②都不能代替③，不能除以4、加经验百分比、套旧ChatML常数，或把JSON文本token数标成完整输入token。

拟新增本地`InputCounter.count(payload)`返回`visible_text_tokens`、`full_input_tokens`或`full_input_upper_bound`、basis、encoding/包/资源SHA、payload SHA及unresolved字段。未知保持null，status=`full_count_unresolved`，不发模型请求、不拿保守占用当精确计数。完整payload包括instructions/角色、完整已发历史、转发字段、函数schema、工具参数与结果、输出schema；缓存输入也全数入累计输入。

在当前已确认“零API、本地准确计数”的T0合同下，这个缺口是**token门硬阻碍**。本轮没有用供应商计数端点补洞，也不宣称该端点免费。后续只能：取得可验证的本地完整编码规则/有证明的请求上界，或在另一次集中修订中明确调整计数验证方式。若改用官方计数API，必须另行说明授权、调用/费用与发送范围，不能混入零API T0。本稿推荐保留原门，先补证。

## 7 正式规模与费用重算

直接继承F1规模：1,283测试账户、主重复1。原8视图各R/S/M一次，Q1/Q2仅完整M一次；质量两个控制在同一锚点本地重排，不重复模型/取证。正式计划为R 10,264根、S 10,264根、必要M 10,264根、质量M 2,566根，合计33,358方法根，**23,094个模型付费候选根**。不按n8=1,111缩池，不另乘六角色、三组件或两次重试。

| 候选 | 模型尝试上限 | 累计输入 / 输出，百万token | 主案无缓存折扣的条件性token费用 |
| --- | ---: | ---: | ---: |
| 原F3 12 / 96k / 12k | 277,128 | 2,217.024 / 277.128 | USD 2,909.844；容量已有已知缺口，不能作为可执行低价方案 |
| A：17 / 192k / 24k | 392,598 | 4,434.048 / 554.256 | **USD 5,819.688** |
| B：25 / 384k / 48k | 577,350 | 8,868.096 / 1,108.512 | USD 11,639.376 |

公式为`N根×(I上限×0.75+O上限×4.50)/1,000,000`。它是**准确输入上界与生成上限被证明并强制执行之后**的纯token数学上界，当前只是候选配置报价，不是实际预计账单或可行性保证。每次费用向上取整到微美元最多另加1微美元：A全局≤0.392598美元、B≤0.577350美元。

主案A的模型费用候选：每付费根至多252,017微美元（0.252美元加17次舍入余量）；final至少保留12,751微美元（8k输入+1.5k输出按无缓存价加1微美元），均包含在根额度中。拟议正式模型池总封顶USD 6,000，覆盖上述约USD 5,820.081包络；不是已批准支出。B若获选，候选总封顶为USD 12,000。两者不同时批准、不相加；未知usage保留占用，不能把余额当可再支出。

Luna仅作成本敏感性：原/A/B无缓存写入时为USD 360.2664 / 720.5328 / 1,441.0656；若全部输入以1.25倍写入价计则415.692 / 831.384 / 1,662.768，再加微美元舍入。这个比较说明版本与缓存会计选择的重要性，不能证明Luna任务质量、访问或版本冻结已经通过。显式缓存模式且不设断点可避免新代缓存写入，但若选该路线仍须核对native usage，不在本轮自动启用。[官方缓存说明](https://developers.openai.com/api/docs/guides/prompt-caching)

不报实测平均费用：当前没有真实调用/token/自然失败率。税费、汇率、任何未来P1、另选区域/服务等级的差价、供应商计数接口费用、本地计算/存储及链实验费用均未纳入上述模型池报价；须在相应执行授权中明确，不用旧USD600填补。工具总配额按33,358根×4,096/256得136,634,368逻辑/8,539,648物理，仅为根限额乘法，不是预测实际工具工作量或其货币价格。

## 8 最小供应商适配与公共接口合同

不引入多供应商注册中心、Agents SDK或另一预算账。既有RootBudget的资源接口保持；新增原生usage细项留在Adapter审计，并在费用内反映。所有新schema独立版本，旧scripted_public 0.1.0及原fixture限制继续有效。

| 公共验收入口提案 | 职责、可核查结果与变更 |
| --- | --- |
| `ModelAdapter.prepare(request)`，新增，纯本地 | 构造实际Responses payload、strict schemas、model/settings，返回wire SHA、计数basis/完整上界、输出cap/费用预留和缺项；缺项不能生成可发送prepared。prepare不发送、不取证、不记一次模型尝试 |
| `ModelAdapter.invoke(request)`，保留方法名、增加显式新版本 | 核对prepared wire与根reservation完全一致，调用注入的唯一sender一次；映射原生function_call/call_id、function_call_output、结构化文本、refusal/incomplete/error及usage；原生/规范化/错误都保留。不得内部重试，真实模式缺能力、完整计数、预算或单独授权即sender前拒绝 |
| `EvidenceSession.dispatch('acquire_batch', plan, actor_role=...)`，新增独立版本操作 | 只解释§3封闭计划，内部复用已接受E1、assess/advance公共入口；逐子操作同账。请求来自实际模型消息、批内首10停止、下一候选闭合与回执关联可从audit验证。旧list/read参数与含义不改 |
| `RecommendationRun(...).run()/audit_view()`，沿用入口、增加新版本binding | 新版本区分离线供应商格式fixture与真实执行；绑定实际request来源及计量basis，不能继续统一标scripted/synthetic或public_fixture_only。新批画像、消息传递和新生产请求R1/R5映射只在新版本启用；旧公开c1/c2协议不放宽 |
| `InputCounter.count(payload)`，新增纯本地 | 按§6输出可证计数及缺口；离线fixture可给字面完整计数用于检查会计，但不冒充真实官方计数证明 |

供应商映射最小字段合同如下；内部request/attempt ID与供应商ID分别保存，不伪造二者相等：

| 原生字段/事件 | 规范化与审计要求 |
| --- | --- |
| 请求`model`、`reasoning.effort`、完整`input`/`tools`/输出schema、`max_output_tokens` | 由prepare固定wire；预留/发送核同SHA，实际返回model单独保存并核对所选快照，不能只记调用时别名 |
| `response.id`、HTTP `x-request-id`、返回model及其他实际提供的版本标识 | 与本地request_id/attempt_id/reservation_id关联；未提供的版本信息保留未知，不补造system_fingerprint或日期版本 |
| `output`中的`function_call`/`call_id`/`name`/JSON `arguments` | 映射为原生工具请求，逐个检查；只允许已绑定schema及宿主授权的当前游标/批计划。工具结果由对应`function_call_output`送回原call_id，下一次Responses请求另计1次 |
| 文本结构化结果、refusal、`status`与`incomplete_details` | 按新output_kind封闭schema验证；拒绝、截断或未完成不得作为成功草案，原始响应及实际usage仍保存 |
| `usage.input_tokens`、`input_tokens_details.cached_tokens`、`usage.output_tokens`、`output_tokens_details.reasoning_tokens` | 主案映射为总量与子集，验证整数及包含关系；保留原生usage，不从可见输出反推。备选若涉及`cache_write_tokens`则另校验输入三类别之和 |

如果缓存等必需计价子项缺失，实际费用保持null；允许按无折扣上界保留占用，但不能把上界标成已结清实际费用。sender不内置SDK/HTTP重试或重定向后的再次模型POST；每次实际模型请求都由宿主另建意图并消耗同一根调用额度。原生响应fixture只验证映射，不证明供应商账户已访问或消息计数已准确。

真实请求的业务clauses必须从已接受JointSession/设计请求绑定映射，不能把公开夹具c1/c2或fixture标记直接搬到开发任务。运行器当前preflight锁scripted_public、fixture、execution_budget=null，模型ID=null、输出100,000、费用0及provenance硬编码；都需新版本显式处理，单加HTTP函数不能上线。原`advance_action`的fixture_only边界保持。

主案usage：`input_tokens`总量含缓存；`output_tokens`总量含reasoning及格式生成，细项不重复相加。`cached_tokens≤input_tokens`、`reasoning_tokens≤output_tokens`。费用为`[(I−C)×.75+C×.075+O×4.5]`微美元；input=100/cache=40/output=30/reasoning=20时为183微美元，累计输入/输出是100/30。即使none且reasoning=0，输出也可能含不可见格式token，不能按可见文本计费。[官方生成计数](https://developers.openai.com/api/docs/guides/token-counting)、[推理计费](https://developers.openai.com/api/docs/guides/reasoning)

HTTP状态不是零费用凭据。格式失败、拒绝、截断但有有效usage时照实际计量；已发送而timeout/断连/5xx、usage缺失时调用照计、token/费用占用保留并停止，不免费重试。发送前本地拒绝的模型尝试为0。官方错误文档没有给这些错误逐类确定的统一收费/退款承诺，**失败最终金额未知**，只能按后续权威回执/账单结算，不写“失败均免费”。同一尝试晚到回执不得重复扣账，也不得恢复发布。[官方错误](https://developers.openai.com/api/docs/guides/error-codes)、[官方逐运行费用控制示例](https://developers.openai.com/cookbook/articles/per_run_spending_controller_responses_api)

## 9 文件范围、依赖与实施门

本轮只新增本目录`spec.md`、`evidence.md`、`confirmation.md`、`map.md`、`issues/01-budget-binding-and-t0-contract.md`；不回写工单12、正式spec或既有map/接受。

确认后的离线实施候选白名单如下，**不是本轮写入许可**：

| 类别 | 候选文件范围 |
| --- | --- |
| 既有生产的最小修改 | `recommendation_runner.py`（新版本编排/画像/载荷/真实绑定）；`model_adapter.py`（prepare及native校验/usage/来源）；`evidence_access.py`（新批操作、逐子回执/预算及已绑定的程序时限）；不更改E2资格语义 |
| 新生产 | `provider_openai.py`（单一Responses映射/无重试sender）、`token_counting.py`（本地计数/缺口）；不建通用供应商框架 |
| 依赖 | 独立`requirements-model.lock`及最小environment.yml关联；必须先确认精确版本/encoding资源/轮子与传递依赖SHA。当前锁项未齐，不能直接安装或更改Python版本 |
| 公共测试 | 新`tests/test_provider_openai.py`、`tests/test_token_counting.py`、`tests/test_batched_recommendation.py`及`tests/provider_fixtures.py`；旧测试只读，新测试穿上述公共入口 |
| 守护/交付 | 本目录将来的`diagnostics/run_check.py`、`protect_scope.py`、`check_delivery.py`与`verification/`；本地审计复用现有允许根`data/recommendation-runtime-audit/<新轮次>/`、公开临时根`.tmp/recommendation-runtime/<新轮次>/`，不覆盖旧路径 |

上述文件名均相对于`C:\Users\Kane\Documents\CodexProject\Thesis`。joint_access/joint_tasks/evidence_verification/quality_fusion/recommendation_actions、config、数据/原S/账户、论文/研究、旧接受与工单15继续只读。若实际实现需要改白名单以外接口，先集中列出事实及最小修订，不解除旧fixture限制或绕私有入口。

离线实施的本地资源提案为另立一次累计1,800秒Python/4GiB进程树（含64MiB守护）、外部API/费用0；与下节原T0的1,800秒上限分别记账，不能把新目录当作旧账清零。确认依赖及实施授权后，所有项目命令显式使用`conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -B ...`。本轮项目代码/测试/构建/安装执行0。

## 10 直接继承的T0范围及前置门

直接引用已确认[71ef5c9正文§10](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-final-experiment-protocol-review-20261016.md)：

> 全开发枚举：320×(原8+Q1/Q2共10视图)×R/S/M三个公开脚本策略，最多9,600份依赖/预算清单及受控消息计数；不逐份重放整条动作链，不读目标，不评价推荐优劣。

> 极值工程回放：每视图/策略分别取逻辑闭合量、物理请求、累计输入token最大的开发根，并列按root UTF-8字节升序；去重后最多90根。每根冷/热缓存各一次，最多180次，再加最多12个新真实接口公开故障夹具，共不超过192次实际脚本回放。

> 拟沿用Thesis、30分钟累计本地计算/4GiB；超限保留已完成覆盖并报告验证未完成，不自动扩范围。

该范围已经确认，本轮不重定账户、视图、选择算法、次数或资源，也**不执行T0**。质量R/S在T0中是技术策略覆盖，不成为新增正式付费实验。若实施中的公开故障例已满足T0所需同接口/精确版本证据，按绑定复用，不为凑12次重复回放。

| 门 | 开始前必须具备 | 当前状态 |
| --- | --- | --- |
| G0 设计变更 | 一次确认本稿批处理/F1/F3/新公共schema及文件范围，原实验设计其余不重问 | 待确认 |
| G1 离线适配接受 | 新版本public tests、native fixture映射、批内停止/会计/隔离、旧接口必要兼容；固定ac4874c起点和精确候选审查证据 | 未实施；旧105例/13组合直接继承 |
| G2 模型/完整计数 | 模型/设置/价格/版本、精确依赖资源锁；本地完整计数或经确认的有效上界；非字节估计 | **完整消息计数仍硬缺口，不能报通过** |
| G3 T0执行授权 | 原9,600/192/1,800秒/4GiB范围的一次明确授权及新累计账；API sender禁用/联网生成0 | 本轮未授权执行、未运行 |
| G4 T0结论 | 全覆盖；计量/隔离不变量零违例；全开发清单不超候选；极值正常路径闭合且在枚举上界内；所有故障停住并保账；候选/每种终态/失败都报告 | 未运行；拒绝超限测试通过不能替代容量通过 |
| G5 执行冻结/支出 | G2/G4闭合后另写预算冻结与实际总模型池授权；真实延迟/自然完成率如需证明，另立有总额的P1 | 未冻结/未批准；P1、链部署与15不在本合同授权中 |

T0报告需按方法/视图给全部清单数量、输入/输出/逻辑/物理/时间预留P50/P95/max、超限数及原因；极值回放墙钟/内存/冷热缓存另列，未知不进数值分位数并报缺项数。最差根选择依据必须是可证完整输入量，不能在G2缺失时改用字节选择“token最大根”。没有完整计数时只能报告部分技术事实，不算原T0整体完成。

## 11 公共验收接口与人工判定

后续只新增变化对应的公共行为测试及必要影响回归；不重跑已接受全库、公开组合或上游生成/评分/组包。不读取正式测试推荐表现。人工期望先来自本合同/公开原件，不能调用生产实现生成答案。

| 编号 | 公共入口与必要断言 |
| --- | --- |
| H01 | prepare：相同native payload同hash；角色/工具/schema任一变化进入完整计数；计数未知在sender前拒绝且attempt=0 |
| H02 | invoke：严格工具调用ID/参数/返回和结构化输出逐项映射；拒绝、incomplete、畸形JSON、错误/迟到原件保存；每个发送尝试可定位 |
| H03 | invoke+RootBudget：100/40/30/20例归一化100/30、183微美元；重发全输入重计；未知usage保占用、停根、不得重试/发布；舍入及同回执补结算无重复扣费 |
| H04 | batch+run：公开12对象必要臂第10合格即停，11/12原件访问0；质量臂仍按宿主固定前缀；跨根/游标/权限/快照计划拒绝。完整C与S/账户/质量主点保持 |
| H05 | batch+audit：每个内部list/read/assess/advance有同根回执，32页/读上限保持，逻辑逐项、物理逐实际Adapter请求；部分失败不能继续越游标、候选不重计、不换账 |
| H06 | run：六角色实际完成向量、管理调度、追溯申请及续轮、每个已评估候选画像、Issue→修订→复核均可查；S同能力单身份，R模型0。公开4/12批路径推导9调用作为新断言；这是新接口测试，不重跑旧25/65组合 |
| H07 | run+ledger：一次feedback+2次失败仍共同≤17；额外页/续轮有真实增量，超过上限停，不伪造17次普适完成。token、工具、候选、时间任一超限都有独立终态 |
| H08 | final：普通阶段不能挤占1调用/8k/1.5k/1逻辑/0物理/60秒/费用预留；final禁止补证，三个本地阶段有界；提交/封存失败不发布；组件同A/G/终态、失败共同anchor_failed |
| H09 | Counter/依赖：包/encoding/native schema版本与SHA匹配；缺完整结构规则保持null；不能把纯文本精确、fixture字面计数或历史字节转成官方完整计数接受 |

本轮自检：调用与字段复核来自旧公开账；正式规模与新费用为可复算算术；官方能力有直接链接；分词/失败计费/自然运行未知明确保留；全部修订与许可项见[集中确认表](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/confirmation.md)。本轮没有新的代码测试通过、自然模型完成率或容量接受结论。
