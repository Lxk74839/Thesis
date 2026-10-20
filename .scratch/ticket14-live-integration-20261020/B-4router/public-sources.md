# B 阶段 4Router 公开资料核查

核查日期：2026-10-20（Asia/Shanghai）。状态：仅公开静态资料研究；所有账户、模型和 API 实测均未进行。

## 范围与固定条件

- channel：`4Router`；base_url：`https://4router.net/v1`；精确 model_id：`gpt-6-luna`。后两项中的地址有公开教程依据，精确模型为用户指定，不能由旧教程示例替换。[手动配置](https://docs.4router.net/guides/manual-config/)
- `100 用户、18 全场景、单轮`仅为目标范围，不是执行授权。
- token 分组、实际费率、预算均保持 `null`；没有查询账户、读取凭据或取得实际报价。分组页面要求以控制台实时信息确定模型与倍率，公开分组示例不能确定本账户权限。[模型分组](https://docs.4router.net/guides/model-groups/)
- 本记录未发起任何生成、计数、models 或其他 API 请求；未读取 API Key、环境凭据或登录页面；未运行项目 Python、测试、推荐、评价或统计；未写资源账。

## 来源范围与身份边界

主站 [4router.net](https://4router.net/) 的本轮静态打开结果仅为启用 JavaScript 的提示，未取得主站到文档站的可读外链。`docs.4router.net` 为同注册域的文档子域，其 [文档首页](https://docs.4router.net/) 自称 4Router Docs，并明确链接主站。因此，本轮已核到“文档→主站”，没有伪称核到了反向链接或完整身份认证链；下文作为该品牌文档子域的声明记录。

搜索曾返回同名 `.cn`、其他 Router 品牌及第三方比价页面，均未作为能力、模型或价格证据。没有采用 OpenAI 文档来推定 4Router 已支持某项能力。

## 能力结论

下表“待验证”表示在本轮限定的公开资料中没有取得足够契约，不能解释为“不支持”。“文档声明”也不等于本账户、精确模型实测通过。

| 核查项 | 文档声明或当前证据 | 对 `gpt-6-luna` 的状态 |
| --- | --- | --- |
| Responses 接入 | Codex 概览明确称客户端采用 Responses API，并给出目标 Base URL 和 `wire_api = "responses"`。这是客户端接入指导；本轮没有找到逐字段的 `POST /v1/responses` HTTP 参考契约。[Codex 概览](https://docs.4router.net/guides/codex/) | 待验证：文档可以支撑选择 Responses 接入方向，不能证明精确模型和账户实际可用。 |
| 函数工具调用与工具结果回传 | Windows 教程称已适配 Codex 的内置搜索、图像工具等链路，但未在所读页面提供自定义函数工具参数、调用 ID 与结果关联、工具结果再次提交的完整契约。内置工具声明不足以验收项目函数工具闭环。[Codex Windows](https://docs.4router.net/guides/codex-windows/) | 待验证：函数调用产生、参数解析、结果回传与最终回答均无实测。 |
| 严格 JSON Schema 结构化输出 | 所读文档首页及接入教程未提供 `json_schema`、`strict`、Schema 支持子集或拒绝/截断处理契约；限定域搜索也未检得直接说明。[文档首页](https://docs.4router.net/)、[Codex 概览](https://docs.4router.net/guides/codex/) | 待验证：不能用普通 JSON 文本或客户端自行校验代替服务端严格结构化输出能力。 |
| usage 的 input/output/cached/reasoning | 所读接入资料没有完整 usage 响应样例、缓存与推理 token 字段映射或计费包含关系。本轮没有取得足以证明四类用量可提取且可对账的依据。[Codex 概览](https://docs.4router.net/guides/codex/)、[模型分组](https://docs.4router.net/guides/model-groups/) | 待验证；不能把缺失字段填 0，也不能据此推算实际费用。 |
| request ID 与错误 | FAQ 举出了 `401` / `invalid_api_key`、`model_not_found`，并提醒模型范围依赖账户；没有公开完整错误对象、HTTP 状态矩阵、request ID 响应头/响应体契约或重试语义。[手动配置 FAQ](https://docs.4router.net/guides/manual-config/) | 仅错误示例有文档依据；请求标识、错误映射和失败记录仍待验证。 |
| 完整输入发送前 count | 本轮未检得适用于 Responses 完整请求的发送前计数契约，尤其没有取得 `/responses/input_tokens` 的公开承诺。没有确定计数操作的认证、模型/分组适用性、字段覆盖、是否计费或精确程度。[文档导航](https://docs.4router.net/)、[Codex 概览](https://docs.4router.net/guides/codex/) | 关键阻塞，保持未知；任何计数接口均未请求。 |
| 精确模型及本账户可用性 | 所读教程示例不是 `gpt-6-luna`；概览标明示例基准为 2026-04-10。模型分组页要求按控制台实时显示确定模型与倍率。本轮未取得精确模型、当前令牌分组和本账户权限的公开证明。[Codex 概览](https://docs.4router.net/guides/codex/)、[模型分组](https://docs.4router.net/guides/model-groups/) | 待验证，model_id 仍固定为用户指定值，禁止静默回退。 |

## 完整输入计数的具体缺口

本节是项目验收所需的核验清单，不是 4Router 公开能力声明。对候选 `/responses/input_tokens`，至少还需确认：

1. 目标账户、令牌分组及精确 `gpt-6-luna` 是否允许该操作，路径是否确为受支持的公开计数操作。
2. 是否可接收与拟发送生成请求等价的完整输入，包括 instructions、当前和历史消息、检索/画像/追溯证据、自定义工具定义及参数 Schema、既有工具调用与工具结果、输出 JSON Schema；哪些字段不能计入或不能接收。
3. 是否能在生成请求之前返回可保存的计数、错误及请求标识，计数与最终 usage 的关系，是否产生计费，以及缓存/推理 token 如何处理。

当前没有取得上述承诺，所以 `count_endpoint_confirmed`、`count_coverage_confirmed`、`account_model_available` 均只能记录为未确认。不能用客户端估算、只计用户文本、只计部分消息、其他协议的计数端点或 OpenAI 的能力说明替代该缺口。此判断基于本轮所读 [文档导航](https://docs.4router.net/) 与 [Codex 接入说明](https://docs.4router.net/guides/codex/) 的覆盖范围，并受下述检索边界限制。

## 检索记录与局限

直接打开并阅读的主要页面：

- [主站静态首页](https://4router.net/)
- [文档首页与导航](https://docs.4router.net/)
- [手动配置与 FAQ](https://docs.4router.net/guides/manual-config/)
- [模型分组](https://docs.4router.net/guides/model-groups/)
- [Codex 概览](https://docs.4router.net/guides/codex/)
- [Codex Windows](https://docs.4router.net/guides/codex-windows/)

搜索还返回同站 VSCode、Mac、Linux、CC Switch 和 1M 上下文教程；没有下载其公开 models 文件，也没有运行其中的命令。最终定向检索限定 `4router.net` 和 `docs.4router.net`，分别检索下列四组词，搜索工具均返回无结果：

- `"responses/input_tokens" OR "count_tokens" OR "input_tokens"`
- `"function_call" OR "function_call_output" OR "函数调用"`
- `"json_schema" OR "strict" OR "structured outputs" OR "结构化输出"`
- `"gpt-6-luna" OR "cached_tokens" OR "reasoning_tokens" OR "x-request-id" OR "request_id"`

搜索未命中可能源于索引覆盖、文档更新或信息仅对账户开放，不能据此断言服务不支持。没有穷举未链接路径、猜测文档 URL 或探测 API。

## 对 B 阶段的影响

可将 `4Router`、指定 Base URL、指定精确模型及 Responses 接入方向写入方案，并把来源证据保留到方案附件。公开资料目前不足以将函数工具闭环、严格结构化输出、用量与请求标识、完整输入 count 或当前账户模型可用性标为已验收。特别是完整输入计数契约尚未取得，不能将目标范围当作可立即执行的批量任务。token 分组、实际费率、预算继续为 `null`；本记录不提出付费调用或实验执行授权。

工具计时：写入前共 5 次 `functions.exec` 外层返回的墙钟时间相加为约 13.0 秒（包含公开网页检索及一次技能读取）；其中原生命令报告的技能读取墙钟为 0.115826 秒。此处时间是工具研究耗时，不是模型或 API 实测延迟。文件写入和字节复核的原生命令时间由交付消息单独报告。
