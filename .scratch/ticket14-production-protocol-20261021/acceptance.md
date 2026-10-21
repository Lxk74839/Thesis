# 任务14：生产协议修复及独立PUBLIC小输入联调

受审代码：BASE ca0bf3f，candidate e5ea9edfa1932a555a58a9c11a586d3216bbacdf（65f5d91及引用缺失修复e5ea9ed）。本记录只验收本轮增量，不表示完整S或任务14完成。

## 具体修改与依据

`provider_fourrouter.py`按当前Responses对象接纳reasoning必需id/type/summary，及可选content、encrypted_content、status、非空summary；每个已知结构仍校验。业务角色JSON、工具参数/调用ID和发布协议保持原严格校验，未知output类型继续拒绝。诊断保留已知字段存在性、类型、长度及具体stage/code/位置，协议ID可记录，推理/摘要正文、密文原值、未知字段名及Key/Authorization不归档。

`model_adapter.py`以仅在内存的run/session绑定表保留原始协议项目；逻辑消息只带protocol_ref。`provider_openai.py`的既有mapper按原顺序续接native output，再附工具结果，store=false及include reasoning.encrypted_content；默认调用方行为不变。缺失引用、跨session、篡改业务消息拒绝。`p1_engineering.py`复用同一上下文表，`recommendation_runner.py`将prepare审计改为身份/字节/哈希，避免含密文的wire/count副本落盘；不改S方法、工具或发布规则。

协议依据：[官方reasoning指南](https://developers.openai.com/api/docs/guides/reasoning)、[官方工具续接示例](https://developers.openai.com/cookbook/examples/responses_api/reasoning_items)、[Responses对象参考](https://developers.openai.com/api/reference/resources/responses/methods/create)。store=false时需原样续接reasoning/function_call/tool output；加密值按不透明协议数据处理。OpenAI协议资料不证明4Router的所有能力，也不证明费率或计数接口。

## 离线与审查

见[tdd.md](tdd.md)及[review.md](review.md)：20项不同定向测试通过；审查发现缺引用旁路后先RED，局部修复并重跑6项生产协议测试GREEN。最终同候选Standards PASS、Spec PASS。合成PUBLIC不是旧HTTP响应回放。测试未读实际Key、未联网；未重跑上游、A阶段或完整S。入口只是虚构数据经真实ModelAdapter.prepare→生产normalize→原工具校验→下一prepare，不使用旧PUBLIC专用解析器。

## 一次独立PUBLIC实际执行

run_id `PUBLIC-PRODUCTION-PROTOCOL-20261021`；独立authorization `PUBLIC-PRODUCTION-ONCE-20261021`。固定4Router/https://4router.net/v1/gpt-6-luna。实际发送2/2次，HTTP均200，模型均gpt-6-luna；count=0、other=0、并发1、自动重试/重定向/回退=0。实际POST为1295、1693字节（每次≤16KiB）；输出参数1024，HTTP上限120秒，总独立Job实际5.970152秒（≤300秒）。原S尝试和余额未复活。

| 请求 | 实际output类型 | 生产解析 | 输入/输出Token | reasoning Token | 请求ID |
|---|---|---|---|---|---|
| 1 | function_call | list_evidence(cursor=null)校验通过 | 168/19 | 0 | null |
| 2 | message | 严格JSON通过，draft_id=PUBLIC-DRAFT-7 | 219/28 | 0 | null |

第一轮原始function_call项目及其ID/status原样进入第二次请求，固定PUBLIC工具结果回填成功。两次usage_diagnostic.state均accepted；原生可接受计数合计输入387、输出47，reasoning为输出子量不重复累加。兼容字段native_usage仍为null，不把它伪造为完整原始usage归档；以生产usage_diagnostic的已知字段为证据，未保存完整响应。额外usage字段原值和兼容抽取为null的具体触发字段未知。本轮不为此追加调用或扩大修复。价格/费用为null，整体Token/费用计量仍unknown/incomplete。

**真实响应没有reasoning输出项，也没有encrypted_content。** reasoning_covered=false、reasoning_validated=false、encrypted_context_present/replayed=false；合法可选reasoning及密文续接仅由合成fixture覆盖，不能宣称真实覆盖。当前真实结果证明生产小输入工具往返及严格JSON通过，不证明1493候选下完整S成功。

原始小型脱敏证据：`data/recommendation-runtime-audit/ticket14-development/p1/PUBLIC-PRODUCTION-PROTOCOL-20261021/result.json`。控制回执、独立claim、stdout和Job资源在本目录PUBLIC/；response_id已记录，request_id缺失保留null。无真实用户/评论/评价标签读取，无内部推理正文、密文或凭据归档。

## 恢复完整S的条件

1. 本轮2次PUBLIC许可已用完；旧S两次尝试均已消耗，旧余额不能自行变成第三次许可。需为完整D1/V00/S明确新的独立尝试授权/ID/输出目录及累计调用、执行、输出和存储边界；原历史账和失败证据保留。
2. 仅在新许可明确计数/费率/缺usage豁免范围后使用工程模式；严格模式的完整输入计数、费率及预算要求仍有效，未知不得填0。本轮未验证4Router计数接口或费率。
3. 复用既有完整1493候选及来源隔离准入，针对新候选/授权核对发送前控制链、冻结预留窗口、HTTP/根deadline、最终输出预留、正文/响应及共享64MiB存储余额。本轮没有重新装载真实D1数据或执行完整S。
4. 若完整S真实响应出现reasoning，必须按现生产严格校验并保存结构诊断；目前真实reasoning/加密续接仍未覆盖，不能预先宣称已解决所有渠道差异。
5. 完整S须实际A/G、原发布协议（含协议允许空结果）、审计和预算闭合后才可验收；后续六个M任务、异常场景、Q1/Q2与评价衔接均未执行，继续按既有冻结清单分别授权。任务14保持未完成。

资源结算见[resources.json](resources.json)。继承原账，不冲销历史超限。preservation.json确认原账前缀及T0不变；正式冻结数据、独立参考、评价器核心和论文未修改。
