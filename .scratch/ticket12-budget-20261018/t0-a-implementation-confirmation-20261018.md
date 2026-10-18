# 工单12：T0-A开发集请求目录准备集中确认

日期：2026-10-18。Status：**待一次集中确认**。工作目录：`C:\Users\Kane\Documents\CodexProject\Thesis`。固定BASE：`88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a`。

**推荐：实现一个不可发送的开发集目录编译器，生成全开发依赖/候选预算清单和每轮完整候选请求W/P；复用现有消息组合及原生映射，不逐根运行推荐动作链。** 本文最后A01—A08为一个实施及A阶段执行包。人类确认后先归档授权，完成逐行为TDD和固定候选双轴审查，再直接执行A及本合同内的复现/交付核对，无须再次询问已确认步骤。此授权不包括外部计数C、容量回放B或P1。

本轮仅只读查阅合同、源码与来源元数据并新增本Markdown；项目Python/测试、供应商API、T0-A/B/C和P1执行均0。没有读取私有评价目标、测试推荐表现、身份密钥正文或供应商凭据，没有修改生产代码、配置、环境锁、论文、已有接受记录或工单状态。

## 1 继承依据和本次补齐点

- [批处理接受](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/acceptance-offline-batch-20261018.md)与[离线适配接受](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/acceptance-model-offline-20261018.md)直接继承。后者归档88e8b80、实现候选8c5ed82，Standards/Spec最终均0问题。本轮不重复测试或审查这些已接受实现。
- [F1—F3确认](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md)及[正文§10](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket12-final-experiment-protocol-review-20261016.md)规定：**“320×(原8+Q1/Q2共10视图)×R/S/M……最多9,600份依赖/预算清单……不逐份重放整条动作链，不读目标，不评价推荐优劣。”** 原T0总额为1,800秒/4GiB；后续极值回放去重≤90根、冷热≤180次、新故障≤12、总实际脚本回放≤192，均不在本次A执行包内。
- 已确认的[模型前置合同§5](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/model-preconditions-confirmation-20261018.md)已把T0拆为A离线准备→C独立外部计数→B零API容量统计/回放。A允许token未知；G2b全量官方回执闭合前不能选择token最大根或做B。
- [工单13联合准备接受](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket13-acceptance-joint-task-package-0.1.0.md)、[共同取证接受](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/evidence-forensics/acceptance-20261017.md)及其来源/权限/计量语义保持。研究草案和修订论文已只读查阅，正式确认合同优先。

当前源码限制必须正面处理：RecommendationRun.run只收公开fixture；其初始化消息使用H，而联合模型投影使用history，必要条款也不能拿公开c1/c2冒充真实R1/R5。ModelAdapter.prepare目前只收native fixture；联合包预算仍是旧候选且execution_budget=null。**本案新增专用的纯准备路径、明确字段适配和候选覆盖记录；不放宽公开运行器门，不回写联合包。**

## 2 B02/B03主案：仅作后续T0验证候选

只采用[原集中表B02/B03主案A](/C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/ticket12-budget-20261018/confirmation.md)。以下不是已经容纳全部受控路径的证明，也不是正式费用或可执行预算冻结。

| 资源 | 每个S/M根总候选 | 总量内final保护 | 普通阶段可用上限/限制 |
| --- | ---: | ---: | --- |
| 模型发送尝试 | 17 | 1 | ≤16，六角色共用；反馈/修复/续轮也占槽 |
| 累计完整输入token | 192,000 | 8,000 | ≤184,000；A实际完整计数为null |
| 累计全部输出token | 24,000 | 1,500 | ≤22,500；含推理输出，不重复加推理子项，A实际值null |
| 逻辑操作 | 4,096 | 1 | ≤4,095；批内逐登记/原件/list/read/assess/advance及程序操作照原口径 |
| 物理工具请求 | 256 | 0，条件性 | ≤256；final只提交既有已核验稿，不补证，无新增外部依赖 |
| 不同实际进入候选 | 64 | 0 | 必要臂第10个合格即停；质量臂固定前缀64；完整C不缩小 |
| 失败重试/格式修复 | 2 | 不另增 | 模型与工具共用；退避1/2秒计入根时限，一次反馈不另叫重试 |
| 根时限 | 900秒 | 60秒 | ≤840秒；setup/工具/退避/程序均计入，不按角色扩额 |
| 条件性模型费用包络 | 252,017微美元 | 至少12,751微美元 | ≤239,266微美元；只继承原主案报价假设，不批准花费 |

单次限制：普通模型请求≤45秒、输入≤96,000、输出cap≤8,192，并受根剩余/final保护；final输入≤8,000、输出cap≤1,500、模型≤45秒，final/commit/seal三个本地阶段各≤5秒且合计在60秒内。批上限32，真实逐项停止和信息范围保持。final出现新依赖时0物理假设失效，须另提合同修订。

R沿用相同工具、候选及时间候选，模型调用/token/模型费用及其final模型预留均为0；程序final逻辑1和时间保护仍存在。质量R/S仅为T0技术覆盖，不增列正式付费实验。B07批16、其他模型和预算备选均不启用。B06正式模型池、计数费、税费/P1/链费用均不获本次批准，不沿用USD600。

候选限额保存在新目录的`budget_candidate`及合同摘要中；既有配置/联合包的budget_candidate、execution_budget和execution_authorized一律只读。新产物同样保留`execution_budget=null, execution_authorized=false`；A的独立执行授权只许可目录准备，不许可生成发送。

**A的预算判定边界：**模型请求槽、计划逻辑/物理依赖和声明的单次上限可以列明；真实累计I/O、费用、动态剩余额度及每轮发送准入仍为null/not_evaluated。A为普通轮冻结名义输出cap=8,192、final=1,500的完整候选W，不虚构前轮供应商usage来计算余额。输出cap之和单列为`sum_requested_output_caps`，不把它称作实际累计输出或证明24k足够；不承诺每轮可同时取满。B若因实际回执、受控输出或剩余额度改变cap/历史/工具结果，必须重新prepare及绑定目录，不能把原W回执改签给新W。

## 3 规模、数据白名单及隔离

计划键固定为`(root_task_id, view_label, method, repeat=1)`：320个原开发账户×`V00,V01,V03,V05,V06,V07,V09,V12,Q1,Q2`×`R,S,M`，完整覆盖时9,600行；每法3,200行，每视图/方法320行。不扩账户、不改划分/原S、K10、完整C/b、质量主点、必要条件和视图来源；Q的控制重排不增加模型请求。

### 3.1 宿主侧开发白名单的形成

现有联合model投影刻意不带分组；不能因此读取private/evaluation.jsonl获取split。推荐以下**精确控制元数据权限**，需要随A01一并确认：

1. 只读已接受07/08/13记录、接受摘要和对应配置中的路径/SHA/版本；不运行准备入口、评分、P0、S2或上游生成。
2. 宿主读取`data/splits/grain-A-1.1.15/user-split-1.0.0/accounts.jsonl`中user_id/split等分组元数据；只保留原split=dev的320项。它不含评价目标。不得根据历史、类别或效果重新筛人。
3. 仅为把原开发账户关联到既有08 task_id，宿主按`config/preference-task-1.0.1.json`固定的原规则，用**该数据身份键**`data/task-inputs/preference-task-1.0.0/id-key.bin`读取一次并计算`HMAC-SHA256(key, b"preference-task-1.0.1\0" + user_id_utf8)`。这是确认后的定点数据关联权限，不是供应商凭据探测；本轮未读键正文。验证原键摘要及原根ID，不换键/重新划分。键、原user_id、分组、文件路径不进入W/P、公开日志或Git。
4. 只载入这320个root_task_id的联合安全投影。共享model JSONL允许为校验/字节区间索引作非语义扫描；先定位唯一顶层root_task_id，非开发行不反序列化H/C、不进入会话、输出或日志。索引解析须处理嵌套/转义，不能用评论中的伪ID命中；全文件摘要核对不等于获准使用测试输入。

允许的业务输入是13的model/catalog、model/roots、model/candidates及model manifest；按开发根选择view-bindings中的固定快照/profile/τ/principal，必要时只读private/session-map里的不透明会话关联元数据。共享商品目录/视图材料仅在其本来允许的范围内使用。

禁止打开私有evaluation/reference/gold/UQ掩码、测试推荐输出、原私有目标或目标正文；不读旧index/cache、额外评论或外部语料。private/access-probe也不是请求输入。已接受来源/接受记录可以提供依赖元数据，不能从其中把评价值转入规划。所有路径按项目根、原摘要及非reparse祖先验证，不能接受任意路径/SQL/身份或快照覆盖。

### 3.2 新开发消息投影

通过JointSession.dispatch的model_request和candidate_page合同取得安全字段；新宿主消息版本把完整history映射为H并保留H/S/C/b/cutoff/背景统计的原值、摘要和访问能力，原08/13文件不改。真实必要条款沿用R1/R5及批准profile，不映成c1/c2。视图名、扰动名单、管理快照ID、全局登记序号、原user_id、组别、来源路径/总清单摘要及其他候选拒读清单均留宿主侧。

构建索引/校验完整文件只是setup，不把整包视为某根实际A。方法可见的证据仍须属于该受控计划的list/read结果及当前授权范围；未请求材料不进入角色消息/画像/核验。只给摘要不能宣称读过正文。

## 4 目录生成器：一个主要入口

主要公共入口为`python -m t0_catalog prepare --authorization <独立授权JSON> --output <新目录>`。CLI是唯一目录准备入口，生产函数留在同一Module内部，不另加prepare_data阶段、服务或通用任务执行器。授权JSON绑定本文SHA、人类确认、BASE/实施候选、开发来源摘要、固定320×10×3范围、候选预算版本和唯一T0资源账；调用方不能自由改scope/model/候选/条款/限额或源路径。

授权schema固定`t0-a-authorization-0.1.0`，封闭字段为schema_version/approved/scope/contract/human_confirmation/base/candidate/program_acceptance/sources/budget_candidate/resource_ledger/api_limits；其中contract及human_confirmation各含项目内path/SHA，sources只列§3准许的来源引用，scope=development_catalog_only，budget_candidate=B02-A+B03，api_limits的count/generate/other全0。candidate与program_acceptance在实现审查结束后按同次人类确认的条件填写，不能在程序接受前启动开发准备。输出路径必须处于§6允许的新目录，不得覆盖源、账或旧目录。

成功退出0/status=T0_A_catalog_prepared_only；权限/来源/缺项/超范围/资源不足退出2/status=T0_A_incomplete并保存原因及部分覆盖。若目录完整但有已知逻辑/物理候选超额，可保留目录并明确candidate_validation=failed；不能把目录成功状态解释为候选预算通过。

公开小测试使用独立`public_catalog_test`授权及显式PUBLIC数据，保持public/synthetic标记，不能生成accepted开发状态；开发模式必须匹配真实接受链、原320根及固定输入路径。把公开夹具换标签或给它伪造320个键必须在开发门拒绝。

### 4.1 编译过程，禁止逐根完整动作链回放

1. 固定全部源绑定、320开发根、10视图和三方法计划键；重复/漏键先报错。只读取已接受b，不重新拟合TF-IDF或准备数据。
2. 每个视图建立一次只读、可释放的(snapshot/principal/τ/profile/对象版本/授权范围)索引。相同依赖单元最多编译一次：通过现有取证/生产核验合同求得登记分页、原件批读、动作/事件/策略范围及准入/推进条件，记录原始来源和逐项计量。禁止用独立参考替代生产核验。
3. 索引只复用文件校验/确定性依赖计算。按根、方法、游标分别重建**计划**账和计划回执；不复用其他根/方法的决定、修订、已取得集合或热缓存折扣。每个未来cold请求仍列对应物理请求，每次返回仍列逻辑量；A本身的实际索引I/O/模板probe数量、时间另记。计划cold/hot数量不冒称每根实测。
4. 按原`(-b, parent_id UTF-8)`队列展开每根受控状态。必要臂在第10个合格对象后立即结束该根依赖，不列第11项的list/read/assess；若前64仍不足10，按原停止/未完成语义留原因。质量臂固定64前缀。全局索引中存在某对象不表示该根请求/取得该对象。
5. 从这些受控状态组合逐轮消息。M保留需求、管理、用户画像、农产品画像、生命周期追溯、依据核验六职责；S以单智能体身份承担同样信息/能力；R只列程序依赖，无模型消息。批计划≤32，批内list/read/assess/advance逐项列出；请求批计划与读后续轮分开，画像覆盖每个实际处理候选。
6. 复用§4.2的共同组合和已接受原生mapper，准备完整W/P；不调用ModelAdapter.invoke、InputCounter.count或供应商工具，不调用RecommendationRun.run，不产生逐根publication/commit/seal。最后流式输出、冻结覆盖和摘要。

因此，A可以逐根展开消息/依赖说明，但**不为9,600根各建立完整RootBudget/EvidenceSession动作链并跑到发布**。实际依赖模板probe受同一个A资源账约束，不能把9,600次完整run改名compile。模板数量、实际dispatch次数、I/O及复用分别报告，不能隐藏在setup里。

### 4.2 与运行器映射保持一致的最小衔接

从recommendation_runner.py提取纯本地共用`compose_role_request`，接收闭合的安全状态/已获投影、角色阶段、历史/工具结果和显式候选输出cap，输出逻辑请求；现有运行器与目录编译器都用它组合context/history/工具和角色schema。只移动必要的组合逻辑，不复制第二套_context或六角色schema，不改现有公开run的fixture/c1/c2/路径限制、停止和业务验证。

ModelAdapter.prepare新增**仅准备**版本`rsm-model-prepare-0.1.0`及`execution_kind=t0_development_catalog, provenance=synthetic`。它接收完整模型/消息/工具/输出schema/cap及来源ID，不要求伪造数值输入上界、reservation或deadline；输出沿用已有openai-prepared-0.1.0的W/P和摘要，input_tokens仍null。调用同一provider_openai映射；ModelAdapter.invoke遇到该版本/模式必须发送前拒绝，不能用fixture计数/预留补成可发送请求。旧0.1/0.2/0.3合同保持。

同一显式状态、逻辑消息和mapper版本下，目录与运行器的W/P应逐字节一致；必要小型集成测试观察已有run交给替代sender的原件。该要求保证组合/映射一致，**不宣称目录已预测自然回复或B实际重放必然走同状态**。任何工具结果、ID、预算cap或消息改变均按原B10规则失效重建。

### 4.3 一个冻结的synthetic路径，不展开所有未来分支

固定脚本版本`t0-controlled-trace-0.1.0`：完整合法取证计划，每批一次读后完成，额外自选查询e=0；S/M前两个分析阶段各安排一次synthetic格式错误及宿主显式修复（共享ρ≤2），到达非空草案/核验阶段时安排一次有来源定位的synthetic阻塞Issue、一次修订及再核验（f≤1）。合法提前终止的根保留实际到达的脚本阶段和原因，不虚构final成功。恢复/错误消息复用共同组合策略，不自行漏掉或添加历史。

这是每根**一条声明轨迹**，正常阶段和失败尝试在同条路径中；不把正常/反馈/全部重试位置分别展开成多套根，更不称覆盖所有自然轨迹。受控调用公式仍为`5 + 4*ceil(n/32) + 2f + ρ + e`，适用条件照旧；64候选路径最多17槽，额外合法续轮如出现必须保留并报告超范围，不能剪掉第18轮凑上限。零候选/未完成路径按具体协议另记。

脚本回复、Issue、计划回执及受控时钟值全部明确synthetic；不写供应商response_id/x-request-id，不伪造observed usage/已通过程序发布或自然模型日志。实际模板probe原件和实际耗时另存，计划回执用确定性的root/method/view/stage序号关联，不拿跨根真实回执冒充新取得。受控回复可以引用实际获准事实，不能增加未取得材料。每个W包括该状态的完整H/允许C信息、历史重发、原文工具结果、角色互传及输出schema。

## 5 产物与覆盖合同

采用`T0-request-catalog-0.1.0`的流式对象目录，避免把全部W/P同时载入内存。每根一行逻辑清单而非9,600个完整运行目录；输出根拟定`data/ticket12-t0/catalog-0.1.0/`，已有内容拒绝覆盖。

| 产物 | 必填内容 |
| --- | --- |
| catalog.json | schema/BASE/候选/源摘要、脚本/共同组合/mapper/schema版本、预算候选、固定范围、全部组件摘要、complete及missing；不带易变时间 |
| roots.jsonl | ≤9,600个计划键、完整C/H/b绑定、停止规则/实际展开前缀、依赖引用及逐项计划账、模型槽/反馈/重试、候选预算/final、计划终态、未知和超额原因；R明确request_count=0 |
| requests.jsonl | 每个原根/阶段/尝试到prepared_id及依赖/历史/角色回复的引用，语义角色和S有效身份分别记；来源位置只在宿主侧，不丢重复请求 |
| objects/<prepared_id>.json | 每个唯一对象的完整wire_body/wire_utf8=W、count_body/count_utf8=P、模型/设置、工具/角色schema及版本、W/P/各schema SHA、各自精确UTF-8字节量；每个引用可还原完整请求 |
| dependencies.jsonl及源索引 | 唯一依赖模板、实际来源/授权/快照/版本、分页/批读、生产结果及每根计划回执映射；区分实际模板probe与派生计划量 |
| coverage.json | 计划/已列/缺失/重复/失败/超范围根及请求数，按视图/方法/终态列数；原始请求总数N、唯一对象数U、缺对象/缺阶段；I/O/token未知及原因 |
| run.json及checks/ | 易变实际执行/资源/源码指纹/实际I/O和失败原件、保护摘要、独立交付核对、复现结果；不进入稳定目录字节比较 |

去重键按现有prepared绑定：精确W/P、模型、项目命名空间、mapper和工具/角色schema版本；不能按相似文本、候选、角色或P单独合并。相同W跨尝试引用可复用对象；每个原请求仍在N和逐根计划账中。总量分别报告`Σ原引用W字节/Σ原引用P字节`、`Σ唯一W字节/Σ唯一P字节`、实际存储总字节；不能把存储量直接称上传量或token。

S/M的每轮/累计完整输入、实际输出token、实际生成费用均null；R因无模型请求，相应模型计数为推导0。全目录token总量只要存在未知就null；不计算token分位数/最大根。字节量可给max/P50/P95，但字段名必须明确bytes。

上限仍为每S/M根≤17个声明发送槽、N≤108,800、U≤N≤108,800；单完整body≤16MiB是传输保护。漏阶段/越界/超额不能用截断正文、缩C/证据、丢失败、改脚本或换模型修复；保留部分产物，complete=false并列原因。完整A目录是对声明轨迹的覆盖，不能写“全部自然请求容量通过”。

### 5.1 供应商项目及后续C衔接

供应商项目尚未绑定。本案选择**不阻塞纯本地A**：准备命名空间固定`project_id=UNBOUND-T0-DEV-CATALOG`，顶层标`supplier_project_status=unbound, external_count_ready=false`。它不是已核实的供应商项目，不读取凭据探测；不把该占位绑定作为C许可。

本流式目录不是现有openai-count-manifest-0.1.0的全量内存对象，也不是官方计数回执；现有count CLI对它应拒绝，不通过改scope/public标签使之可发送。后续C须在其另行确认的执行/费用包中绑定真实供应商项目，并将本目录**逐对象无损重prepare/转换为已登记计数目录**；prepared_id/manifest_id随项目变化重新生成，原始N及每根来源不丢。若需要给既有计数工具增加流式读取，属于届时C的明确接口增量，A不修改token_counting.py、不假称其已验证大目录内存容量。

这是本合同对A/C交付格式和项目衔接的显式补充，不回写C01—C06旧接受。本次确认即可实现并执行A；C仍受项目、实际U、费率/失败计费、金额/数据外发/调用时限及工具消费能力的独立门约束。24小时/108800次仍未启用，真实计数/生成及其他供应商API许可0。任何A修订或项目重绑均不能借换目录重领C额度。

## 6 确认后的精确文件范围

| 文件 | 允许的最小修改 |
| --- | --- |
| **新增t0_catalog.py** | 唯一CLI、闭合授权/开发选择、依赖模板/受控脚本、共用组合调用、流式目录/覆盖报告；不内置网络或供应商counter/sender |
| **新增tests/test_t0_catalog.py** | 公共CLI行为和少量共享组合/prepare/E1必要集成；公开事实与外部I/O替身，helper留本文件，不新增通用测试框架 |
| recommendation_runner.py | 仅提取/接入纯消息共同组合，支持新准备投影；现有run入口及其权限/候选/程序/发布门不放宽，不新增真实开发run |
| model_adapter.py | 仅准备schema/模式及invoke明确拒绝该模式；复用原mapper，不改原0.1/0.2/0.3行为 |
| evidence_access.py | 仅LocalEvidenceSource验证后按快照/对象建立只读索引和复用读取；文件校验/来源/授权语义保持，EvidenceSession权限/游标/逐项计量和RootBudget不改。索引不是方法热缓存 |
| 本目录diagnostics/run_check.py | 增新源码指纹和封闭`--resource-domain offline|t0`选择，默认offline兼容原调用；账根固定，限额/既有累计历史不变，禁止任意自选账目录 |
| **新增本目录diagnostics/check_t0_catalog_delivery.py** | 不导入生产的交付/保护/覆盖检查，只消费授权源元数据与A产物，不读评价目标 |
| 本目录独立authorization/verification/acceptance记录 | 先保存确认与本文原字节SHA，后留TDD、各轴原报告、A执行/复现/资源/未完成事实；不回写历史 |
| data/ticket12-t0/、.tmp/ticket12-t0/及下节两账的子产物 | 新目录/staging/对象、失败原件/报告；均不入Git，不覆盖上游/旧产物 |

provider_openai.py、token_counting.py、joint_tasks.py/joint_access.py、prepare_data.py、生产四态/质量/动作算法、配置/环境、旧测试/fixture及全部上游/论文/已有接受/工单15只读。若实现发现还需改这些受保护文件，须先指出具体合同缺口，不能静默扩范围。

## 7 公共测试Seam与逐行为验收

主要Seam：上述t0_catalog公共CLI（退出码及交付文件）。只在直接影响处补ModelAdapter.prepare/拒绝invoke、EvidenceSession.dispatch及必要RecommendationRun.run替代sender集成；不单测私有hash/parser/state helper，不另测RootBudget内部。

| 行为顺序 | 一个行为的公共期望 |
| --- | --- |
| 1 授权/数据选择 | 缺确认、错版本/来源、非开发根、跨目录/reparse即拒绝；公开2开发+1测试混合源只读2开发正文，目标/测试正文访问陷阱不触发；PUBLIC不能冒充开发接受 |
| 2 原投影适配 | history→H无损、真实条款保持；完整C/b及背景/批次一致，目录与现有源变更私有字段无关，不重算b |
| 3 依赖/停止 | 公开前10合格后没有第11项请求/计划原文；质量前缀、32分页及批读照合同；索引复用不删除逐根list/read/assess/advance逻辑或cold物理量 |
| 4 角色/续轮 | M六角色及逐候选画像、追溯计划/读后续轮分别可查；S信息并集不缩；脚本为synthetic，R的W/P数0 |
| 5 准备/共同映射 | 公开原件的字面W/P正确；相同显式状态下运行器替代sender原件与目录一致；prepare发送0，catalog模式invoke及旧count CLI消费均拒绝、实际外发0 |
| 6 反馈/重试/超范围 | 脚本反馈和两个格式修复按原轨迹各占槽、保历史；第18轮/缺材料/超过body界限保未完成，不删请求或以更短事实凑限额 |
| 7 去重/统计 | 同W不同宿主attempt只存一对象但保两原引用；改工具/schema/cap/版本不能错合并；N/U/W及P字节、缺项/失败与所有根合并报告，token保持null |
| 8 确定性/资源 | 两次独立公开生成的稳定字节一致；随机模板probe ID/实际时间只在易变审计，计划ID可复现；中断/输出冲突/资源耗尽留下partial，不覆盖或清零 |
| 9 直接影响回归 | 旧公开run守卫、prepare03映射及新索引前后E1原件/拒绝/计量一致各选最小例；旧全库、4/12/64组合、公开13组合、上游生成均不重跑 |

按mattpocock-skills:tdd一次一个行为：公共失败测试→最小GREEN，再下一个，不预堆全部测试，不为已满足行为破坏源码制造RED。真实9600覆盖由实际A交付核对，不在实现测试中提前运行真实A；小型公开cross-product测试不冒充真实覆盖。fixture的数值/字节/输出cap都不能成为官方token证据。

## 8 资源账、固定候选审查与实际A验收

### 8.1 实现测试账

唯一继承账为`data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl`。当前135次、累计**114.82704119995469秒**，剩**1685.1729588000453秒**；总上限仍1800秒，4GiB含64MiB守护。失败、测试、诊断、保护及子进程均累计；不得新领1800秒。实施前复核账/未结inflight，取实际剩余而非本文常数强制重置。

全部项目Python显式`conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -B ...`，零新依赖。该账只用于程序实施及公开测试；不能偷偷从中运行真实开发A或抵扣T0实际执行。

### 8.2 A和后续B共用的原T0账

本轮未见T0已执行记录；确认后首次真正A执行前定位并登记唯一T0资源标识。若已有同标识账必须沿用；确无旧账才在固定`data/recommendation-runtime-audit/ticket12-t0/resource-ledger.jsonl`创建初账。不可用日期、输出目录、冷/热、A/B阶段或重试另建额度。

**A（源验证/索引/实际模板probe/全目录生成/复现/保护/交付核对）+B未来全部实际工作，共享1800秒/4GiB总额。** A实际单调墙钟及失败、子进程、I/O等待均记账，进程树含64MiB守护。C仍是未授权的独立外部账，不能混入或挪用T0额度。

A实际仅一次全目录生成，再一次同输入稳定内容摘要重算作复现：不再落地第二套9600清单，只比较重算的根/请求/对象/组件稳定字节摘要；这两次准备工作都记A，不称192次中的端到端回放。真实源码/run没有调用，因此完整动作链回放次数0。复现可复用已绑定只读索引，但不复制首轮输出当重算答案。

无需假设A或B各能用满1800秒。A结束报告`T0_used_after_A`和`remaining_for_B=max(0,1800-used)`；A耗尽或未结inflight时停止，不续开干净账。A成功不保证余量足够B，B也不自动获准执行；其原规模/选择及总额不变。资源不足如实未完成，不缩开发集合或降低完整性来报通过。

### 8.3 固定候选独立双轴审查

实现/必要测试后固定candidate，以`git diff 88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a...<candidate>`及提交清单开展mattpocock-skills:code-review。Standards和Spec两个独立代理分别静态审查，不互读；Standards看项目规则/技能基线，Spec只看本文、人类确认和继承合同。审新增目录/抽取/索引/纯准备增量，不重新审已完成模型适配或批处理。

原报告保留；阻塞修复须公共RED→最小修复→定向复验→固定新候选复审。范围内的可执行遗漏一并闭合。两轴无阻塞及必要测试通过后，可依据本次集中确认直接执行A；不再补一轮相同权限询问。实际A结果由独立交付检查和保护摘要核对，不能只凭代码审查接受。

### 8.4 实际A完成标准

1. 原320开发根×10视图×3法精确覆盖，9,600个唯一计划键，缺根/重复/错组0；各S/M声明轨迹的所有实际展开阶段/重试/续轮都有完整W/P和来源，R的3,200行请求数均0。失败/提前终止根也保留清单，不能只统计成功路径。
2. 完整C/H/S/b及原资料只读；授权、版本、源摘要、游标/停止、六角色和逐项计量不变量零违例。目录完整不等于所有候选预算可行：逻辑/物理等已知超额照报candidate_failed，未知token准入保持未知。
3. N/U/重复引用/逐项和累计字节/缺阶段、缺对象、失败/超额及按视图/方法覆盖数字对账；所有对象摘要及正文可还原。超17槽、U超108800、body超界或缺正文不得标complete。
4. 同输入稳定内容复现相同，保护摘要无越界修改；资源账闭合且不超1800秒/4GiB；无新依赖、供应商API/实际模型发送/正式评价均0。
5. 分开保存“程序子项接受”“A目录覆盖/候选失败及未知”“原T0剩余资源”。只可接受`T0_A_catalog_prepared_only`，不能写T0整体/G1/G2整体/容量/预算冻结通过。真实执行有缺项则`T0_A_incomplete`并留原件，不伪造成功接受。

## 9 一次集中确认表

| ID | 推荐确认内容 | 确认后的直接效果 |
| --- | --- | --- |
| A01 | §3精确开发范围、宿主分组/数据身份键关联权限、共享文件非语义索引及禁止评价内容 | 无须读私有目标即可定位原320根；不授权额外账户/测试正文 |
| A02 | §2 B02/B03主案及名义cap/未知动态准入的准备边界 | 只作T0候选，覆盖全部资源和final，不冻结预算或正式费用，不启用备选 |
| A03 | §4一个主要CLI、共用组合、prepare-only版本、验证后依赖索引及固定synthetic脚本 | 不逐根完整run，不能把公开fixture改标签当开发任务；旧run权限保持 |
| A04 | §5流式目录、完整W/P/来源、N/U/字节/缺项、未绑定供应商项目及后续C衔接补充 | A无需未知供应商项目/计数即可执行；不把A目录当已登记可发送计数manifest |
| A05 | §6文件白名单、§7公共Seam及逐行为TDD | 只实施所列新增/直接影响行为，既有材料/算法/旧接受只读 |
| A06 | §8两类资源账及实际A含复现/交付检查 | 实现沿用剩余额度；A+B共用原T0 1800秒/4GiB，不分别重新领取 |
| A07 | 固定88e8b80为BASE的独立Standards/Spec增量审查和修复流程 | 先程序接受，再按同次授权直接执行A；不重复旧模型适配审查 |
| A08 | §8.4完成标准及本节授权终点 | 确认后可直接实施并执行A；C/B/P1、真实费用、token最大根/容量判断、预算冻结、链部署、15冻结及工单12关闭均不在授权内 |

仍未知且不阻碍纯准备A：实际N/U/载荷大小、实际生成/复现耗时及B剩余资源、真实供应商项目/联合字段接受/计数费率和失败收费、每轮官方完整输入数、自然输出及动态cap、整体预算是否可容纳。A运行后只更新其能测得的目录/字节/资源事实，其余继续null/unknown。若A内发生权限/源版本/17槽/资源不足，保留失败停在未完成，不另向未经确认路径绕行。

本轮交付自检：仅新增本Markdown；生产/测试/配置/环境/论文/历史接受改动0，项目Python/测试/供应商API/T0执行0，原离线累计账仍135次/114.82704119995469秒。本轮按人类要求停在A01—A08的一次集中确认点。
