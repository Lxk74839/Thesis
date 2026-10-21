# 官方协议依据与本地选择政策

核对日期2026-10-21。这里只查询公开文档，未请求4Router或OpenAI生成/计数服务。官方OpenAI协议不能证明4Router每次实际返回均符合该协议。

- [Responses API参考](https://developers.openai.com/api/reference/resources/responses/methods/create)：output是异构输出数组，message.content为有序内容项；工具调用arguments为JSON字符串，call_id关联结果。phase可为commentary、final_answer或null。完整参考抓取超过工具内容限制，相关phase语义另以下面已实际读取的指南核实。
- [官方部署指南：assistant phase](https://developers.openai.com/api/docs/guides/deployment-checklist#set-up-the-assistant-phase-parameter)：commentary是进度/工具前说明，final_answer为完成回答；后续请求须保留原phase。这支持将两类消息分开解释，不能从字段长度反推值。
- [文本指南](https://developers.openai.com/api/docs/guides/text)：SDK便利output_text会聚合文本。因此聚合文本本身并非普遍违反协议；错误在于本地将不同phase消息无条件合并并当作单一严格角色JSON。指南未承诺跨message拼接结果是一个JSON文档。
- [函数调用指南](https://developers.openai.com/api/docs/guides/function-calling)：按call_id回填结果，reasoning模型的工具轮次还须回传reasoning项。
- [会话状态指南](https://developers.openai.com/api/docs/guides/conversation-state)：store=false手动管理上下文时，追加原response.output，包括加密reasoning项。本包继承既有protocol_ref机制，保留全部项及顺序，诊断不复制这些敏感字段。

本地单角色合同据此采用保守政策：只解析唯一非commentary业务message，message内的output_text按content顺序合并。一个final_answer加commentary可解析；多个final_answer、多个无phase项或final_answer与无phase项混杂均拒绝歧义。工具+commentary合法；工具+业务JSON继续拒绝。无phase的唯一message兼容已验收返回；role/status存在时严格校验，不扩大到协议之外的output类型。这里的唯一性及不混合规则是应用合同，并非声称官方API禁止多message。

已证实的合成反馈：commentary文字+合法final JSON被旧生产解析器拼接后拒绝；同message分块原已支持；坏JSON旧已拒绝；重复key旧解析会覆盖，新增严格拒绝。A5只留下两个message形状和json_decode位置，未保留正文及实际phase，不能据此确认A5就是该合成模式。
