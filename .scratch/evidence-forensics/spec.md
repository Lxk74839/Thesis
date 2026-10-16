# 受限工具与异常生产核验：最小实施合同

日期：2026-10-16（Asia/Shanghai）。状态：**第一阶段审核稿，待集中确认；本稿尚未授权实施。**

固定基线：`ac49059ffa1f61545033b84f688eee4be58d75be`。本轮只新增本专项合同、[确认表](confirmation.md)、[工单01](issues/01-restricted-tools-and-production-verification.md)和[索引](map.md)。合同中的函数、字段及新文件均为确认后的实施约定，不表示已经存在或通过测试。

目标是交付共同的真实本地SIM取证Adapter，以及只消费方法实际取得材料的生产核验Module。成功标准为：公共Interface能证明获权取证、来源闭合、原8语义、Q兼容及共同计量；独立Standards/Spec审查无剩余阻塞。真实推荐运行、预算可行性和正式封存分别验收。

## 1 直接继承的依据与范围

| 已接受依据 | 本专项直接继承 |
| --- | --- |
| [正式数据规格](../data-preparation/spec.md)、[09确认](../data-preparation/issues/09-evidence-protocol.md)及[09协议正文](../data-preparation/ticket09-stage1-sim-evidence-request-review-draft-20261015.md) | 一父商品一SIM批次；六阶段、材料组合；来源、权限、精确字节、双时间、版本/撤销、四态及相关授权范围完成性 |
| [F1—F3确认](../data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md)及[精确正文](../data-preparation/ticket12-final-experiment-protocol-review-20261016.md) | 原8、Q1/Q2、R/S/M信息并集、固定队列/停止、实际A/G、计量及T0门；正文SHA-256为`d2b22af021b2e3b7a25046927c122ba653fe52691bc90c964b5f5edf6b7da4ca` |
| [10接受](../data-preparation/ticket10-acceptance-sim-normal-1.0.0.md)、[11接受](../data-preparation/ticket11-acceptance-sim-scenarios-1.0.0.md) | 现存正常/场景事实、原件和登记格式、合法动作及封存快照；不重新生成 |
| [12实际Interface](../data-preparation/ticket12-offline-interfaces-20261016.md)及[离线接受](../data-preparation/ticket12-offline-acceptance-and-remaining-decisions-20261016.md) | 正常v1的`rank_quality`及公开动作合同已接受范围；不将正常校验失败翻译成异常四态 |
| [13合同§10](../data-preparation/ticket13-stage1-joint-package-and-independent-evaluation-contract-20261016.md)、[13接受](../data-preparation/ticket13-acceptance-joint-task-package-0.1.0.md)、[14报告§5](../data-preparation/ticket14-full-data-acceptance-and-sufficiency-20261016.md) | 联合准备及数据层验收已完成，本专项承接其取证/生产核验缺口；不重开已接受模块 |

已只读读取[研究草案](../../research/数据修复方案与验收草案_20261010.md)和[修订论文](../../manuscript/论文初稿_表达与实验结构修订版_20261010.docx)正文及公式；它们不覆盖后续确认。论文题目、双模块、六角色、数据路线、原S及账户划分保持。项目无GLOSSARY.md及docs/adr，按domain约定继续，不建占位文件。

本地已启用mattpocock-skills及文档插件；本合同采用codebase-design的Module/Interface/Seam/Adapter和tdd的公共行为验收。只读本地依据已足够，不新增插件、依赖或外部检索。

## 2 最小Module与Seam

| Module / 拟新增文件 | Interface与职责 | 依赖及不覆盖项 |
| --- | --- | --- |
| 取证与根账：`evidence_access.py` | `EvidenceSession.dispatch(operation, arguments)`暴露共同取证；宿主侧`audit_view()`导出不可变A/回执，`assess_current()`原子记账后调用核验；身份、范围、分页、缓存和账集中在此 | 组合只读`JointSession`；注入受限本地事实Adapter、单调时钟和根账。没有文件浏览、模型或推荐运行器 |
| 生产核验：`evidence_verification.py` | `assess_evidence(binding, acquired) -> assessment`，纯内存；输出逐声明/候选状态、完成性、拒绝理由与来源链。Q转换也在此就地完成，不另建框架 | 只读实际A、冻结请求/规则；纯计算不自行构造数据访问。复用`rank_quality`，不导入独立参考、生成器答案或诊断程序 |

这是两个deep Module：调用方只需掌握受限操作和核验结果；授权、分页闭合、来源、版本及计量不散落到R/S/M或六角色。根账不再单拆Module，Q转换不增加通用插件系统。内部事实Adapter确有两个用途：真实本地只读文件、同格式公开微型文件及故障控制；后者不是预制四态的假取证器。时钟可控以验收超时，生产使用真实单调时间。

公共测试Seam为：**E1**：真实`EvidenceSession.dispatch`及其宿主审计回执，捕获授权/实际I/O/分页/计量，不能验证自然模型行为；**E2**：`assess_evidence`及宿主`assess_current`的组合，捕获A内推导、来源、准入和程序计费，不能验证独立gold或最终发布流程。测试只跨这两个Interface；不测试私有辅助函数或mock内部核验结论。

现有`joint_access.py`、`quality_fusion.py`、`recommendation_actions.py`、准备入口及已有测试保持只读。`candidate_page`原样委托既有Interface：`order=parent/base`、固定32项、完整C及既有续页语义。新包装层补记实际使用，不重算b、不截C。旧投影的`tools=[]`及输入指纹不改；新取证工具的schema/版本作为独立宿主扩展导出，真实模型注册留运行器专项。

## 3 宿主绑定与实际取得集合A

宿主从13已接受来源绑定建立`run_id/root_task_id`、方法运行实例、完整C/b/候选批次、当前固定队列位置、请求条款、principal、材料版本/snapshot、τ及协议版本。**当前候选、身份和快照均不接受调用方覆盖。** 所有角色连接同一个根上下文；角色仅是宿主审计归属，不产生权限。R/S/M每方法运行各有一份同口径根账，M六角色合计一份。

调用方没有构造/替换宿主对象、A或回执的工具；只能提供§4的封闭参数。安全投影与候选分页复用13。分页看到候选不等于已推进取证游标；更换当前候选只能由受信任宿主依据显式评估结果执行，不能凭模型传入父ID、页码或角色推进。本专项返回推进条件，完整运行器和停止/发布流程留后续接入。

`A`按方法运行记录真实取得的对象及可观察失败，至少包含：原字节、实际摘要、登记原行、批次/事件/动作依赖、获权策略与快照原文、范围枚举/读取回执、来源定位和取得时间。每个对象记录材料版本、snapshot、principal、业务键、kind/id/version、文件组件摘要及行/字节定位；核验引用还含JSON pointer及使用的回执ID。位置只在宿主审计侧保留。

构造会话只绑定来源，不能把整包事实视为A。底层可为完整性核查/索引扫描文件；扫描量另记setup字节/I/O/时间，不让扫描事实进入方法A。任何参与核验的快照、策略、动作、事件或空范围事实，仍须通过共同取证实际返回并入账。禁止从配置、全局索引、缓存旁路或独立参考免费补全未读事实。

模型仅收到当前范围的白名单事实和技术观察：材料/事件/动作的获权原文、登记的安全字段、SIM披露、不透明句柄及用量回执。登记全局sequence、共享snapshot管理ID、全局行数/截止序号、源路径、视图名称、扰动名单、策略中其他候选拒读清单、原始总清单及私有摘要均不进入模型。策略/快照原字节由已计量的宿主A保留，模型侧仅投影当前授权语义；不能让投影遗漏变成宿主补证。

## 4 共同取证Interface

以下为待确认的封闭合同，UTF-8 JSON承载；原件摘要仍按已有无行末LF精确字节核对，不能先规范化再比较。

| 操作 | 调用方输入 | 成功输出 |
| --- | --- | --- |
| `list_evidence` | 恰为`{cursor}`，首项为null；当前请求条款由宿主绑定，不另给可缩窄到正向材料的过滤器 | `status=ok`、不透明`scope_handle`、`entries`、`next_cursor`、`enumeration_complete`、实际初始依赖/既有依赖引用、`receipt` |
| `read_evidence` | 恰为`{evidence_refs:[...]}`，1—32个不同的不透明ref，均由本会话当前范围列取产生；允许同一物理请求批读 | 按输入顺序返回`items`：ref、逐项status、成功时原件精确`raw_utf8`、实际字节数/摘要、登记引用/来源句柄；附共同`receipt` |

`entries`按候选登记范围稳定排序，含登记安全字段、`target_kind/target_id/version`、登记摘要及不透明读取ref。ref统一覆盖batch、event、material、change_action，不能因名字叫read_evidence而把事件/动作放到免费旁路。原登记字节在A中保留，安全投影不改写登记事实。快照/策略及无动作范围的初始证据由首个list请求实际取得；后续引用已取得依赖，不凭文件名伪造空动作字节。

**列举范围：** 最小实现保守枚举当前候选在该获权快照内的完整登记范围，再加其授权版本/撤销关系。包含独立谱系的支持和否定、旧版/合法新版/动作、不可采用但属于该范围的登记；不先按pass、issuer正确、摘要匹配或最终状态过滤。对指向当前对象的登记取得错配原文时保留原字节供拒绝核验，不沿错配原文去读取其他候选。登记可见但原件拒读的情况保留实际拒读观察；登记本身无权读取时不泄漏其存在。

选择完整候选登记范围可直接兼容Q要求的完整registrations，避免新增一种摘要；**不因此要求读取全部八种材料**。生产核验只要求请求/软偏好及实际对象路径所依赖的原文。R1至少依赖sample/report及批次、inspection和必要前驱事件；R5增加retail及其路径；Q的A检查再依赖dispatch/receipt及相应事件。事件前驱闭合到批次；缺一个必要前驱即不能用索引摘要冒充已取得事件。无关harvest原件不因路径经过harvest事件而成为R1必读项。

list每页固定最多32条登记，末页可不足，空获权范围也是可正常结束的页。游标为宿主签发/保存的不透明句柄，绑定run/root/当前候选/请求范围/principal/snapshot及固定顺序；跨根、跨候选、跨快照、伪造和失效游标统一拒绝。到末页才`enumeration_complete=true,next_cursor=null`，它只证明此范围枚举结束，不证明原件已读或声明Supported。重复页可幂等重放事实，但每次实际请求和返回照计。

枚举回执还必须保留当前请求必要槽位的授权覆盖观察。已知必要槽位受限时，不能通过只返回可读子集将缺口抹去；终页标志不能替代必需读取完成性。范围外对象不枚举、不泄漏，也不声称查尽现实世界反证。

read无隐式分页；超过32个ref须分请求，逻辑逐项计算。ref绑定完整上下文和登记版本；随机ID、路径、URL、查询语句、额外root/principal/snapshot/role参数均不获权。先验证整批ref/参数和授权，再访问事实存储；不能先探测私有目标。原件摘要错配属于内层业务观察，仍返回实际字节，由核验排除；不能据此把外层完整发布的场景包误判为损坏。

| 状态/错误 | 含义与回执 |
| --- | --- |
| `access_denied` | 不获权操作/参数/ref/游标及跨范围挑战；模型文案不区分私有对象存在性；拒绝前无目标读取，保留失败计量 |
| `invalid_request` | 当前合法操作的纯类型/批量长度错误；不返回路径或存在性信息；身份覆盖仍用access_denied |
| `unavailable` | 在完整且获权的事实源内，已登记原件实际缺失；保留登记、实际查找和缺件观察，不提供四态答案 |
| `io_error` / `deadline_exceeded` | 读取/超时未完成；按实际尝试结算，剩余项不伪装成已查缺失；是否重试由共同根规则决定 |
| `budget_exhausted` | 原子预留不足，拒绝发起新物理工作；保留用量和未完成范围，不偷偷扩额 |
| `source_integrity_error` | 已绑定组件丢失/截断、外层清单摘要或来源绑定不符、路径越界；停止受影响会话，不给所有候选补Pending |

正常响应或失败均有回执；批读的单项失败单列，未执行项为`not_attempted`，已实际返回的成功项仍入A。真实迟到响应在审计中保留，根截止后不继续取证/推进；不能倒填完成时点。传输失败且没有返回某原件，不视为该原件已取得。内层业务缺件与外层组件损坏按11已接受规则区分。

## 5 生产核验及推进条件

`binding`只含当前冻结请求/业务对象/τ和受信任范围绑定；`acquired`必须来自该方法宿主A的不可变导出。`assess_evidence`没有文件、网络、评价或生成计划依赖；不读私有gold、F/合格集合、U8/UQ掩码、目标、异常标签或独立参考实现。自报状态、角色共识、单条pass及登记摘要都不能替代实际原文组合。

结果至少含`assessment_status=unassessed/assessed`、逐声明`evidence_state=null/Supported/Refuted/Pending/Conflict`、候选聚合、`eligible`、`completion`、`advance_allowed`、被采用/排除材料及来源链。`completion`的`enumeration_complete/required_reads_complete/version_checks_complete/attempts_settled`均为布尔值；不能合成一个模糊done。assessed不等于范围已闭合，必须一并看完成性。

**Unassessed是评估进度，四态是证据判断。** 尚未显式评估、未尝试相关取证或只遇到无事实的传输中断时，保留Unassessed（`evidence_state=null`），不改为Pending。显式对实际取得/已尝试材料评估后，严格应用09：s/r为完整可采用支持/否定组合；`complete`要求相关范围、必需原文、版本/撤销均核验完成。

| 实际A中的条件 | 声明判断 |
| --- | --- |
| s=1且r=1 | Conflict；另列完成性 |
| s=0且r=1 | Refuted；另列完成性，相关范围尚未闭合时仍不能冒称完整 |
| s=1且r=0且complete=true | Supported |
| 已实际评估的其余情况 | Pending；包括读完拒绝、已查缺件或部分正证，明确原因/未完成范围 |

局部正证、未结束分页经显式评估可按09得到Pending，但`advance_allowed=false`，不能用此状态跳过当前候选。预算/时间导致的未完成继续记录运行未完成，不改成完成的拒绝。已结束枚举、所有必要取得尝试均有成功或终局缺件/拒读/拒绝回执、没有待结算/可继续处理的相关项，才可将完成评估的Pending/Refuted/Conflict交宿主作拒绝后推进。原件缺失时“尝试已结束”不等于“必需原件已取得”。

候选合并沿用Conflict→Refuted→全部Supported→Pending；尚有Unassessed的必要声明且未发现有效Conflict/Refuted时，候选保持Unassessed。只有显式评估且全部必要声明Supported、相关范围闭合才能`eligible=true`并进入该方法实际G。预取、已登记或rank函数能解析均不自动入G。

先核对来源与签发/登记/动作权限、原件字节摘要、父商品/批次/事件/采样/运输段、时间、版本和撤销，再组合内容。只采用当前快照截止内且τ时生效的合法头版本；合法supersedes取代旧pass，不能制造Conflict；头版不可取得/摘要错/撤销时不回退旧正证。不同谱系合法pass/fail并存才构成Conflict，非法动作或元数据矛盾不自动构成内容Conflict。缺动作依赖时不猜v1仍有效。

`historical_fact`不加TTL；当前断言用`valid_from_ms ≤ τ < valid_to_ms`。撤销仅排除指定版本，不改成fail；快照后登记/尚未生效动作不能改写当前判断。无效材料只影响依赖它的声明；不得以无关材料变化否决R1/R5。

生产范围是原8`V00/V01/V03/V05/V06/V07/V09/V12`必需语义，以及支撑其来源/权限/对象/版本/撤销的公共反例；不是新增16视图正式运行。必要请求继承R1 AND R5，必要臂按已有b排序。本专项不实现模型反馈、发布复查、凭证登记或账本签名，也不解锁`advance_action`的public fixture限制。

## 6 Q1/Q2兼容

Q取证复用同一E1，仍须实际取得snapshot、policy_bytes、actions_bytes（含实际空流观察）、完整候选registrations和已读originals；只从A转换为已接受`rank_quality(binding, acquired)`形状。不把全包加入A，不给缺失项生成默认原文/空动作，不修改旧评分器或扩大正常v1适用范围；动作非空、复杂版本等超出Q合同则明确拒绝。

保留库存同属性z/m、C分母1、A分母2、T原始分子分母、raw q与来源。到货未取得或发运依赖缺失时A贡献0，不改分母、不补证。完整C中未取得同属性支持的候选不进入mean分母；已经实际取得z=1的对象按F1计算，分母不能偷偷换成G或Top10。

`rank_quality`的局部eligible/G仅是已接受评分Interface输出，最终排序必须以显式评估冻结的实际G为范围；不能让预取但未评估对象扩G。保留完整C的raw q用于mean，再在同一个G排序/截TopK。full/no_quality/mean_quality及α=1边界只在冻结的同A/G/终态上无I/O计算。真实M锚点、full发布一致性与失败三个组件共同计0仍由后续运行器/F1验收；本专项仅用公开b证明转换兼容，不冒充真实组件效果。

## 7 共同计量和回执

每次回执包含宿主生成的`receipt_id/request_id/retry_of`、操作、实际绑定、宿主角色归属、开始/结束/迟到标记、逐项结果、来源、cache_hit、逻辑/物理用量与实际传输字节、程序操作、预留/结算/释放、根前后账及是否已结清。模型版只显示安全句柄、当前范围技术结果和用量；宿主版保留精确绑定/来源。回执是本地审计记录，不能宣称外部签名或链确认。

用量字段沿用已有`logical_tools/physical_tools/candidates/retries/elapsed_ms`，增量和根累计分别保存；另记`response_bytes`、逐项`adapter_request_id/source_ref/cache_hit`及`reservation{held,settled,released,unresolved}`，禁止用仅有一个total的回执。时间为真实单调耗时，SIM τ不当运行时钟。模型/token/费用在本专项本地调用中为0，不据此填未来模型预算；未知用量用null和未结清标志表示。

| 项目 | 统一口径 |
| --- | --- |
| 逻辑用量 | 每次实际返回的登记、原件、快照、策略或空登记/动作范围事实各1单位；一次批读N件按N计。assess及后续submit/verify/patch/final每实际程序操作1单位，后续操作本轮不实现。重复返回/缓存命中仍逐项计，纯回执头/句柄不递归计费 |
| 初始依赖 | 首次实际取得的snapshot/policy/动作范围同样逐项计。正常profile的“无动作结构”与Q的实际0字节动作文件分别留来源，不能偷偷从空列表假定。全局文件完整性/建索引setup另报，不能用setup免费传入判定事实 |
| 候选分页 | 每返回一个白名单候选行计1逻辑，物理按实际Adapter调用；内存分页可为0物理。它不是原件取得，也不增加已评估候选数；上限候选数计不同的实际进入取证/评估候选 |
| 物理用量 | 每次真实事实Adapter请求计1；批读实际形成一请求才计1，若拆成k次则计k。缓存完全命中且无新Adapter工作为0；不把磁盘read次数称物理请求，也不把多个后台请求藏为1 |
| 缓存 | 每方法运行独立冷启动，六角色共用本根缓存；不跨R/S/M、root或视图预热方法事实。键含run/root/候选范围/principal/snapshot/τ/策略与内容版本/target/version；跨快照同id/version不可命中。命中仍重新授权，不复用决策/修订 |
| 失败/重试 | 已获预留的失败操作或批内失败项各1逻辑，成功返回事实各按项计，同一失败项不重复加1；已发起物理请求照计，授权/参数拒绝无目标读取、0物理。预算/截止守卫在入场前拒绝及not_attempted项为0逻辑/0物理，拒绝次数另记，不作为免费已执行工作或重试成功。重试为新request，引用retry_of，照计实际用量并占共同重试额度；不自动重试或清零。格式修复额度也不另给角色 |
| 预留/未知用量 | 入场先保留失败处理所需额度，再于发起前原子预留最坏返回量/请求量及时间，始终保护最终预留。结算已消耗，释放只限明确未发生的预留；未知usage保持未结清及保守占用，不填0/免费重试。预算守卫拒绝不再消耗已耗尽的预算；超限和迟到保留账并停止新工作 |
| 纯计算 | E2和Q重算只读已取得内存，另记本地时间/内存；assess的1逻辑仍记。Q离线组件重排不新增取得或工具用量，不借重排扩A/G |

例：已取得初始依赖后，list返回3条登记=3逻辑；批read成功返回2原件且第三项已查缺件=3逻辑；冷Adapter各1请求，合计6逻辑/2物理。对相同成功2原件再次缓存批读=2逻辑/0物理。该例仅定义口径，不替代真实依赖计量。

新宿主使用显式测试limits/reserve验收原子性，不为正式运行代填最终预留。F3候选仍为2,048逻辑/256物理、64候选、共2次重试、600秒，S/M各12调用/96k输入/12k输出；M六角色合计，R模型/token为0。单请求45秒及1/2秒退避继承F3。最终程序预留仍待T0逐依赖闭合，`execution_budget=null, execution_authorized=false`。本合同规定计量，不证明这些数值可完成固定前缀，更不声称T0通过。

## 8 公共人工反例与验收

公开夹具只有人工商品A/B、真实格式原字节、登记、事件、策略、快照及动作；父ID/b/τ为人工常量，无真实账号或私有答案。每个预期先按下表手工写定，不调用生产函数/独立gold生成期望。除专门删改项外依赖均完整合法。

| 编号 / Seam | 人工事实或操作 | 必须观察到的行为 |
| --- | --- | --- |
| H01 / E1+E2 | 正常sample+pass、有效on_sale、路径/登记/范围均闭合 | R1/R5及候选Supported、eligible；所有依据可回溯到实际回执 |
| H02 / E1+E2 | 保留报告登记，实际原件缺失；另给一个发布清单不符的损坏源 | 前者取得unavailable后评估Pending；后者source_integrity_error停止，不能批量补Pending |
| H03 / E2 | fail原文配旧pass摘要；另将原文/登记摘要一起合法改成fail | 前者不可采用/Pending；后者完整绑定Refuted，直接区分V03/V05 |
| H04 / E2 | 独立谱系pass/fail，共用合法sample；再去掉sample或错配事件/项目/批次 | 完整正反为Conflict；无完整绑定不构成有效正反；错配不能当内容否定 |
| H05 / E2 | retail的valid_to恰等于τ；历史sample/report仍有效 | R1 Supported、R5 Pending；不得给历史报告加TTL或将到期改成Refuted |
| H06 / E2 | 合法v2/fail及supersedes；再测试v2缺件/摘要错/被合法撤销 | 前者Refuted且不与旧pass冲突；其余不恢复旧pass。非法动作不能撤掉合法原文 |
| H07 / E2 | 合法撤销v1；另把登记放到快照截止后或动作生效放τ之后 | 仅当前可见且生效的撤销排除支持；撤销不是fail，未来记录不改旧快照 |
| H08 / E1+E2 | 已知登记可见但报告读取拒绝；伪造principal/root/path/URL/旧候选ref | 实际获权缺口评估Pending；越权统一拒绝且目标读取0，不能通过改角色获权 |
| H09 / E1+E2 | 33条相关登记，否定组合在末页；只读首32条/末页后仍未读反证原件 | 首页面不能报枚举完成/Supported；只见正证至多部分Pending且不能推进；完整正反才Conflict |
| H10 / E1+E2 | 未取证直接assess；部分页后中断；已枚举且所有必需尝试终局缺件 | 分别保留Unassessed、部分Pending且不可推进、已评估Pending可供安全拒绝；不混淆进度与证据状态 |
| H11 / E2 | 只改无关harvest产区原文及其合法登记 | R1/R5资格及必要臂固定b次序不变；原件仍可留实际来源 |
| H12 / E1 | 同id/version分支字节不同；重复成功读取；六角色并发争用最后额度；失败/重试/迟到 | 跨快照不命中；命中仍计逻辑；仅一次原子预留成功；根账守恒，失败不退消耗、迟到不推进 |
| H13 / E1+E2 | Q完整正常v1实际A；删到货或发运依赖；有已取得z=1但尚未入G对象 | 与既有rank字段兼容；缺件A分母仍2；mean在实际A的完整C中取值，最后仅同G排序，不免费补原文/扩G |
| H14 / E1+E2 | 固定允许事实，替换/移走私有gold、F、目标或异常计划；保留只有pass、无fail字样的路径 | 可见响应、用量、状态与排序不变；实际可打开路径仅白名单事实。原8判断来自字节/关系，不能按名称走分支 |

H06另用合法v2/pass确认“升版不必改变资格”；这是版本规则反例，不增加V10正式运行。H04/H07/H08覆盖对象、撤销和权限依赖，不把其全量视图纳入新主比较。

验收条件为H01—H14全部通过且无隔离/来源/计量违例；E1必须经过真实公开微型文件Adapter，不仅测试内存已给答案。必要影响回归仅既有候选分页/安全投影及Q纯评分Interface，不重跑上游全部验收、P0或生成。另作固定开发根（安全root字节序首项）与固定当前候选（既有b队列首项）在原8+Q1/Q2的10个来源绑定probe，核对实际来源、授权、原字节/投影/回执及Q schema接入；不扫描全开发根、不输出推荐整表、不读取目标/独立参考、不计算效果或可行预算，不称T0。真实异常语义由人工例覆盖，不假定该候选恰在原S。

源probe和测试只读取已接受事实，独立审计可直接核对其原件/登记和人工预期，但不得把审计额外读取回灌方法A。来源probe失败须报告具体绑定缺口，不能靠重生成材料或修改上游“修好”。

## 9 修改白名单、依赖及实施顺序

| 范围 | 确认后允许的最小写入 |
| --- | --- |
| 新生产代码 | 仅`evidence_access.py`、`evidence_verification.py`；不增加准备阶段、CLI、配置、模型SDK或通用框架 |
| 新公共测试 | `tests/test_evidence_access.py`、`tests/test_evidence_verification.py`，必要的一个共享`tests/evidence_fixtures.py`；不改已有测试及接受样本 |
| 专项记录 | 本目录内授权/回执说明、TDD记录、必要源probe/独立核对脚本、Standards/Spec报告与独立接受记录；实际临时夹具/审计输出仅项目内独立临时/忽略路径，不覆盖数据 |
| 已接受上游 | 全部只读，包括论文、研究材料、既有代码/配置/测试、数据/记录、原S、账户分组及13/14接受记录；本专项索引只在新目录登记 |

运行时直接使用既有Python 3.13.16/标准库，无新安装；所有实现后的Python/测试/probe显式`conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis`。本轮只有文件/Git/摘要/文档只读核对，未执行项目Python、测试或probe。

依赖已齐备：09及10/11事实/动作格式、12正常Q评分、13安全投影/候选映射、14接受链。它们的已有完成结论直接引用。待确认的是本稿新增Interface、批读/分页、A与计量、Seam/人工例及文件范围；不要求再确认F1—F3或数据路线。模型ID/分词器/官方能力/失败计费、真实运行器、最终发布预留、T0/P1、效果统计和账本不是本专项实施前置，也不会由本专项替代。

确认后按以下顺序直接进入获准范围，不再为同一范围重复索取确认：

1. 记录人类确认、合同原字节SHA-256、E1/E2/H01—H14及本白名单，先归档授权再写代码；合同原稿保留，状态由独立授权记录更新。
2. 按tdd做一个公共行为RED→一份最小GREEN，逐项推进；先E1实际取证/账，再E2四态/版本，最后Q兼容。不先批量写全部测试，不以生产输出反算期望。
3. 运行新行为及必要影响回归、10来源probe；记录成功、失败、实际用量及上游保护，无问题后不反复重跑。
4. 固定候选提交，用下述两个独立代理按同一base/candidate作Standards与Spec审查。阻塞集中处理、定向补测和复审，非阻塞仅记录，不借审查扩大范围。
5. 仅在合同适用验收及审查无剩余阻塞时，另写专项接受记录；工具、核验和Q转换分项给真实结论，保留运行器、T0与15门禁。

审查固定base为`ac49059ffa1f61545033b84f688eee4be58d75be`；核对它解析且祖先关系正确后冻结candidate SHA，审查命令为`git diff ac49059ffa1f61545033b84f688eee4be58d75be...<candidate>`和对应提交清单。Standards只读项目规范、相关skill及固定diff；Spec只读本合同/确认、继承协议及同一diff，分别独立出报告，互不预先共享发现；汇总不合并两轴。两份报告都绑定精确base/candidate，不以浮动HEAD或本轮文档自检代替实现审查。

## 10 保留门禁与本轮交付检查

[工单15](../data-preparation/issues/15-reproducible-freeze.md)文件和状态保持原字节；其ready-for-agent不是自动冻结授权。剩余D12、稳定序列化/组件命名/独立抽核及全部适用门禁仍须满足。14交付完成不等于整体充分性通过，975人数也不等于实际精度已通过。

本专项接受最多解除“受限取证及原8生产核验未接受”这一依赖；模型/六角色Adapter、完整根运行/发布、官方能力及分词/计费、T0和可执行预算、P1/支出、统计效果、链部署/对照、15正式封存仍按原归属处理。不运行T0/P1、模型/API或链部署，不读取正式测试推荐表现，不重新生成数据。

本轮只核对文档结构、引用、确认项/验收映射、Git写入范围及保护摘要；不宣称生产测试或Standards/Spec已经通过。集中确认项见[confirmation.md](confirmation.md)；本稿与确认表须一同确认，修改任一实质条款后重新核对其绑定。

第一阶段实际自检：4份Markdown、26处本地引用均可定位，H01—H14及CFE-01—CFE-08齐全，无未闭合围栏/行尾空白。15份保护文件前后字节数/SHA-256相同（含论文、研究草案、协议/接受记录、旧spec/map、工单15及拟复用代码）；既有跟踪文件相对ac49059无差异。仅新增本专项4文档，项目Python/测试、数据生成、T0/P1、模型/API、链部署执行均为0；这些是文档范围自检，不是实现接受。
