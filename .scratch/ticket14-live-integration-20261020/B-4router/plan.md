# B阶段合同补充：4Router 接入方案

日期：2026-10-20。状态：接入方案与独立配置草案，未实施、未联网验证。
继承A验收与代码候选e34ef4a2a291e21184f5cc37e20a0d7983d2a1b2；当前归档HEAD为f62591d89417b71fed26655cb38bc38ec48ed141。仅补原draft.md第3.2、4、7、8节的渠道差异，A的测试、双轴结论及数据接受链直接复用，不重新审查。

## 已确认与可实施部分

用户已确认渠道`4Router`、base_url=`https://4router.net/v1`、精确模型ID=`gpt-6-luna`，目标为冻结100用户、18场景、单轮。这里单轮沿用冻结任务的`repeat=1`；六角色与工具往返仍可能需要多次模型请求，不能解释成每任务只发一次生成。

目标继续引用plan_id=`9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088`、plan.json的3910字节及SHA256=`ced63edbf099271cc9ba5282c6d4f1ee918353c9319b0e4c6bc8d4e927d25316`。冻结清单记载5000任务、3400模型任务；它们不是API调用额度。R/S/M及Q适用方法均按原清单，Q的三个质量组件不额外生成。用户、场景、repeat、任务键及原计划中null/false均不回写。

本目录`config.draft.json`仅记录已确认值、未知项和待确认建议，不是可执行配置，不直接传给A的UNBOUND清单校验。今后确认完整配置后才按原合同生成独立`configuration/<config_id>.json`和对应内容摘要；probe、开发试跑、正式执行各有独立授权记录，绑定config摘要、冻结plan_id及各自清单/任务键。A的独立1账户8任务清单保持冻结、不执行；100用户目标范围也不构成正式授权。

现在可以确定单一Responses mapper、计数投影、授权拒绝行为和外部transport夹具的离线实现方案；本步只交付这些合同与测试清单。渠道能力未知不妨碍写拒绝测试，但不能据此宣称真实接通。

## 公开资料核对及待验证边界

证据等级仅分“用户确认”“文档声明”“待验证”；本轮所有网络能力实测均为无。4Router资料详见public-sources.md，检索未命中不能解释为服务不支持。OpenAI资料只作为Responses协议基线，不证明4Router透传或本账户可用。

| 项目 | 已取得的依据 | 4Router处理及状态 |
| --- | --- | --- |
| Responses | 4Router教程明确给出base_url及wire_api=responses，但示例是旧模型和Codex客户端配置。[渠道文档](https://docs.4router.net/guides/codex/) | 拟使用`POST https://4router.net/v1/responses`。这是协议路径推导，精确模型/分组的原始HTTP能力仍待验证；不照抄教程模型或客户端远程压缩设置 |
| 精确模型 | OpenAI模型页列出`gpt-6-luna`及Responses、函数调用、Structured Outputs能力。[模型基线](https://developers.openai.com/api/docs/models/gpt-6-luna) | 请求ID字符串固定，禁止替换教程旧模型或备用模型；4Router公开页不足以确认本令牌可用性。返回model必须符合事先确认的身份规则，不临时接受其他别名 |
| 函数工具 | OpenAI使用`type=function`工具，返回`function_call`，以`call_id`关联`function_call_output`；推理模型返回的reasoning items有续传要求。[函数调用](https://developers.openai.com/api/docs/guides/function-calling) | 自定义函数闭环待验证。只映射既有获准工具，宿主执行；不启用web/search等服务端工具。唯一调用ID、参数Schema与结果配对继续校验；不能把普通文字当工具调用。无法无损处理的reasoning/续传项应停止，不静默丢弃 |
| 结构化输出 | Responses角色输出使用`text.format={type:json_schema,name,schema,strict:true}`，不同于只保证JSON语法的json_object。[结构化输出](https://developers.openai.com/api/docs/guides/structured-outputs) | 严格Schema透传及既有角色Schema支持子集待验证；保持现有封闭角色Schema和本地校验，不降级成提示词约束、JSON模式或程序补答案 |
| usage | 协议基线含input_tokens/output_tokens/total_tokens、input_tokens_details.cached_tokens及cache_write_tokens、output_tokens_details.reasoning_tokens。[Responses响应](https://developers.openai.com/api/reference/python/resources/responses/methods/create) | 渠道实际字段及含义待验证。保存原始usage；子量不再加到父量，缺字段留null，不填0。缓存写入或未知计费明细不能沿用旧公式忽略；token已知与费用已绑定分开记录 |
| 发送前完整计数 | OpenAI公开`POST /v1/responses/input_tokens`，说明完整输入、历史、工具和结构格式均影响计数；字符和局部tokenizer估计不足。[计数基线](https://developers.openai.com/api/docs/guides/token-counting) | 候选为`https://4router.net/v1/responses/input_tokens`，但4Router支持性、完整覆盖与计费均未取得公开承诺；确认端点及能力保持null，这是生成前真实阻塞 |
| 请求ID/错误 | 渠道FAQ只提供部分认证/模型不可用示例。[渠道FAQ](https://docs.4router.net/guides/manual-config/) | HTTP状态、有限原始错误体、发送状态独立保存；本地request/attempt/run ID不覆盖response.id或渠道请求头。渠道未给ID时留null，不能造一个供应商ID。具体错误对象及响应头名待验证 |

4Router分组会影响可用模型、接入方式和服务层，文档要求以控制台实时显示为准；不能自动选择AppCodex/GptApi等分组，也不捏造分组请求头或在模型ID加前缀。配置中的token_group和group_binding_method均留null，待提供非秘密分组信息及选择方式。教程的Codex provider name不等于本项目渠道身份，也不需要安装其一键配置或改全局Codex设置。[分组文档](https://docs.4router.net/guides/model-groups/)

## 完整计数、发送及结算的最小补充

沿用`ModelAdapter.prepare/invoke`和`InputCounter.count(prepared, authorization=...)`，只新增4Router明确分支；不增加注册表、自动路由或多供应商框架。

1. `prepare`保持纯离线：从独立配置读取模型/渠道/分组/mapper和已确认请求参数，构造完整生成正文；固化UTF-8正文、工具及角色Schema摘要和config摘要。body中`model`只允许精确指定ID，不调用旧MODEL/价格路径。
2. 计数正文从同一准备结果投影，保留所有影响输入的字段：完整input（安全初始输入、各角色完整历史、已返回工具调用和结果、实际画像/证据上下文）、instructions（若有）、tools及参数Schema、text.format及角色Schema、reasoning/tool_choice等实际输入设置。只移除端点明确不接受且不影响输入的生成控制项；允许移除清单必须由能力确认和定向测试锁定，不能为使接口成功逐项删掉工具或Schema。
3. 不使用previous_response_id、服务器会话或自动压缩来替代本地已固定历史；上下文超限停止，不隐式截断。请求参数里的none推理、stream=false、store=false、truncation=disabled、parallel_tool_calls=false仅为本草案建议，确认前不继承旧默认值；none是为缩小首个协议探针范围提出的新建议，不是认领旧设置。若需reasoning续传，先完整保存/回传其协议项并纳入同一次计数；未支持则能力拒绝。
4. count同样先核config/授权、价格上界及包级count次数/费用预占，写count intent后才发送；回执绑定channel/base_url/group/model、project、mapper、正文/计数/Schema摘要和操作ID。计数回执来源为4Router原生计数（待证），不能标成OpenAI直连官方回执；注入transport仍是fixture。旧T0的9600根许可及缓存不能套用。
5. 可靠count成功后，按已确认收费规则的最坏输入费率、输出cap和附加费用预占根级及包级预算，再写生成intent发送一次。费用单位到原cost_microusd账键的币种/换算/向上取整规则也须确认；不假设缓存命中，不采用旧截图或OpenAI标价当实际4Router费率。
6. 只允许确认的HTTPS主机/路径和显式时限/大小限额，无隐式重定向、SDK重试或模型回退。归档原始响应、原生usage、返回模型/服务层、实际发送计数、请求标识和trace；按尝试结算，不累加累计快照。输入usage须与绑定的可靠计数符合确认比较规则；漂移、未知发送、未知费用或缺usage都保留占用并停止，不猜免费、不补发。

若渠道确认没有可靠完整计数，本合同下仍是`incomplete_count`并禁止生成；改用Chat Completions、另一渠道计数、tiktoken估算或放松预算合同均不是本次方案的隐含备选。

## 最小代码修改范围与定向验证（均未实施）

| 文件/公共接口 | 仅有的必要变化与针对性测试 |
| --- | --- |
| 新`provider_4router.py` | 一个渠道的prepare/verify、count投影、HTTP封套与规范化。复用provider_openai的纯JSON/Schema助手；旧provider_openai.py保持只读，不调用其绑定旧模型、主机或费率的prepare/send_count/normalized_usage路径。用手写HTTP封套验证model、工具往返、strict角色输出、原生usage、未知字段/错误和本地/供应商ID分离 |
| `model_adapter.py`的prepare/invoke | 仅增加绑定4Router配置与授权的明确分支；注入transport永远保留fixture来源。测试参数缺失无网络、错config/group/model拒绝、trace/请求次数、拒答/截断/格式、未知usage及未决intent不重发；既有PUBLIC/native fixture路径不变 |
| `token_counting.py`的count | 增加新清单/探针许可和同输入回执关联，不放宽旧_external/T0限制。测试tools/角色Schema/历史/工具结果任一变化均使回执失效；正确字节投影、错项目/模型/分组拒绝、缺count停止、实际/未知计数费用占用 |
| `experiment_runner.py`、`recommendation_runner.py` | 在既有execution_record接独立config/authorization摘要和真实发送/usage计数，复用安全装配、RootBudget与发布门。包级generate/count/other预占是已有合同待补接线，不声称RootBudget已覆盖全包；局部记账，不另造预算框架。测试授权前不读凭据/不建运行账；正式键不能借开发许可运行；最终预留、失败/重试、Q同一次A/G不重复收费 |
| `experiment_io.py`（真实评价获准时） | 原转换/纯score_task/summarize复用；增加仅经授权的真实输出与已接受参考来源分支，替换写死的synthetic basis/读取范围限制须有明确合同。保留A的PUBLIC入口与拒绝路径，不能简单删除守卫。测原生/合成basis分离、实际A/trace引用、未知usage、失败/未执行/NA、Q锚点及少量执行incomplete；不改评价器核心/CLI |
| 原`run_check.py`的新B包分支 | 单独核该次配置/授权、API分项许可与资源上限；离线测试仍拒绝网络。未来获准探针仅放行本渠道确认的两个POST路径，不扩大A、旧T0或通用网络权限 |
| 新`tests/test_4router_adapter.py`及上述现有公共入口测试的必要用例 | 手写PUBLIC原生封套和独立预期；sender/counter只在外部transport seam注入。逐行为TDD，首次已通过如实记录。只运行新增及直接受影响的Adapter/count/运行器/预算/读取回归；不重跑A全套、上游或旧T0/P3 |

实施仍须确认本补充合同、剩余配置和独立本地资源上限，再按原TDD及固定candidate的独立双轴流程进行。本步不生成实现工单的“完成”状态，也不再启动A审查。

## 最小联网验证提案：仅PUBLIC协议探针

当前执行许可generate/count/other均0。以下只是待确认的最小候选上限：**最多2次count、2次generate、other=0、并发1、重试0**；费用硬额、输出cap、超时及响应大小仍待填写。不请求models接口，不故意制造付费失败，不读取真实开发/测试账户或评价参考，不执行推荐/评分。

前置条件：明确目标令牌分组和gpt-6-luna可用性；取得该渠道完整count端点/字段覆盖及收费承诺；实际费率、最坏费用上界、探针预算和请求参数齐备；离线合同测试通过；另行确认仅PUBLIC探针的config摘要/操作ID/有效期/次数与费用许可。然后才按批准的本地凭据引用取Key，Key不写入配置或审计。

| 顺序 | 请求与验收 | 立即停止条件 |
| --- | --- | --- |
| 1 | 对包含短PUBLIC历史、一个现有函数工具Schema和既有角色Schema的完整准备输入做count；封存计数正文及回执 | 不支持/字段拒绝、未知费用、坏回执、未决发送；**不继续生成** |
| 2 | 同一准备正文做一次Responses生成，要求调用一个既有允许的函数，如read_evidence；仅允许PUBLIC引用，宿主用手写PUBLIC结果应答，不开真实证据会话 | model/服务层错配、非预期工具/多调用、坏参数、缺usage、count与原生输入usage不符、拒答/截断、身份/网络错误；不自动重试 |
| 3 | 将真实返回的function_call/call_id和PUBLIC工具结果（以及必要协议续传项）加入完整历史后再prepare/count | 旧回执被复用、完整输入无法计数或任一未知项；不继续生成 |
| 4 | 第二次生成返回该角色的严格封闭JSON；本地校验、保存usage/各类ID/trace，关闭根级与包级结算 | 非JSON/额外字段、工具结果配对错误、计数漂移、未知用量/费用或超额；保留占用停止 |

两次生成各比较自己的count回执和原生input_tokens；cached/reasoning/cache_write缺失不能补0，计费所需信息缺失则停止。第一次若未产生所需工具调用，探针记录未验证，不为凑通过追加请求。错误路径主要由离线夹具覆盖。探针通过仅证明这份PUBLIC输入下的协议闭环；不是开发预实验，更不解锁正式100用户。之后仍按已冻结1人8任务开发清单分阶段申请试跑，正式执行另签绑定原冻结计划的授权。

## 真实阻塞项与用户下一步提供内容

1. **令牌分组及可用性**：分组准确名称、选择/绑定方式、该组允许第三方Responses和精确gpt-6-luna的非秘密说明；不要提供Key。
2. **实际计费依据**：币种/单位、分组倍率是否已含、普通/缓存读取/缓存写入/输出及推理包含关系、长上下文/服务层附加规则、count和失败收费，生效时间及非秘密价目依据。继续为null，不用旧截图或上游价替代。
3. **试跑预算与参数**：PUBLIC探针的generate/count/other次数和费用硬额、每次输出cap、根级limits/final_reserve、超时/总截止、重试/并发上限；推理参数和service_tier须显式确认。B实现的本地时间/写入/内存上限也尚未授权，不继承A余额。
4. **供应商能力证据**：完整输入count的准确端点、等价字段覆盖和费用说明；函数工具/strict Schema/usage及ID契约若有请提供文档或非秘密支持说明。若仅能给实测许可，也不能先绕过可靠计数发生成请求。

上述信息齐备后，下一操作是确认本补充合同并实施离线TDD，固定候选双轴审查；随后单独确认PUBLIC探针预算/执行。当前仅渠道/base_url/模型/目标范围已确认，不能把配置草案或旧A验收当作真实模型、开发试跑或100用户实验的放行记录。

本步仅原生静态读取、公开资料研究、JSON语法/一致性及文件原字节检查，不运行项目代码或测试。文档成本以60秒、1MiB保守上界独立计入原离线账，不称实测，不取用A包余额；不授予B实现或联网预算。原A归档保持不变，原离线账只追加、T0账不动；核对与本次资源记录见verification.json。
