# 本包规格：响应message选择与失败业务回放

BASE858409a；仅生产provider_fourrouter.normalize/ModelAdapter调用边界及必要测试、诊断。不新增真实API或A6/M/正式实验许可。画像、推荐、发布、数据及旧证据只读，旧A5正文无法恢复。

公共测试接口：生产normalize、ModelAdapter.prepare/invoke（PUBLIC transport）、已接受完整S PUBLIC离线流程。单命令最小复现：.scratch/ticket14-message-parsing-20261021/check.ps1 repro -m unittest tests.test_fourrouter_message_selection。所有响应手写合成，不能称A5回放。先RED，再依据protocol.md做最小修复。

同message文本按顺序合并；commentary是中间协议消息，不解释为业务JSON；必须恰有一个业务message（final_answer或唯一无phase兼容消息）。多业务/混合不明phase/未知type、损坏JSON、重复key、角色Schema及工具参数不合格均拒绝，不取最后项、不修补JSON。工具可伴commentary，不得同时返回业务JSON。完整native输出及顺序仅保留在已有续接内存中；不解密、不在诊断归档reasoning正文/密文。

失败回执/审计raw_response.business_output仅保存message/function_call白名单项、原始索引/phase/status、按原分块保存文本及UTF8 SHA256；capture canonical序列化≤96KiB。超限或凭据样式/实际Key回显时整份正文省略，明确不可回放，不截断冒充完整。未知或不支持结构明确不可完整回放。合法usage及原有失败/无重试规则保持，成功响应不增加正文诊断。新输出证据不能补写旧A5。

定向TDD、固定同候选Standards/Spec审查；复用其余验收。900秒包/120收尾、累计8700，继承7768.934749400534与历史超限；写128MiB/内存4GiB，P1共享128MiB保持，不实际执行。无依赖/真实Key/生成/count/other调用。
