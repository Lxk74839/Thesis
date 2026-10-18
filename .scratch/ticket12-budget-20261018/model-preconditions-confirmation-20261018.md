# 工单12：模型接入前置条件集中确认

日期：2026-10-18（Asia/Shanghai）。Status: **待一次集中确认**。工作目录：`C:\Users\Kane\Documents\CodexProject\Thesis`。本文件是独立新增提案，不回写原B01—B12表、F1/F3正文、历史接受记录或工单状态。

本轮只查官方公开资料、只读检查现有合同/接口并编写本文件；没有运行项目Python、测试、供应商计数/生成API、T0或P1，没有安装依赖、改代码/配置或批准费用。继承`023a6cc5b906541f01b56cfd805594719bfac557`的[批处理分项验收](acceptance-offline-batch-20261018.md)及[两轴审查](verification/review-6ca3446.md)：30项通过、受控9/9/13调用、Standards和Spec各0阻塞/0非阻塞。本轮不重跑、不重新审查该实现。

**推荐：B09采用零新增第三方依赖；B10采用官方完整输入计数，作为单独的外部前置步骤；T0本体保留零API，只导入逐请求绑定的计数回执。** 一次确认后可直接实施的是本文规定的离线适配、计数工具及公共测试；不自动执行外部计数、T0/P1或任何正式模型发送。计数费率没有被公开资料闭合，不能承诺外部步骤确认后就可无条件执行。

## 1 已核实事实及证据边界

核验仅沿用既定主案：OpenAI直连Responses，固定`gpt-5.4-mini-2026-03-17`，`reasoning.effort=none`，文本、自定义函数工具、strict角色输出；不重新选型。

| 已核实事实 | 官方依据与实际限制 |
| --- | --- |
| 模型页列明上述日期快照、400,000上下文、128,000最大输出，支持Responses、函数调用及结构化输出；支持none | [模型页](https://developers.openai.com/api/docs/models/gpt-5.4-mini)。这是公开能力，不是本项目账户可达性或联合字段实调证据 |
| 官方提供`POST https://api.openai.com/v1/responses/input_tokens`，用于发送前完整输入计数；包括消息结构和边界，不能由纯文本分词代替 | [计数指南](https://developers.openai.com/api/docs/guides/token-counting) |
| 计数参数明确列有`model/input/instructions/tools/tool_choice/parallel_tool_calls/reasoning/text/truncation`；`text`支持结构化输出配置 | [计数接口参考](https://developers.openai.com/api/reference/python/resources/responses/subresources/input_tokens/methods/count)。模型字段是模型ID字符串；未发现该快照的单独支持矩阵或排除项，因此文档级适配有依据，实际组合成功仍未知 |
| 计数成功返回`object=response.input_tokens`及整数`input_tokens`，没有返回模型ID、生成usage或计费凭证 | 同上。只能记录“请求了哪个模型”，不得伪造“计数响应回显模型”或生成费用为0 |
| 生成的`max_output_tokens`、`service_tier`、`store`、`stream`不在上述计数端点参数表中；`service_tier=default`对应Standard | [生成接口](https://developers.openai.com/api/reference/python/resources/responses/methods/create)。两端字段不能逐字整包照搬，须采用下述明确投影 |
| 工具调用及工具结果用`call_id`关联；strict工具schema与角色JSON输出schema是两种配置 | [函数调用](https://developers.openai.com/api/docs/guides/function-calling)、[结构化输出](https://developers.openai.com/api/docs/guides/structured-outputs)。格式正确不替代既有事实/引用/资格门禁 |
| 模型公开生成报价为每百万普通输入/缓存输入/输出USD0.75/0.075/4.50；计数指南、计数参考和价格页未给出计数端点的独立费率或明确免费声明 | [模型页](https://developers.openai.com/api/docs/models/gpt-5.4-mini)、[价格页](https://developers.openai.com/api/docs/pricing)。不能将生成输入价套作计数价格，也不能由“无生成”推出免费；失败计数的收费规则同样未知 |

本文件所称“完整计数”只指供应商对**该次已冻结请求输入**返回的计数，不是自然后续请求的上界。输出总量仍按供应商`output_tokens`结算，包含隐藏生成；推理子项不得再加一次。价格仅供适配会计，不批准正式费用。[计数/输出口径](https://developers.openai.com/api/docs/guides/token-counting)

## 2 B09：不新增tiktoken、SDK或分词资源

tiktoken的剩余用途是辅助比较纯文本长度或提示压缩；本次所需的硬门是含角色边界、工具和输出结构的完整输入计数。前者不能提供后者，当前也没有必须按本地文本token拆分的行为需求，故不增加该辅助功能。

- 新增第三方包、传递依赖、Windows wheel、encoding下载及其资源摘要：**全部为0/不适用**，不是“待补空白锁”。不新增`requirements-model.lock`，不修改`environment.yml`或现有环境锁。
- 沿用Thesis Python3.13.16。JSON、SHA256、文件及HTTPS使用标准库；不引入OpenAI SDK、requests/httpx、tokenizers/transformers。HTTP边界仅为一个注入式、无自动重试的发送函数。
- 原环境文件SHA256：`environment.yml=5077dee22f2476e4fa7c6306960601b304fe3a0b48d00efa4e01a7065570a6ed`；`environment-win-64.lock.txt=b3f0541f82239c2ba77176c3bb1b1905790589f2223e8a596c0994948de5e6a0`。后续执行前核对既有解释器/锁，不以此声称当前已经做过新运行验证。
- 可以记录UTF-8字节作传输限制和摘要输入，字段明确叫`wire_bytes`；不输出伪完整的`local_input_tokens`或可证token上界。将来确需文本分词，再独立提出版本/wheel/传递依赖/资源SHA及安装授权，不夹带进入本范围。

## 3 B10：同一请求准备、完整计数及实际发送合同

以下是待确认的工程约束，不是官方提供的签名或原子事务。官方计数和生成是两个独立请求；本地用冻结内容及审计防止二者漂移。

### 3.1 冻结唯一原生请求

`ModelAdapter.prepare(request)`只做本地映射，生成`openai-prepared-0.1.0`：完整生成body、计数body、两者SHA256、模型/设置/mapper/tool/role-schema版本、来源根/角色/阶段绑定、缺项列表。它不调用计数、不发送生成、不预占一次模型调用。

生成body记为W；计数body记为P。JSON固定UTF-8、`ensure_ascii=False/sort_keys=True/separators=(',', ':')/allow_nan=False`；保留数组顺序、原字符串、换行和Unicode，不做额外规范化。实际HTTP必须使用留存字节，不能在计数后重新组装内容。

| 请求内容 | W：生成body | P：计数body |
| --- | --- | --- |
| 模型 | 固定日期快照，不接受别名/降级 | 同一精确字符串 |
| 消息/历史 | 既有安全消息序列映射为Responses `input`；原content对象先规范化为明确的文本；assistant函数调用及对应`function_call_output`按原顺序保留 | 与W中已完成映射的`input`完全相同，包含重发历史、角色互传及实际工具返回 |
| 指令 | 原system/developer指令放在input中；不再重复放一份instructions。若未来使用instructions字段，须显式升级合同 | 与W一致，不自行遗漏或补加 |
| 工具 | 本地已绑定工具映射为`type=function`、名称、描述、`parameters`及`strict=true`；无托管检索/代码执行/子代理 | 同一完整工具数组及顺序 |
| 输出结构 | `text.format={type:json_schema,name,strict:true,schema}`；按当前角色/阶段的已绑定封闭schema，不丢必填业务字段 | 整个`text`原样计入，不能只数schema正文字符串 |
| 推理/工具选择 | `reasoning={effort:none}`、`parallel_tool_calls=false`；有工具时`tool_choice=auto`，无工具时none | 同值；无工具时统一显式空数组及none |
| 截断 | `truncation=disabled`；该字段参考标为deprecated，未来移除须更新合同 | 同值，禁止auto截断 |
| 输出/服务与保存设置 | `max_output_tokens`取阶段与根剩余的受保护较小值；`service_tier=default/store=false/stream=false` | 不向计数端点发送不支持的这四个字段；仍全部纳入W摘要及发送门 |

P只允许上表计数端点支持的字段，不把内部run/request/reservation ID或deadline当作供应商body字段；这些标识保留在宿主审计。禁止`conversation/previous_response_id`、文件/图片/URL引用、prompt模板、自动压缩、personality及缓存控制扩展，避免未显式冻结的服务端状态。S/M采用完全相同的模型、设置、工具能力和计数规则。

### 3.2 计数回执和重新计数

新增公共`InputCounter.count(prepared, *, authorization)`。离线调用仅查已导入回执，缺失返回`count_missing`；只有单独的外部计数许可才允许一次POST计数。native fixture的字面计数使用`basis=fixture`，永不升级为`basis=official_input_tokens`。T0导入官方回执仍无API；不允许在T0中cache miss后懒调用。

`openai-count-receipt-0.1.0`至少保存：receipt/manifest ID，W/P摘要，所请求的精确模型，mapper/工具/角色schema版本，供应商项目绑定，时间，HTTP状态及实际`x-request-id`，原始响应/摘要，整数`input_tokens`，计数尝试ID和来源。`returned_model=null`如实记录；费用证据另存，缺失为unknown。导入需核对宿主已登记外部尝试与原始回执，不能凭任意手写正整数或fixture字典取得发送资格。

缓存仅复用同一冻结目录内、同项目、同精确W/P/模型/版本的成功回执；每个原根/阶段/发送尝试仍引用其对应条目。失败不产生可用缓存。任一内容、工具、输出结构、推理/服务设置、输出cap、映射版本或模型变化，旧prepared/计数绑定失效，重新prepare及计数；即使P偶然相同，也不把旧W回执自动改签给新W。只修改宿主attempt ID而W不变，可引用同一回执；每次生成仍重计全部实际输入及费用。

`ModelAdapter.invoke(request)`的新版本`rsm-model-request-0.3.0`关联`prepared_id/count_receipt_id`及根reservation/deadline；旧0.1/0.2字节/fixture路径保持。新版本在sender前核对留存字节、版本、回执、能力、当前输入数、输出cap、费用及最终预留，任一缺项拒绝且生成attempted=false。通过后一次invoke最多一个生成发送尝试，无内置重试；请求/响应/用量/错误保留。

官方计数用于单请求`I`，阶段输出cap为`O`；至少核对`I+O<=400,000`、`O<=128,000`及待确认F3更严格的单次/累计/最终预留。没有计数时I为null，不能用字节或fixture估值放行。发送后的usage与预计输入不一致、缺失、费用无法结算或晚到，保留原件和占用并停止；不用较小的实际值回写篡改预检证据。计数不是生成usage或计费凭证。

原生适配保存HTTP状态/原始body、供应商response ID/x-request-id/返回model及service_tier，与本地request/attempt/reservation分别关联；不伪造它们相等。usage保存input/output总量、cached/reasoning子项及实际提供的cache_write等细项，检查非负整数及子项不大于总量；缺必需细项不凭空补0。主案已知价下费用向上取整为微美元；未绑定的附加费或非零cache_write不能悄悄忽略。错误有无usage分别处理，超时/断连不宣称免费；只在用量/费用已知且原共享重试许可仍在时，由宿主显式发起下一次尝试。[原生字段](https://developers.openai.com/api/reference/python/resources/responses/methods/create)、[错误类别](https://developers.openai.com/api/docs/guides/error-codes)

## 4 独立外部计数步骤C：范围、数量、费用和停止

**步骤C是API调用，不是零API。本文请求确认其合同和实现，不请求现在执行或支出。**

1. 先有冻结全量目录：每个开发根/方法/视图的受控路径列出每次完整W/P及出处，包括读后续轮、反馈/格式修复/重试时实际会变化的消息和最终提交。不得只导出首轮、代表角色、最大字节样本或已通过批处理的4/12/64夹具。
2. 对精确相同W/P去重，建立所有原根/阶段到唯一计数对象的引用；R没有模型请求，计数0。无完整目录就不开始外部步骤。去重不减少业务候选、证据范围或根覆盖。
3. 以目录首个实际待计body验证既定快照及联合字段，不加“hello”试发。若成功，这次本身就是该条计数，不重复测；若不支持，停止，不换模型、删schema或跳到生成API探测。
4. 所有唯一对象逐个串行计数，预登记一次尝试后只发送一次。错误/超时/断连/429/5xx/畸形计数全部停止该阶段并保留失败及未知占用，不自动重试、跳过失败或换目录续开额度。人工修正后的再次尝试也占同一阶段剩余额度，须符合已授权许可。

| 外部执行许可须固定的项目 | 推荐合同与上限（本轮不启用） |
| --- | --- |
| endpoint/模型 | 仅上述OpenAI计数POST、既定快照及冻结版本；生成POST、Files/Models/其他API调用上限均0 |
| 发送内容 | 完整P，因而含开发白名单H/C、安全角色消息、实际取证结果、工具和输出schema。哈希不能代替正文；不发送私有评价标签、测试推荐表现、凭据、论文或本地路径。缺少任何必要正文就不称完整计数 |
| 调用数量 | 精确目录去重对象数U；全阶段累计HTTP尝试（含失败）不得超过U，且绝对不超过**108,800**。这是`320×10×2(S/M)×17`的计数规划安全封顶；17只限制本外部目录的槽数，不批准B02模型调用上限或正式费用。若完整脚本有任一根超过17槽或U超上限，外部阶段开始前报范围不足，不能截掉多余请求。公开故障fixture离线验证，不另发API；冷热回放复用相同W回执 |
| 时间/内存/传输 | 拟独立外部阶段累计墙钟<=86,400秒、并发1、单次<=30秒、进程树<=4GiB。单body<=16MiB、计数响应<=1MiB，超出拒绝而不截断；字节限额只是传输保护。24小时是停止上限，不是吞吐或全覆盖保证，也不占用/改写原零API T0的30分钟本地账；等待网络也计外部墙钟 |
| 费用依据 | 查阅来源未公开计数端点费率/免费及失败计费规则；**单次价格、总费用估算/上界均unknown**。不得套用模型生成输入价、把U当免费调用或挪用USD600/USD6,000 |
| 金钱/发送门 | 当前计数支出授权0、实际允许调用0。以后许可必须另固定官方可核查费率/失败规则、币种、项目及独立总金额上限，再逐次预留；任何一项缺失，第一条之前停止。即使将来确认免费，调用数/墙钟/数据外发和失败记录仍受限；本次技术确认不等于该执行许可 |

成功覆盖要求每条原始请求引用到有效完整回执，导入后按原根累计I，包括历史重发和每个实际重试。覆盖报告列总根/请求/唯一对象/有效回执/缺项/失败数量；少一条就只能报告部分覆盖，不能以抽样或缺项排除后的分位数宣布全部容量通过。

自然模型生成的后续内容在步骤C之前未知。C只证明冻结的受控轨迹；将来P1/正式执行中每个新的W仍需独立完整计数授权及门禁，不能沿用受控轨迹的token数。动态计数的请求量、成本和网络时间必须列入届时共同资源包络，尤其final计数不能占用普通阶段保护或假装旧60秒已足够。本文不授权在线动态计数或重定F3数值。

## 5 原B10及T0衔接的集中修订清单

原文保持只读；确认后另存修订及接受记录，不覆盖历史。原合同的“不调用付费计数接口补洞”与本提案存在实质变更，不能解释为原合同本来已允许外部计数。

| 位置 | 原要求/缺口 | 推荐改为 |
| --- | --- | --- |
| 原B09、spec§6/§9 | 待补tiktoken/wheel/encoding锁 | 零新增分词依赖；沿用现有Python锁；删除新分词锁及environment修改的实施需要 |
| 原B10、spec§8的InputCounter | 纯本地完整计数或可证上界；完整结构未知 | prepare为纯本地；InputCounter区分官方回执导入/独立外部POST/fixture；只有逐请求官方回执支持本文完整计数门 |
| [原F3正文§10](../data-preparation/ticket12-final-experiment-protocol-review-20261016.md)第2项 | 核对本地分词；不调用付费计数接口补洞 | 删去本地完整计数作为唯一途径；零API T0可以使用独立C已获授权取得的完整回执，外部调用/费用/耗时另报且不伪称0 |
| spec§10 G2/G3先后 | G2完整计数全齐才允许T0，T0又负责生成全开发消息清单 | 拆为G2a模型/映射/零新增依赖合同接受；另获T0本地执行授权后可做A离线目录准备；C单独执行许可；G2b全量回执闭合后才做B容量统计/极值选择与回放。避免靠抽样绕过循环前置 |
| 原T0技术范围 | 9,600清单、极值<=90根、冷热<=180次、新故障<=12、总回放<=192；1,800秒/4GiB | **全部数量、开发账户/视图/选择与并列规则保持**。A+B共享同一个原T0累计本地账，不逐根完整重放9,600条来导出消息；C在二者之间独立记账。R的累计模型输入为0 |
| T0结论及统计 | 全开发token分布、token最大根选择依赖完整计数 | A只报目录/依赖/其他可核查事实，token保留null；G2b后才对全部原根累加并选token最大根，不按字节替代。正常/失败及缺项同时报告；不能只报成功子集 |
| F3会计及未来发送 | 模型调用、E1工具、token、时间及final共账 | C计数调用在独立API账，不冒充生成或E1工具，也不免费隐去。未来动态计数须计入同根时间/费用和独立调用上限，final新增依赖须重新闭合；本轮不改17/192k/24k/900秒等候选值或冻结预算 |

原T0规模是[已确认正文§10](../data-preparation/ticket12-final-experiment-protocol-review-20261016.md)及[前案直接引用](spec.md)的继承范围。**本次确认只接受上述衔接合同，不触发A、C或B执行。** 原B02/B03/B06等未确认数值不因此获批；T0开始前仍需适用预算候选及其他前置门合法闭合，不能用G2a替代G0。T0仍需单独执行授权；P1、真实延迟/自然完成率、正式费用、链部署、15冻结、工单12关闭均不在本轮。

## 6 确认后可直接实施的文件与公共边界

实施BASE固定为`023a6cc`；实施前先单独归档人类确认及本文SHA，原提案不回写。新版本不放宽旧scripted_public fixture，也不借native映射开放正式数据/真实执行。

| 文件范围（项目根相对路径） | 允许的最小实施 |
| --- | --- |
| `model_adapter.py` | 新纯本地prepare及0.3.0分支；prepared/计数/预留/版本核对；native响应到现有规范化消息与usage映射；旧0.1/0.2保持 |
| `provider_openai.py`（新增） | 单一Responses W/P映射、封闭工具/角色输出schema及native结果归一化；单次HTTP计数发送边界，固定HTTPS origin、禁redirect/自动重试。生成只有注入式sender边界，本范围不实现真实HTTP生成发送函数 |
| `token_counting.py`（新增） | InputCounter、冻结目录导出/导入/覆盖校验和独立外部计数入口；许可缺失拒绝。提供`python -m token_counting export/count/import`三种明确命令，count默认拒绝且不读环境凭据探测；本阶段测试全部使用注入式HTTP替身 |
| `recommendation_runner.py` | 只加native公开fixture分支，prepare→离线回执查询→根预留→invoke；完整I替代该分支的字节计量，普通/final保护和失败留账沿原入口观察。真实live run继续拒绝，不扩展原c1/c2或正式数据路由 |
| `tests/test_provider_openai.py`、`tests/test_token_counting.py`、`tests/provider_fixtures.py`（新增） | 只用公开原件和明确字面计数；覆盖下表新增公共行为；既有测试/fixture不改 |
| 本目录`diagnostics/run_check.py`、新增`diagnostics/check_model_delivery.py`、`verification/`及独立实施/接受记录 | 守护仅增新源码指纹范围，保留原账路径、累计历史和额度；新交付检查器不导入生产，核对公开原件/回执关联及保护摘要，失败不覆盖 |

`evidence_access.py/RootBudget`、joint模块、业务核验/评分/融合/动作模块、配置、账户/C/H/S/质量主点、论文/研究、旧接受、reports和工单15保持只读。计数费用/时间在允许的集成分支复用既有RootBudget资源预留；不增加第二套根预算或为计数放宽原工具权限。目录工具只消费显式prepared清单及对应引用，不在本阶段新增或运行全开发T0枚举器。

新测试入口仅`ModelAdapter.prepare`、`ModelAdapter.invoke`、`InputCounter.count`、必要`RecommendationRun.run`集成，以及目录导出/导入的`python -m token_counting`公共CLI。provider/HTTP/文件/时钟为外部Seam，用替身观察发送次数、字节和实际输出，不单测私有mapper、hash函数或RootBudget内部。CLI的export接受prepared JSONL及output路径，import接受manifest/receipts/output路径，count接受manifest/permit/journal路径；以退出码和交付文件观察覆盖，不测试内部函数。新native fixture显式标记`execution_kind=openai_native_fixture`、`usage_basis=fixture`且`provider_requests_sent=0`；假HTTP计数/费率/回执同样标fixture，不能被external或live许可接受。

| 行为顺序 | 公共可观察期望（未来逐个测试，不是本轮测试结果） |
| --- | --- |
| 1 准备与映射 | 字面官方格式的完整消息、工具结果及strict输出被保留；W/P字段分别正确、相同输入同SHA；prepare发送0次 |
| 2 变化失效 | 改消息/工具/输出结构/模型/设置/输出cap或版本，旧回执不能放行；缺失/未知字段不静默剔除 |
| 3 零API查回执 | 缺计数为null/count_missing且sender0；fixture整数只在native fixture生效，不能获得官方/live资格 |
| 4 外部许可及单次发送 | 未授权/费率或金额不全/目录不完整/调用或时限不够时POST0；许可完整的公开替身返回只发一次完整P，发生redirect/429/超时不偷偷重试 |
| 5 回执解析与完整覆盖 | 布尔/负数/缺字段计数拒绝；原件、W/P、模型/版本/项目不匹配拒绝；跨根重复W可引用但每个原请求都在覆盖表；缺一条不报全量 |
| 6 invoke及会计 | 字面native function_call、call_id、输出文本、refusal/incomplete/error逐项映射；100输入/40缓存/30总输出/20推理归一化仍为100/30、183微美元，推理不重复加；未知usage/越预留/晚到保占用并停 |
| 7 运行器集成 | 新分支用完整I作累计/单次/预留核对，超限不生成发送；复用最终预留，计数缺失不取final槽补救；R不产生计数或生成。六角色和原批停止/取证能力直接继承，必要时仅针对改动调用链做小型回归 |

按已确认的[mattpocock-skills:tdd](C:/Users/Kane/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/tdd/SKILL.md)实施：**一次一个新行为、公共测试实际RED后最小GREEN**，不预写整批测试；已接受行为直接引用，不为制造RED破坏实现。只运行新增测试及因prepare/invoke调用链改变而直接受影响的旧接口回归，不重跑30项批处理收口、旧全库、公开组合或上游生成。

## 7 后续计算额度、独立审查及门禁

- 推荐沿用既有离线实施累计账`data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl`，**不新领/重置1,800秒**。已记70.26800119999098秒，后续最多剩1,729.731998800009秒；以实际账末值为准，失败/诊断/保护及子进程全部累计。进程树4GiB含64MiB守护预留；沿用唯一inflight及递增编号，新产物用独立文件名而非新账清零。若不足，停止保留证据，不借原T0额度。
- 所有项目Python显式`conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python -B ...`，不安装依赖。离线实施API/正式模型费用均0；此阶段不触发任何外部预检。
- 完成后固定新的候选提交；按[mattpocock-skills:code-review](C:/Users/Kane/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.1/skills/engineering/code-review/SKILL.md)，两个独立代理分别审Standards和Spec，固定`git diff 023a6cc...<候选>`，保留原报告。Standards用项目规则及技能基线，Spec只用本文件与人类确认；不将原整张B表视为授权。审查后必要修正继续同账、定向测试并固定复审，不重审已接受批处理差异。
- 提交只含上节必要文件及本目录新增确认/实施/审查/验收记录；reports、既有产物、环境及生产预算配置不纳入。通过只代表离线适配合同实现，不宣称官方计数可达、真实容量/G1/G2整体通过。

## 8 一次集中确认项与剩余未知

以下C项构成一个**技术实施包**；人类可一次确认全部，或指出具体改动。不是重开B01—B12整表确认，也不将现有批处理结论重新置疑。

| ID | 请求确认的具体选择 | 确认后的直接效果 |
| --- | --- | --- |
| C01 | B09零新增第三方依赖，保持Python3.13.16及两份现有环境文件 | 不再等待tiktoken版本/wheel/encoding空白锁；无安装 |
| C02 | B10采用§3完整官方计数回执、W/P绑定和变化重计；纯本地只prepare/回执导入/fixture辅助 | 确认可实现的公共接口和拒绝规则；不把本地字节当token |
| C03 | §4外部计数合同及108,800绝对调用安全封顶、完整目录/费用前置/停止规则 | 只批准实现许可门与计数工具；**当前外部执行许可、费用授权仍为0** |
| C04 | §5的B10/F3/T0衔接修订：A离线准备→C独立计数→B零API容量回放；原规模不变 | 解除“计数全齐才准准备计数目录”的循环；不执行任一阶段 |
| C05 | §6白名单、五个公共Seam及逐行为TDD；真实HTTP生成函数/live run继续不开放 | 确认后可直接离线实施，不再就已列接口逐个询问 |
| C06 | §7继承剩余计算额、同账及固定BASE双轴独立审查、最小提交 | 所有失败累计且不重复旧验证；不借T0额度、不重开任务 |

公开资料仍不能消除的未知：账户能否使用该快照计数、联合字段实际接受/strict子集兼容、计数及失败费率、全开发目录实际U/上传量/耗时、全部受控轨迹的真实输入数及预算是否容纳、自然生成后续载荷与供应商延迟/费用。前四类中的实际调用事实只能在以后明确获批的外部步骤取得；费率/支出证据未齐则该步骤不启动。**确认本技术包不会将这些未知改写为已通过，也不保证T0或预算候选可行。**

本轮交付自检：仅新增本Markdown；生产/测试/配置/环境改动0，项目Python/测试/供应商API/T0/P1执行0；`023a6cc`及旧接受直接继承，未提交新实现。完成后等待本表一次集中确认，不自行开始实施。
