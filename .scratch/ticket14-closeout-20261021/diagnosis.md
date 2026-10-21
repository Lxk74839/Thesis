# 接入诊断（真实对照，非试点结果）

3次生成全部通过生产prepare→冻结reserve→invoke→既有HTTP sender，串行、HTTP120秒、无重试/count/其他API。每次发送前持久记账。诊断不会执行真实取证工具，也不构成完整S。

| 输入与差异 | HTTP/解析 | 产物run |
|---|---|---|
| 短PUBLIC，生产四工具，工具Schema含uniqueItems，严格文本JSON | 408；同A7的流提前断开错误 | PUBLIC-T14-diag-short_tools-1792571069048 |
| 同一短PUBLIC，四工具及strict保持，只移除工具Schema的uniqueItems | 200；生产工具校验通过 | PUBLIC-T14-diag-short_tools_supported-1792571187702 |
| A7已保存的完整首acquire逻辑输入，保留1493候选，同样移除工具Schema的uniqueItems | 200；acquire_batch有效；实际POST607196字节 | T14-D1-V00-S-DIAG-1792571209297 |

证据在P1共享根下各run/result.json，Job资源在T14-DEVELOPMENT-CLOSEOUT-20261021下各同名控制目录。完整输入不是PUBLIC数据，未标成fixture。未恢复或声称重放A5失去的正文，也未恢复A7未封存的推理密文。A7失败逻辑请求没有protocol_ref，因此本次完整输入对照不需要伪造原生上下文。

结论：该工具Schema关键字是可重复观察的触发因素；输入规模本身不足以解释短输入也出现408。完整输入在相同修正下通过，支持将此必要映射用于本轮生产试点。渠道内部把Schema问题表现为流断开408的具体原因未知。没有禁用strict工具、文本Schema或本地去重/冻结条款校验。无须消耗其余3次初始诊断额度。

协议依据：
- [4Router手动配置](https://docs.4router.net/guides/manual-config/)及[Codex Windows](https://docs.4router.net/guides/codex-windows/)公开指定Responses和既定base_url；未公开逐关键字兼容性。
- [OpenAI函数调用](https://developers.openai.com/api/docs/guides/function-calling)：strict工具要求封闭对象及所有属性required。
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)：支持JSON Schema子集，数组约束列出minItems/maxItems，没有列出uniqueItems。公开资料不能单独证明4Router内部实现；上面的实际对照提供本渠道证据。

版本：4Router mapper 0.3.0，本轮配置启用wire_schema_subset；本地工具Schema仍含原约束、原始逻辑请求不被改写。composer 0.4.0将完整1493项base score以独立映射保留，仅对当前/G中需要引用的项重复长citation；全部batch映射及必要历史保留。真实非执行预检请求约179KiB，未缩小C或召回。

预算分配：单run先给24次上限（始终受本轮160次总账约束），普通8192、最终1500、预留最终1次及145秒。Q1/Q2基于既有批处理上限统一冻结同一base排序前缀32项的取证预算，不按标签挑选对象，仍暴露完整1493候选；沿用既有fixed_prefix机制、融合系数和同锚点三组件，不改变评分规则。

针对性离线验证：新增6项（含S/M子例）及直接受影响解析、HTTP诊断、冻结预检/截止窗口回归共43项通过，11.332秒。未重跑A或上游全套。旧PUBLIC测试产生的可变fixture诊断文件恢复原字节，真实旧尝试不改写。

首次审查cf512ca发现：旧装配成员检查仅对R/S免读私有评价行，新M预检曾实际走该读取分支。值未进入安全输入、未输出或用于选择对象；没有M生成请求。这是本轮前置隔离缺陷，不能声称此前预检评价读取为0。修复为精确冻结pilot_id、tasks文件SHA及安全D1成员证明；不扩大目录准入。运行准备与非执行预检现在也处于禁读守护内。公共io.open禁读回归先在旧路径RED，再GREEN，七个完整装配/预检均不读Key或评价行。

另按Spec审查为父进程stdout/回执/worker-error保留2MiB共享空间，并从子run存储上限同样预留；父启动先检查磁盘占用，接近1GiB时不创建控制目录或启动worker。新增外部文件系统虚拟占用回归通过（首次运行GREEN，未虚构RED）。修复后新增及直接受影响冻结/截止窗口20项通过，25.178秒。

## 首次S工程run后的定向修正

dc214d3两轴PASS后执行T14-D1-V00-S-1792572853477。4次生成、45.9297621秒，取证请求HTTP200且合法acquire_batch，取得/核验1项后以batch_plan_exhausted终止，无publication。实际模型计划将max_list_pages与max_read_batches均置1；旧提示未明确本轮批处理分配上限。保留此失败，不改判，不原样重发。

composer0.5.0将两项资源计划明确为32并写入工具Schema枚举；它们是上限，仍按原取证完成/停止规则执行，不要求凑满。新增生产解析回归以虚构最小参数复现1/1计划未受Schema约束的问题，RED→GREEN；validate_call在存在完整工具Schema时复用closed_schema/matches执行校验，只有历史消息结构检查所用的name-only表继续执行原结构规则。没有修改推荐排序、工具实现或已冻结条款。17项新/直接受影响的解析、完整PUBLIC S/M及原生续接测试通过，6.793秒。下一run必须使用受审新候选；不增加PUBLIC调用。

## S业务输出合同接线（保留失败）
run T14-D1-V00-S-1792578102598：8次生成，A=10/G=10，画像已通过，failed_protocol/invalid_model_issue，无publication。离线从已封存响应核对：草稿kind使用inspection/retail_status/score等旧Schema允许而发布规则不接受的别名；5个问题单source_receipts均不在实际取证回执表，3个pointer与候选位置错配。此次不改写原回答。
composer0.7.0将草稿wire引用改为短ID，目录只来自实际取得A及安全基础分，原响应与派生完整citation草稿分别留存raw/derived/catalog/A摘要；旧domain publication与最终门禁逐字保留。Schema/提示采用既有发布kind/text合同，核验Schema限制实际draft/候选/pointer/取证回执，位置配对仍由原运行器校验。完整PUBLIC合成S/M回归及原生reasoning续接通过。未复制真实审计作fixture。
新增引用解析接口先RED（缺实现）再GREEN；核验字段约束回归发现共享Schema对象污染并RED→GREEN修复。受影响28项通过，再验证13项通过。

run T14-D1-V00-S-1792583847292：9次生成，A10/G10，画像及模型核验通过；程序报20条citation_does_not_support_claim，随后修订复用draft_id，failed_protocol/invalid_revision_binding。原响应与失败不改判。
实际已取得依赖共15个引用；模型仅选4/3个局部引用，闭包不完整。citation-control.json是明确标注非真实模型回答的内存反事实控制：用同一实际A的完整已接受闭包检查原发布规则，20条问题→0；API0，无publication。采用一次显式选择的verified_claim_bundle（member_ids均实际已取得引用），不补证、不从参考补引用；原始短ID选择与展开草稿分存。修订ID绑定本消息唯一ID及旧parent。PUBLIC引用束解析RED→GREEN、完整S/M及定向21项通过。

run T14-D1-V00-S-1792584535014：10次生成，A10/G10，原程序草稿问题0；核验HTTP200在旧65536字节接收阈值被截断（response_body_limit），失败usage未知。正文未保存，不能判断其内容或推理项。此本轮统一授权未单列响应体上限，按单run128MiB/共享1GiB/内存4GiB以内显式配置接收1MiB，旧64KiB默认不动；HTTP120秒/输出8192等不改。超过新界限继续停止，不跳过解析。大PUBLIC合成opaque封装经真实HTTP读取函数及生产normalize验证；超界具体错误码RED→GREEN。含评价目录隔离修复16项定向测试通过。

run T14-D1-V00-S-1792585222115：5次生成，dispatch通过；模型选择candidate_page后自行done，无真实batch，A/G/核验均0，failed_protocol/missing_batch_acquisition。新mapper0.4.0只对本轮acquire合同固定首请求tool_choice=acquire_batch，实际batch回执返回后tool_choice=none；正常化同时拒绝不遵守选择的响应。保留四工具定义及原批处理/发布规则，参数与既有dispatch固定机器字段对齐，完成字段仅绑定实际工具结果。PUBLIC S/M生产贯通tool_choice对照RED→GREEN。
Q准备：同一前缀32及全C不变，仅分4项一组完成全部商品画像；PUBLIC5项边界从单组5项RED→4+1两组GREEN，最终画像集合与实际核验集合相等、同锚点三组件均通过。普通S/M不分块。为本轮离线写入、测试、Git及归档预留保守512MiB（非实测），仍从新增2GiB内扣除，旧账不冲销。
定向组合29项有28项通过、1项因前一模块永久审计钩子禁止PUBLIC评价目录创建而失败；评价模块单独4项全部通过，未更改生产守护来绕过。其余25项实际通过沿用。

S T14-D1-V00-S-1792585830710真实released，9次，A10/G10/推荐10。只读IO初次严格拒绝settlement_binding_mismatch：旧native预算operation含工具原文，而audit按既有规则转哈希。完整PUBLIC S/M/Q产物关联复现RED后，共用原audit_reference_projection做哈希等价核对（不忽略字段）；native后续intent仅存request/prepared/wire等身份并链接单份trace，消除重复预算正文，不变更请求或推荐业务。5项直接回归GREEN。原真实S只读复验gate/publication均true，1457825输入、7622输出Token、cost=null、9项费用未知；不改写或重跑S。
