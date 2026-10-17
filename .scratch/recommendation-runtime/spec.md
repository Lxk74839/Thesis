# 推荐运行专项第一阶段：R/S/M运行器与六角色适配最小实施合同

日期：2026-10-17（Asia/Shanghai）。状态：**待集中确认的实施合同；本稿不是实施授权、执行配置或接受记录。**

固定BASE：`6ac5c2cddde6973b9743e3e17f5c264840f42854`（`6ac5c2c`）。审核开始时HEAD等于BASE、工作区干净。项目根为`C:\Users\Kane\Documents\CodexProject\Thesis`。

本轮受命交付合同、[集中确认表](confirmation.md)和[专项工单01](issues/01-rsm-runner-and-six-role-adapter.md)，仅新增本目录四份Markdown。确认后，直接实施本合同§9的本地代码、公共TDD、最小公开联调及独立审查范围。真实供应商绑定、T0/P1、真实任务推荐、付费调用、效果统计、链部署及工单15冻结继续保留各自门禁。本轮不执行这些工作。

## 1 依据与验收对象

已只读读取项目AGENTS及代理约定、[研究草案](../../research/数据修复方案与验收草案_20261010.md)、[修订论文](../../manuscript/论文初稿_表达与实验结构修订版_20261010.docx)的正文/表格/公式、下列确认与接受链及实际Interface。研究草案和论文中的早期参数不替代已确认F1—F3。未全面重审上游、未读取正式测试推荐表现。项目无GLOSSARY.md或docs/adr，不新建占位文件。

| 直接继承的权威来源 | 本合同采用的内容 |
| --- | --- |
| [F1—F3确认](../data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md)及[精确正文](../data-preparation/ticket12-final-experiment-protocol-review-20261016.md) | 两臂、R/S/M同信息、固定队列/停止、同A/G/终态组件、整表门禁、NA/失败、候选预算及后续验证门。正文SHA-256为`d2b22af021b2e3b7a25046927c122ba653fe52691bc90c964b5f5edf6b7da4ca` |
| [09确认](../data-preparation/issues/09-evidence-protocol.md)及其C1—C11正文 | 对象/批次关联、相关授权范围完成、四态、版本/撤销、历史事实与当前断言、请求来源 |
| [13联合准备接受](../data-preparation/ticket13-acceptance-joint-task-package-0.1.0.md)、[14数据层验收](../data-preparation/ticket14-full-data-acceptance-and-sufficiency-20261016.md) | 正式基础分、安全投影、完整C/批次映射和独立参考关联已接受；不重做数据准备/评分/充分性讨论，不把历史记录的待办状态当成当前缺口 |
| [受限取证专项接受](../evidence-forensics/acceptance-20261017.md)、[其合同](../evidence-forensics/spec.md) | 共同list/read、32分页/批读、实际A、原8异常生产核验、正常v1 Q转换及既有计量已接受，直接复用 |
| [离线动作Interface](../data-preparation/ticket12-offline-interfaces-20261016.md) | `advance_action`仍仅接公开确定性fixture；不能解除其模型/token/费用零值限制来承载新运行器 |

论文题目、双模块和六角色保持不变。真实评论停在父商品层，SIM事实/来源明确披露。模型不读取目标、独立F/gold、参考适用掩码、扰动名单、私有路径、分区、旧答案或全体评价评论。F2统计实现与实际效果不属于本专项。

本专项可接受的结果分三层：①运行协议和共享根账；②公开脚本Adapter与真实本地文件取证的组合；③真实供应商/自然模型轨迹。下一步仅可验收①②，③保持未绑定/未执行。公开脚本中通过的M结构不等于真实M或协作收益已经接受。

## 2 最小Module、Interface与Seam

采用mattpocock-skills:codebase-design的Module、Interface、Implementation、Seam、Adapter、Depth用语。调用者跨小Interface完成整个运行，游标、权限、计量与发布检查集中在Implementation，避免每个角色各写一套。

| Module / 公共Interface提案 | Seam、职责与测试能力 | 明确不覆盖 |
| --- | --- | --- |
| `recommendation_runner.py`：`RecommendationRun(binding, *, evidence, model, root_budget, output_root)`；`run()`、`audit_view()` | 运行Seam P1：一个实例完成一个方法根运行，返回终态/交付/组件记录；只读审计视图给出消息、A/G、游标、草案、Issue、修订与根回执。真实调用方与测试使用同一入口 | 不准备数据、不计算独立参考/指标，不提供任意事件注入、外部发布、CLI批跑、断点恢复或模型注册中心 |
| `model_adapter.py`：`ModelAdapter(transport, *, capability_binding)`；`invoke(request) -> response`，含封闭消息/响应校验 | 模型Seam P2：宿主构造安全请求；Adapter校验并传递模型消息、工具请求、usage及错误。测试侧脚本/故障transport返回本合同原生响应格式，供应商transport及其映射后续另绑定 | 不读文件/证据，不执行工具、不调度角色、不维护第二份预算；没有默认供应商、模型ID、SDK或联网实现 |
| **最小扩展**`evidence_access.py`：`RootBudget(binding, limits, final_reserve, *, clock, journal_path)`；`reserve(operation, upper_bound, *, phase, retry_of)`、`settle(reservation_id, observation)`、`audit_view()`；`EvidenceSession(..., root_budget=...)`可选注入 | 根账Seam P3：现有取证、跨候选、所有角色、模型、程序操作、重试和最终预留共用一账；E1接入同一原子预留/结算路径。journal_path由宿主绑定本run独立目录；根账保留在既有取证Module，不再拆通用计费框架 | 预算为宿主输入；不将F3候选变成默认执行值，不通过新建会话重置额度 |

`evidence_verification.assess_evidence/rank_acquired_quality`、`quality_fusion.rank_quality`和`joint_access.JointSession`直接复用，不修改其语义/输入指纹。新运行器独立导出运行消息与工具schema版本，不修改13历史`tools=[]`投影。P1保存状态所需的记录结构留在运行器内，不为每种事件/角色创建浅Module。

P3是本轮必须显式确认的宿主扩展：BASE的`EvidenceSession`已能`advance_current()`，但其账只含logical/physical/candidates/retries/elapsed，模型调用/token/费用及最终操作未接入；其普通操作始终保护final_reserve，尚无正式消费最终预留的路径。不能在运行器另记模型账、借用fixture账，或直接调用私有`_execute/_dispatch`绕过。既有E1公开调用形式、返回含义、计量人工例和默认独立会话行为须兼容；注入模式的旧usage视图由同一根账投影，不能形成可分叉副本。

宿主先创建RootBudget并开始根时钟，再构造本根事实source/EvidenceSession与运行器；根、limits/reserve、时钟和journal/output目录必须一致，注入不一致即拒绝。Adapter的transport是唯一外部模型依赖，公共测试穿`invoke`校验，不另测私有归一化函数；未绑定真实transport时不能把脚本transport标为供应商。

## 3 R/S/M运行协议与角色合同

### 3.1 共同信息和控制权

每方法绑定同一根H/S/完整C、批准请求/来源、正式b及摘要、业务候选—批次映射、K=10、臂/融合规则、事实快照、principal、SIM核验时点τ及工具版本。取证队列固定为b降序、父ID UTF-8字节升序；完整C仍保持13原顺序，不用候选前缀代替完整候选。每方法独立冷启动一份根账/事实缓存；M六角色共享本根缓存和已取得事实。

模型得到13安全投影及既有工具的安全结果，不接收宿主完整binding、audit_view、来源文件路径或私有总清单。初始投影、完整C可访问性、H原文及获准背景计数不因角色删减；S具有M所有角色可用信息的并集。M按职责组织消息，必要事实可经宿主转发，转发/重发载荷照计输入。模型请求schema只注册`candidate_page(order,cursor)`、`list_evidence(cursor)`、`read_evidence(evidence_refs)`，沿用32页/批上限；身份、当前候选、快照和actor由宿主绑定，工具参数不能自选。未取得原件不因登记存在或setup已扫描而进入模型事实。

宿主决定固定队列推进、生产评估、实际G、预算及最终发布；模型提出当前候选内的合法请求、分析、调度和草案。角色输出不能覆盖请求条款、b、权重、α/β、材料状态或运行上限；固定库存软偏好来自实验设计，画像不把它重写成历史用户真实要求。不开放跨候选预取、文件浏览、托管检索、供应商子代理或额外LLM裁判。

### 3.2 方法

| 方法 | 实际运行行为 | 可核对证据 |
| --- | --- | --- |
| R 完整规则 | 经相同E1列举当前候选登记，按09规则补齐必要条款相关原件/事件/版本/动作，按依赖关系及ID稳定顺序读取，直至相关范围闭合或失败。调用已接受生产核验，再依规则准入/推进；说明模板仅引用实际取得字段和安全目录/H | 工具原字节、完成性、四态、实际G、程序操作及模板理由；模型调用/token始终0。不能按单条pass、私有参考或字符串捷径筛选 |
| S 多轮单智能体 | 单一会话身份承担六类职责；可多轮工具交互、自检并响应同口径Issue，信息与工具能力等于M并集。使用与M相同的未来基础模型/设置及根上限，不限定一次问答，也不强迫花完额度 | 原始模型请求/返回、连续上下文、工具回执、前后草案和至多一次反馈修订；实际用量独立记录 |
| M 六角色 | 六个既定角色均有可追踪的Adapter请求/输出，推荐管理发调度指令，生命周期追溯提出受限取证请求，核验角色反馈。宿主执行调度并登记谁提出、谁执行、结果送往谁；至多一次Issue驱动的反馈修订周期 | 六角色实际完成向量、消息父子关系、调度/工具回执、Issue→修订对应及最终提交。失败可只完成部分角色，不能补造其余消息或称M成功 |

工具的每个供应商续轮、失败请求、格式修复都计一次真实调用；一次模型请求的多个工具调用分别逐项/逐Adapter请求记账。F1的M默认7调用、修订最多再3调用及根候选12调用继续是**尚未验证的编排/容量目标**，不是把7个阶段或六个角色算成7次的许可。正常路径若需更多工具续轮，必须显式暴露调用缺口并受共同上限拒绝；不能用宿主自动执行未申请的取证、隐藏请求或增加额度填平。下一步公开微型联调不证明64候选在7/10/12调用内可完成；真实载荷/容量归T0验证，改变F1/F3须另行集中修订。

### 3.3 六角色输入输出

每条角色输出都引用输入message/receipt，带`role_message_id`、run/session、当前候选/主张范围和生成来源。以下是封闭输出类别；角色文字不赋予新权限。

| 既定角色 | 输入 | 输出及约束 |
| --- | --- | --- |
| 需求解析 | 批准的请求原文、必要/一般偏好结构、来源和共同规则 | 条款/属性对应及歧义说明；必须与批准结构一致，不自行启用新条件/阈值 |
| 推荐管理 | 任务控制的安全摘要、分析结果、实际A/G摘要、剩余预算、可见Issue | 绑定当前候选/主张/接收角色的dispatch；草案/最终提交及修订申请。不能直接改G/游标或发布 |
| 用户画像 | 完整允许H、S、静态目录和批准b规则 | 有H字段定位的偏好说明/未知项；不学习新权重、不读取目标或其他评价账户记录，不重算已接受b |
| 农产品画像 | 白名单候选资料、当前候选实际A及生产评估/正常Q结果 | 属性/单位/值及证据字段对应，缺口和未知；目录标题不冒充批次检验/库存证明 |
| 生命周期追溯 | 管理调度、当前候选/主张、已有ref/游标、实际技术结果 | 闭合schema的工具请求及收到结果后的追溯说明/未完成范围；每份材料带回执，不以角色复述增加独立证据 |
| 推荐依据核验 | 原样草案、批准请求、实际A/G、生产核验和引用 | 绑定draft/candidate/claim/pointer的Issue、阻塞标记和允许动作；不替草案改字，不让模型自报Supported代替生产准入 |

宿主记录实际调度图而不强制虚构固定消息数。默认流程覆盖需求/画像、管理调度、追溯、草案、核验与最终提交；工具续轮按需要穿插并实计。S在单一身份完成同样能力，R用程序完成同样事实流程，不伪造其六角色模型消息。

## 4 宿主状态、游标与终态

### 4.1 唯一运行实例

计划方法键为`(root_task_id, 材料/请求/臂绑定, method, repeat_id)`；`run_id`是不透明且唯一的实际运行实例，另记`execution_kind=scripted_public|provider_real`。角色、候选、工具续轮和重试只有子ID，沿用run_id/root预算；重建模型上下文不得重置根账。重新跑不是重试，不自动新建run_id再取得额度。本次不实现进程重启续跑；中断保留未结算项并以未完成/失败报告，不能恢复成干净根。

| 状态组 | 必须保存的字段/不变量 |
| --- | --- |
| 固定绑定 | BASE/实现候选、合同/提示/工具/Adapter版本与摘要；root/run/method/repeat/臂；完整C、b及摘要、批次映射、H/请求指纹、snapshot/principal/τ；模型绑定与执行授权状态 |
| 队列进度 | `queue`及摘要、`cursor`（下一未完成位置）、`current_candidate`、不同已进入候选、每对象评估及完成性、停止条件/原因；与E1实际当前候选一致 |
| 实际A | E1实际返回的登记/原件/上下文/动作范围、字节/字段定位、成功/拒绝/缺件/失败观察、来源及receipt；setup/未执行不算取得事实，迟到原字节留在实际A并标halted，不进入可发布采用范围 |
| 实际G | 只由显式`assess_current`得到Supported、eligible且advance_allowed的候选准入记录；含assessment/receipt、队列位置、冻结版本；预取/评分器raw_eligible或模型判断不扩G |
| 消息/工作 | 模型原始/规范化消息、调度、工具请求/结果、草案及parent_draft_id、Issue、可见反馈、修订old/new及Issue对应、feedback_round∈{0,1}、pending和根预算回执 |
| 终态/发布 | `terminal/reason/stop_reason`、角色完成向量、范围是否闭合、未结算用量、整表gate结果；唯一发布记录包含实际列表/理由、draft摘要、A/G/游标/终态锚点、预算结算及提交结果 |

`assess_current`未允许推进时原地处理或失败；不因看到Refuted/Conflict/Pending字样就跳过未闭合范围。合法且已尝试完成的缺件/否定/冲突可拒绝后推进；Unassessed不能改名Pending跳过。每次推进必须经过既有`advance_current()`；宿主不修改E1绑定字段。必要臂凑齐10个G后不再调用advance/read/list；质量臂只在固定前缀末尾停止。

### 4.2 停止与发布资格

必要臂：首10合格即停止取证；不足10继续到完整C、候选上限或其他根限制。正常达到完整C或批准候选前缀、且没有其他失败，可以发布G的合规Top10或不足10列表。

质量臂：处理`min(L, |C|)`的固定共同队列前缀，再冻结A/G/游标，不在首次10合格时早停。`L`是待预算验证并批准的数值；64仅为F3候选，生产L不默认赋值。公开人工例的小前缀仅是测试输入。达到计划前缀与资源中断不同：资源中断不能事后改称计划停止。

| 终态 | 判据与发布 |
| --- | --- |
| `released` 成功发布 | 正常停止条件成立、全部必要角色/工作完成、最终整表门禁通过、根账确切结清且交付记录原子提交。非空列表须等于实际G按批准评分得到的TopK |
| `valid_empty` 合法空 | **完整C**逐项评估闭合且没有合格项（C本身为空也可），完成预算/整表空证明及记录提交。局部G空、处理完非全C前缀或预算用尽均不足以证明 |
| `incomplete_budget` / `incomplete_deadline` 未完成 | 资源/时间导致预定流程未完成；实际A/G/当前候选保留，delivered为空，无成功发布 |
| `blocked_evidence` 门禁阻断 | 流程有提交但整表资格/理由/引用/顺序/数量等门禁不通过；保留attempted_delivery及Issue，delivered为空 |
| `failed_protocol` / `failed_model` / `failed_source` 失败 | 身份/状态/来源不一致、模型/工具协议不可恢复、供应商错误耗尽可用恢复、持久化失败或无法结清usage等；保留具体子原因、成本和失败尝试，无成功发布 |

没有启动或记录丢失属于计划执行未完成，不能合成一条成功/NA/零分运行记录。启动后的失败/未完成/阻断按F1在参考适用处计0；独立参考IDCG=0仍为NA。本运行器仅导出终态，不读取参考或计算这些指标。局部空输出单列`empty_unproven`原因而不接受valid_empty；失败与实际违规输出分开记录。

一次反馈周期从首次已核验草案的Issue送达开始，可包含当前未完成候选内的合法补取、画像更新及草案修订，最后重核。已经关闭的游标不倒退，不允许反馈重开已处理候选、扩大冻结前缀或给其他候选免费补证；关闭后暴露的材料缺口导致相应阻断。草案理由纠错可使用已取得A。第二组Issue不触发第二周期，直接交最终程序门禁；无Issue时不强制制造修订。格式错误重试另占共同重试额，不增加反馈周期。

## 5 共享根预算与最小宿主扩展

根账九维沿用`model_calls/input_tokens/output_tokens/logical_tools/physical_tools/candidates/retries/elapsed_ms/cost_microusd`。每个R/S/M方法根一份，跨候选/六角色/Adapter/程序步骤共用同一身份及同步锁。生产limits/final_reserve必须由宿主显式提供并验证；本阶段`execution_budget=null, execution_authorized=false`，不修改13记录。

| 事项 | 预留、结算及失败合同 |
| --- | --- |
| 工具/程序 | 沿用接受的按事实条目逻辑、按实际Adapter请求物理；候选分页、初始依赖、缓存返回、失败项、assess/advance均照原口径。submit/verify/patch/final各实际程序操作1逻辑；消息传递本身不重复按工具事实计，随后模型输入载荷仍计token |
| 候选 | 沿用E1实际进入当前候选取证的口径，根内去重计一次；只看到候选页不计处理候选。新进入时预留候选单位，实际发起取证请求即计，已发起的失败也保留；入场前拒绝/未尝试为0。无实际取得/尝试的assess仍是Unassessed，不能借它跳入其他候选 |
| 模型 | 每次实际Adapter执行尝试预留1调用、完整请求输入上界、包含推理的输出上界及费用上界；工具结果、system/schema、角色互传、历史重发均计累计输入。校验前拒绝未invoke为0调用；执行后超时/拒绝/格式失败同样留调用和已知用量 |
| token/费用 | 保存供应商原始usage及规范化值、计量来源/精确性；cached input若为input子集不重复相加，reasoning若已在output总量中不重复相加。计费独有维度另留原字段，不能假定免费；整数microusd采用已绑定官方规则的保守舍入。没有模型/分词/计费绑定时真实模式在调用前拒绝 |
| 原子守恒 | 普通操作入场须满足`used + held + final_reserve <= limits`各计数/费用维度；时间用同一单调deadline。settle只可消费一次reservation；明确未发生部分才能释放。回执记held/settled/released/unresolved和根前后状态；拒绝操作不偷清已有占用 |
| 未知usage | `null`不填0；已知模型尝试/物理请求先结算，未知部分保留最坏占用并标记未结清，停止新工作/自动重试，最终不能成功发布。只有同请求权威回执可补结算，不能用字节/4或可见文本长度猜隐藏推理/账单 |
| 重试/格式修复 | 工具、模型、角色共用根retries；新attempt引用retry_of、根不变，1/2秒退避及失败成本照计。禁用SDK自动重试；只恢复受允许的传输/格式问题，不因结果不满意重抽。换参数顺序/拆批/重建会话不能绕过既有失败续接计数 |
| 时间/迟到 | 从根输入就绪开始，用真实单调时间计setup、角色、工具、等待/退避、门禁及提交；τ不是墙钟。共享事实结构索引setup另报字节/文件IO，内容不自动入A，不能把setup移到账外缩短根时间。迟到结果保留在实际A/回执并标halted和实际超额，不再用于发布或扩大G、不推进游标、不启动新工作 |
| 最终预留 | 普通阶段保护预留；只有受信宿主在合法结束取证后切换final阶段，消费剩余预留做最终模型提交/程序门禁/记录提交，模型工具不能自选final。失败时只作有账的失败封存，不借final继续取证挽救结果；预留不足则未完成，不能免费finalize |

根账预留/关键意图在真实副作用前写入本run审计日志；异常、中断保留未结算意图。单进程顺序调度，不建设分布式账或恢复框架。实际超额不裁剪为上限，也不先标成功再补账。日志不能提交/回执不能持久化时不发布。已有本地摘要仅用于一致性/定位，不宣称对恶意宿主认证或链确认。

F3仍为候选：2048逻辑/256物理、64候选、2重试、600秒、单请求45秒；S/M各12调用/96k输入/12k输出，M六角色合计；最终至少1调用/8k输入/1.5k输出/60秒在总量内，R模型/token预留为0且保留程序时间。最终程序逻辑/物理预留待T0逐依赖闭合，不填0略过。当前无可执行模型/费用上限；本地测试的字面limits只验证守恒/拒绝，不能改名正式预算。

## 6 排序、理由、反馈与整表发布

必要臂只在实际G按固定b排序；α=1、D空。质量臂只用同A转换所得z/m/q及显式实际G，继承已接受正常v1范围、固定分母和稳定排序；不扩展非空复杂动作scope。已取得但未准入对象可按原合同参与完整C的raw q/mean分母，不能因此进G或发布列表。

草案必须包含有序`items`、每项父商品/批次、逐条理由主张及引用。引用绑定`evidence_ref/receipt_id/target_id/version/pointer`，目录/H说明引用安全投影字段；数值、单位及来源SIM保留。**最小发布理由采用封闭原子主张**：必要检验组合、在售、质量臂库存及获准目录/H偏好说明；每个可发布句子对应已定义谓词/值/单位和模板形式。模型提交原样句子和结构，程序只比对/接受/拒绝，不替模型选引用、补字段或生成修复文本；任意自由扩展的品质/安全/现实信任断言不在本次可发布语言范围。模型的自由分析保留在审计消息，不能混入正式理由逃过核验。R使用同样可核对的模板形式，S/M可选择主张、值和引用。

最小草案形态为`draft_id/parent_draft_id/items`；每item为`parent_asin/sim_batch_id/reasons`，每reason为`claim_id/kind/value/unit/text/citations`，未知/多余字段拒绝。至少包含前两种必要理由，质量库存理由只在同属性z=1时可选；其余理由只能采用下表，暂不增加任意历史概括句式。R与S/M提交同一形态，程序按以下字面规则核对text而不生成替代text：

| reason.kind | 值、引用与原样句式 |
| --- | --- |
| `inspection_supported` | value=true、unit=null，引用实际可采用的采样/报告组合及关联依赖；c1须生产Supported且完成。text=`检验必要条件有完整有效支持（SIM）。` |
| `on_sale_supported` | value=true、unit=null，引用实际零售在售原文/时间字段及关联依赖；c2须生产Supported且完成。text=`核验时点的在售必要条件有完整有效支持（SIM）。` |
| `retail_stock` | value为实际`/facts/stock_units`的非负整数、unit=`units`，引用同一零售库存字段及必要依赖；同属性支持。text=`可售库存为{value}单位（SIM）。`，value用十进制整数 |
| `base_preference` | value为绑定b、unit=null，引用安全候选投影的base_score及其输入指纹；text=`偏好基础分为{value}。`，value固定12位小数。该句只说明固定基础分，不声称学习收益或现实品质 |

Issue至少有`issue_id/draft_id/candidate/claim/pointer/code/blocking/allowed_actions/verifier/source_receipts`。保留首草案、模型核验意见、程序问题、管理者看到的Issue、实际请求/返回、修订old/new及父子草案。模型核验与程序核验意见分开；模型核验不得替代机械门禁，程序不得在后台修正模型草案。本次不实现M−F/M−A自然消融或把脚本改字例当反馈收益。

最终门禁一次检查**整张提交**：绑定/角色完成/合法停止与范围；ID唯一、全在C、批次正确、数量≤K；每项属于实际G；实际A的对象/同属性/权限/摘要/时间/版本和引用路径一致；全部理由符合封闭合同；列表逐位等于批准排序的G TopK；根预算、预留、usage结清及日志/发布记录可提交。K外坏尾项、重复、超长表同样阻断，不截掉再算成功。门禁只读冻结A和安全输入，无文件/工具补证、无模型调用、不改理由或重排草案。发布门禁通过后独占新建发布记录，提交成功才置released/valid_empty；重复run_id不能覆盖旧交付。

质量组件锚点键为同账户/同Q视图/同预定重复的**完整M实际运行**，冻结A_M（含回执/字节）、G_M、完整C/b、融合绑定、cursor/stop_reason/terminal及发布记录摘要。full/no-q/mean仅无I/O重排，不另起run、不查询、不调用模型、不修订或扩大G：

- full用实际raw q；no-q对应`no_quality`，用q_eff=z；mean对应`mean_quality`，用q_eff=z·q̄，q̄只在同A_M中完整C的z=1对象求raw q均值，分母0记0及原因。
- 完整M成功发布时，full TopK必须逐位等于其实际发布；不一致记协议失败，不挑一张更好的结果。原样保留锚点原终态，并另记`anchor_consistency=failed`，共同按F1失败口径处理。
- 完整M失败/未完成/阻断/非法交付或full不一致时，三组件共同`anchor_failed`，供后续评价在参考适用处共同记0；不能仅重排成功子集。NA仍由独立参考决定，运行器不代填指标。
- 控制重排是组件列表，不能搬用原模型理由冒充三张实际交付；其事实可从同A核对。公开脚本锚点仅为协议fixture，不能登记为真实M锚点/模型收益。

## 7 模型消息、工具、usage及错误适配

| 对象 | 最小合同 |
| --- | --- |
| ModelRequest | 宿主生成request/attempt/run/session/role及reply_to；model/capability/prompt/tool/schema绑定；有序messages、允许工具、结构化输出类别、输出上界、deadline及reservation_id。完整线载荷和摘要留审计，模型仅见安全投影。Provider会话ID只是传输信息，不持有新预算 |
| Message | 显式区分system/user/assistant/tool；内部role_message_id与供应商message ID另存；工具请求带call_id/name/封闭arguments，结果逐call_id一一对应、携status及安全receipt。顺序/工具关联不得丢失；缺失/重复/未知call_id拒绝。不同角色互传注明真实来源，不把另一角色消息伪造成供应商原生assistant续答 |
| ModelResponse | 供应商request/model版本、原始返回/摘要、有序内容块、finish_reason、工具请求或结构化角色输出、usage及错误。只接受相应阶段允许的输出，不从任意散文正则猜工具或截断JSON修成成功；JSON额外字段、非法数值、混合非法完成状态均报格式/协议错误 |
| 工具执行 | Adapter返回请求后由P1检查身份/当前候选/schema/预算再经E1执行；每次结果原样按安全格式回传。传输层不可擅自执行、并发、缓存或补工具；模型建议未执行要标not_attempted，只留观察记录，不能进入A的已取得原件/证据集合 |
| usage | `input_tokens/output_tokens`、cache/reasoning分项、费用相关原字段、usage_source及usage_known、请求是否发出/可能已执行、计费精确性。规范化规则必须有官方绑定，未知字段保留未知；合成usage明确标synthetic |
| Error | code/category、retryable、request_sent、usage_known/原usage、部分内容、供应商错误ID、observed_at/late。类别至少区分preflight拒绝、auth/capability、rate_limit/transport/timeout、refusal、format、truncated、unknown_usage。是否恢复由宿主与剩余根账决定，不由SDK隐式重发 |

未来真实模式调用前必须同时具备：本地实现接受、明确供应商/精确model ID与版本、官方能力证据、本地分词与usage映射、可执行预算与最终预留冻结，以及相应真实执行授权。未知项不可由历史建议、环境默认模型、聊天当前模型或SDK默认值代填。R不需模型绑定，但真实任务运行同样等待其适用执行预算/授权；本专项确认不启动真实R。

| 待绑定项 | 需要的证据；阻断哪一步 |
| --- | --- |
| 供应商/model/版本/端点与统一设置 | 明确人类选择、官方文档与参数兼容证据；S/M一致。当前为null/unbound，阻断真实供应商Adapter执行 |
| 上下文/输出/工具/结构化能力 | 官方上限、工具schema与工具结果顺序、并行开关、拒绝/截断、推理参数及实际传输映射；阻断对应真实线协议接受 |
| 分词器/本地计数 | 官方对应tokenizer版本与依赖、system/schema/工具/历史重发的完整请求计量；隐藏推理/缓存计量边界另给规则。无可核实本地计数时报缺口，不调用付费计数补洞 |
| 官方价格/账单/失败计费 | 带核验日期的输入/输出/缓存/推理及其他收费、失败/重试口径与费用上界；阻断真实费用预留/支出，不引用旧报价 |
| L/执行limits/最终程序预留 | 后续获授权T0逐依赖、累计载荷、失败结算和极值验证及独立冻结记录；阻断可执行预算。T0此轮和合同确认均不自动执行 |
| P1/真实支出/链 | 各自范围与授权；不由本合同或本地通过替代 |

下一步脚本Adapter只读公开人工脚本，返回真实格式的预设消息/故障/合成usage；`execution_kind=scripted_public`、`provenance=scripted`、`usage_basis=synthetic`、`release_scope=public_fixture_only`贯穿全部记录。测试账的model_calls表示合成Adapter尝试，另列`provider_requests_sent=0`、实际模型/API/费用=0。不能称本地脚本已验证供应商能力、分词、计费、自然完成率、自然反馈或协作增益。

## 8 公共测试Interface、人工例与最小开发联调

依mattpocock-skills:tdd，确认P1/P2/P3后才写测试；每次一个公共行为RED→最小GREEN，再推进下一行为。测试仅穿公共Interface，不直接改内部状态/私有方法、不模拟自家核验器或用生产输出生成期望。只在模型外部Seam、时间/故障使用受控Adapter；本地证据通过真实E1/LocalEvidenceSource和手写合法原字节取得。

| 公共Seam | 抓到什么 | 抓不到什么 |
| --- | --- | --- |
| P1 `run/audit_view` | 固定队列、停止、实际A/G、六角色调度、反馈、整表门禁、组件锚点及提交记录的组合行为 | 自然模型决策、真实供应商延迟/计费、统计效果 |
| P2 `invoke`请求/响应合同 | 实际线载荷的安全构造、消息/工具关联、usage/错误归一化与拒绝 | 未绑定供应商对这些字段的实际支持；脚本不证明本地分词正确 |
| P3 根账reserve/settle/audit与注入后的既有E1 | 跨候选/角色/工具/模型/重试原子守恒、未知占用、最终消费及兼容旧E1 | F3候选容量或正式预算可行性 |

以下期望先以公开人工常量/事实手工写定。只列应验证的行为，不在本轮创建测试代码；实施时逐纵向切片落实，不批量预写全套。

| 人工例 | 可手核的事实与预期 | Seam |
| --- | --- | --- |
| H01 同信息/零模型R | 同H/C/b/请求，R经完整事实判资格，S单会话多轮、M六角色用同工具并集；R任何非零模型尝试被拒绝，实际provider请求均0 | P1/P2 |
| H02 首10停止/不扩C | 12个公开候选A01…A12，b依次下降且均完整支持；必要臂处理前10即停，11/12未取证。质量测试L=12处理全部；C始终12，不能只导出处理前缀 | P1 |
| H03 不越游标 | A正向组合后仍有未结束登记页或未结算相关读取，B完整支持；A不能进G/跳过，B不得取得。A真正闭合缺件为Pending后才可拒绝/推进 | P1/P3 |
| H04 真正实际G | 同A中预取但未assess的B或模型自报合格B不进入G；关闭候选后反馈不重开。G与raw_eligible不同也保留原始记录 | P1 |
| H05 空与终态 | 完整C={A,B}均已闭合拒绝→valid_empty；仅前缀A已拒绝而B未处理→空证明不成立；超时/预算/格式/来源/门禁故障分别保留终态，不发布 | P1 |
| H06 六角色/消息来源 | 六个不同角色请求、管理dispatch、真实call_id与工具回执可连通；S仍是单身份。缺任一M角色输出不能成功；脚本不能产生provider_real标记 | P1/P2 |
| H07 一次反馈 | 草案把库存引用指到检验字段，Issue定位同draft/候选/主张/pointer；模型修订到同A真实零售字段，old/new可核对。未改、错Issue或第二周期均不能伪装修复 | P1 |
| H08 整表门禁 | K=10但草案第11项坏/重复，或正确G列表顺序反转、跨批次/属性/快照引用、自由“品质更安全”断言；均整表阻断，原理由原列表字节保留，门禁新I/O和模型调用均0 | P1 |
| H09 质量组件常量 | C={A,B,HI,LO}，均合格；b=.9/.6/1/0，m=.75/1/0/0，q=.6/.9/.6/.6；q̄=.675。full分数.675/.75/.5/0，no-q .825/.8/.5/0，mean .703125/.6375/.5/0；full B>A>HI>LO，其余A>B>HI>LO | P1 |
| H10 同锚点/共同失败 | H09中一个z=1对象未进G仍留mean分母；三列表同A/G/游标/终态无新增取证。M失败或实际full发布与重排不同→三组件共同anchor_failed，完整失败根保留 | P1 |
| H11 一根账不重置 | 合成模型调用上限2、final留1：第一普通调用已用1，第二普通调用不得挤占final；换候选/角色/模型会话仍拒绝，合法final消费后总2。重结算同reservation不重复消费/退款 | P3/P1 |
| H12 未知/失败/迟到 | 模型发送后超时usage=null，已知调用1保留、token占用未释放，禁止免费重试/发布；工具失败与模型格式修复共用2重试，1/2秒退避入根时间；迟到原字节留审计但不进可发布A/G | P2/P3/P1 |
| H13 token不重复 | 合成usage input=100、其中cache=40；output=30、其中reasoning=20→规范化100/30，不是140/50。未知output仍null。两次重发各100输入累计200，工具schema/历史不能只计差量 | P2/P3 |
| H14 工具关联/拒绝 | 重复/未知call_id、跨根ref、附加principal/path、非法JSON、截断/拒绝、未经宿主许可工具；不得取得目标字节/创建第二账。模型请求中的私有canary变化不影响安全载荷 | P2/P1 |
| H15 提交/预留/中断 | 最后一个普通动作不能占final；合法final不补读，提交成功才released。提交失败/重复run_id不覆盖旧记录；意图已登记后中断保留未知占用，不用新run重置 | P1/P3 |

最小开发联调仅为：公开小型C、人工原字节文件、受控单调时钟及脚本模型消息，穿P1→P2→既有E1/E2/Q→P3完成正常R/S/M协议、一次反馈、质量组件和故障路径；产物写新忽略审计目录。每例按需取最小规模，H02的12对象只检验停止。**不加载真实开发/测试根，不作320账户枚举、9,600清单、192回放、真实来源推荐probe或本地分词容量验证**；那些属于另行授权T0/供应商绑定。不得把本微型组合改名T0通过。

最小影响回归：原`tests/test_evidence_access.py`、`tests/test_evidence_verification.py`，以及旧动作fixture拒绝非零模型/fixture_only、JointSession安全投影/分页、Q固定分母/mean与无I/O的相关公共例。现有测试只读、不降断言；不重跑SIM生成、全量数据验收、P0、评分/组包、效果统计。新增变化/失败才扩大必要定向回归，不为凑数量全库重跑。

## 9 一次列明的文件范围、依赖与执行顺序

### 9.1 本轮与确认后白名单

| 时段/类别 | 允许写入的精确范围 |
| --- | --- |
| **本轮仅4份Markdown** | 本`spec.md`、`confirmation.md`、`map.md`、`issues/01-rsm-runner-and-six-role-adapter.md`，均在新目录`.scratch/recommendation-runtime/` |
| 确认后生产代码 | 新`recommendation_runner.py`、`model_adapter.py`；**仅修改既有`evidence_access.py`**，限P3根账及其注入/结算/最终阶段衔接，不变更E1授权、范围、来源、分页、核验业务语义 |
| 确认后公共测试 | 新`tests/test_recommendation_runner.py`、`tests/test_model_adapter.py`、`tests/test_root_budget.py`和一个共享`tests/runtime_fixtures.py`；复用原`tests/evidence_fixtures.py`但保持原字节。原测试全部只读 |
| 确认后守护/独立核对 | 新`.scratch/recommendation-runtime/diagnostics/run_check.py`、`protect_scope.py`、`check_delivery.py`；只作环境/累计资源守护、白名单保护、公开交付独立核对，不生成数据或另造运行入口 |
| 确认后专项文档 | 同目录独立`authorization-<date>.md`、`verification/`下TDD/人工验收映射、独立Standards/Spec原文及汇总/修正、交付摘要、新`acceptance-<date>.md`；更新本专项map/工单的状态与评论，合同/确认原稿由独立授权记录更新生效状态，不回写历史字节 |
| 确认后临时/审计 | 仅`.tmp/recommendation-runtime/`及`data/recommendation-runtime-audit/<独立轮次>/`；人工fixture原件、原始消息/失败回执、资源账/未结算意图、独占发布记录和摘要清单；不进入Git，不覆盖已有路径 |

其余文件只读，包括`joint_access.py/joint_tasks.py/evidence_verification.py/quality_fusion.py/recommendation_actions.py`、准备入口、environment/config、全部上游数据/记录/接受、论文/研究、原S、账户分组、工单15与既有专项文档。evidence_access.py是唯一既有代码例外，其BASE原字节/历史接受绑定保留在Git，另写兼容回归接受，不改旧接受记录或冒称当前源码仍是旧摘要。

当前Thesis环境已存在于项目`.conda/envs/Thesis`，已声明Python 3.13.16。下一步仅标准库，无依赖安装、SDK、tokenizer或环境变更。所有项目Python/测试/守护均显式`conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -B ...`，运行时核实sys.prefix和版本；当前合同阶段只做PowerShell/Git/文档只读核对，未运行项目Python。

实施本地资源建议一次批准：累计1,800秒本地Python墙钟、进程树4GiB（其中64MiB预留守护）、模型/API/外部付费0；RED、失败、保护、联调及接受核对全部入同一专项资源账。守护沿已接受Windows Job方法在新路径建立独立账，不复用旧专项剩余额度；中断未结算则停止新命令，超限不扩额。此处是开发计算资源，与F3每推荐根预算分开。

### 9.2 确认后直接执行

1. 归档一次人类确认、合同/确认表原始SHA-256、P1/P2/P3、H01—H15、白名单与资源上限，先保存授权再认领实施。完成条件：范围可定位且无自动填入真实模型/执行预算。
2. 建立新资源/保护账，按P3→P2→P1逐公共行为RED→最小GREEN；每个行为期望来自本合同人工例。完成条件：该行为及必要影响回归有原始失败/通过证据，不调用私有内部捷径。
3. 做§8公开微型组合和兼容回归，独立check仅核公开原件、消息/账/发布文件及字面期望，不导入生产运行/账/核验函数生成答案。完成条件：正常/故障均符合预期，所有失败保存，既有保护范围无非白名单变更。
4. 固定实现候选提交，按§10由两个独立代理审查；集中处理实际阻塞、定向补测和复审。完成条件：两轴分别无剩余阻塞，非阻塞判断单列，不借审查扩范围。
5. 另写专项接受，分别报告共享账、运行协议、公开Adapter/组合及旧E1兼容结果。完成条件：§10各项有真实证据，资源结算/原稿绑定/保护闭合；真实供应商、F3容量、T0/P1及15仍未接受。

合同外实质阻断一次集中列出事实、最小修改及回归影响，不能在实施中通过放宽fixture、另建账、免费取证、修改上游或新增依赖绕过。已批准范围内的普通实现选择与修复不重复请求许可。

## 10 验收与固定BASE双轴独立审查

| 编号 | 必须达到的验收条件 |
| --- | --- |
| A01 | P1/P2/P3已获一次确认，H01—H15逐公共行为有独立字面期望及RED/GREEN证据；没有本轮提前写代码/配置/测试 |
| A02 | R完整规则模型0；S多轮单身份且具备信息并集；M六角色、管理调度/工具/消息来源真实可追踪，脚本与供应商来源区分清楚 |
| A03 | 固定完整C/队列、当前游标、显式评估实际G及停止规则正确；合法空/未完成/阻断/失败/发布各有反例，不能靠局部G空或资源中断伪装成功 |
| A04 | 所有工作同一根账；未知/失败/重试/格式修复/迟到/中断及final消费有回执，守恒不变量零违例；既有E1兼容且原fixture限制未解除 |
| A05 | 只用实际A及显式G；整表资格/引用/理由/顺序/预算门禁不补证、不改写；记录提交成功才发布，失败/重复ID无覆盖 |
| A06 | Q三组件固定同锚点；人工分数/分母、full一致性及共同失败符合F1，组件无新增I/O/模型/G；无真实效果/样本充分性结论 |
| A07 | 封闭消息、工具关联、usage规范化及错误合同通过公开例；真实模式在缺模型/能力/分词/计费/预算/授权时拒绝，不能使用默认值 |
| A08 | 最小公开组合与必要影响回归通过，独立check与只读保护闭合；资源含全部失败且不超本地上限；只写§9白名单 |
| A09 | 同BASE/精确candidate的Standards和Spec两个独立代理报告分别无剩余阻塞，原文/修复/复审可追溯；专项接受明确保留T0/P1、真实供应商/预算与15门禁 |

遵循mattpocock-skills:code-review：BASE永久固定为`6ac5c2cddde6973b9743e3e17f5c264840f42854`，不因授权/修正提交移动。先固定candidate完整SHA，核实BASE可解析且为candidate祖先，`git diff BASE...candidate`非空，再把相同diff命令、`git log BASE..candidate --oneline`交两代理并行静态审查；复审固定新candidate，原报告保留。本轮BASE=HEAD，没有实现diff，**尚未执行或声称通过双轴审查**。

Standards轴读取AGENTS、代理约定、实际存在的编码标准（若届时有CODING_STANDARDS/CONTRIBUTING必须纳入），并带技能完整Fowler smell baseline；项目规范优先，smell是判断性建议，跳过工具已强制事项。Spec轴只以本合同、对应一次授权/工单及其直接继承合同为要求，核对遗漏、错实现及越界。两轴不互读对方报告，输出分别保存在`verification/standards-*.md`、`spec-*.md`，并列汇总、各报数量和最严重项，不跨轴合并排名。审查不运行推荐/私有评价，不代替实际验收。

## 11 当前交付自检与集中确认点

本轮完成标准是：六项任务要求均落到可核查合同、现有Interface缺口与回归明确、模型/预算待绑定没有假填、文件/依赖/验收/确认项一次列全且工单已登记。上述内容可由[确认表](confirmation.md)逐项确认；不重新确认F1—F3、09或数据路线。

本轮仅新增四份Markdown；生产代码、配置、测试、论文、研究及既有接受记录写入0，项目Python/测试/联调/推荐/T0/P1/模型/API/统计/链/15冻结执行0。文档检查只核链接、差异范围和只读材料摘要，不等于实现验收。确认后按§9直接进入获准范围。
