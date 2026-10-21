# 生产Responses解析与独立PUBLIC两轮联调

BASE ca0bf3f；只修provider_fourrouter的reasoning/结构诊断及生产上下文续接所必需的mapper、ModelAdapter、S invoke和运行器审计接线。公共测试接口为实际ModelAdapter.prepare→provider.normalize（包含validate_call与角色Schema）→同一adapter的下一次prepare。合成PUBLIC fixture不是A1/A2响应回放；不加载开发账户/1493候选/真实评论或参考。

按当前官方协议，reasoning必需id/type/summary；可选content、encrypted_content（字符串或null）、status。summary/content的项分别为summary_text/reasoning_text且text字符串。接纳合法可选字段及非空summary，未知字段给具体结构拒绝，未知output类型仍拒绝；业务JSON和工具参数/调用ID保持严格。

store=false时将前一次的reasoning、function_call等output项目按原顺序续接，再附function_call_output。通过adapter内存中run/session绑定的协议项保留表解析引用；逻辑message只带引用，不存内部推理正文或encrypted_content原值。prepare的实际wire/count必须覆盖原样协议项；审计只保留prepared身份/字节/哈希及结构摘要，不能序列化含不透明值的wire。密文不解密、不打印。

诊断仅已知字段存在性、类型、长度/元素数量和拒绝条件/位置，不记录字段值或未知字段名、摘要/推理文本/加密值。HTTP、模型、usage缺失/null/拒绝及失败usage继续如实保存。上下文引用缺失、跨session、篡改业务message必须拒绝。

离线1200秒/累计4800，120秒收尾、128MiB/4GiB；继承账和超限，不计用户等待。新PUBLIC许可最多2生成，固定4Router/https://4router.net/v1/gpt-6-luna，真实prepare+normalize+工具校验，无专用探针parser；POST每次≤16KiB、输出1024、HTTP≤120秒、累计执行300秒含回收/保存，单并发零重试/重定向/回退，count/other=0。只首请求有效工具调用且本地固定PUBLIC结果验证后才发第二次；任一步失败停止。共享P1根64MiB含历史，费用null，缺用量不填0。

两次独立于旧S许可；本轮不运行完整S/M/异常/Q/正式100。离线/双轴/PUBLIC成功均不等于S或任务14完成；必须报告真实reasoning是否覆盖，没覆盖则unknown/未覆盖。后续完整S需另核对准入/存储/执行授权，旧两次S尝试不复活。

依据：[Responses reference](https://developers.openai.com/api/reference/resources/responses/methods/create)、[reasoning指南](https://developers.openai.com/api/docs/guides/reasoning)、[生产式工具续接示例](https://developers.openai.com/cookbook/examples/responses_api/reasoning_items)。参考文档HTML过大时使用官方Markdown/指南核对，未知4Router行为待真实联调，不从OpenAI文档推断渠道费率。
