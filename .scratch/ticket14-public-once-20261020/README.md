# 一次PUBLIC探针

2026-10-20用户已明确确认一次联网许可，取代上一包“尚未确认”的状态；Key填写本身仍不授予其他执行许可。固定4Router、https://4router.net/v1、gpt-6-luna，计数/其他API=0，费用null。

本次仅在固定候选的独立审查通过后，由root通过既有Thesis Conda/Job守护运行`fourrouter_probe.py probe`一次。最多2次生成，单次max_output_tokens=256、reasoning.effort=none，单次30秒、总联网60秒；无重定向、重试或回退。

脱敏回执为本目录result.jsonl，首次独占创建即消耗这次启动许可。存在时CLI拒绝再次执行；无论成功、失败、超时或未知状态均不删除回执、不补跑。每次尝试前写入记录，未知发送数保留null；最终一行给出结果。只记录状态、模型、原生usage、请求ID和工具/JSON校验，不记请求或响应正文、Key或Authorization。

工具有效后才有第二次请求；未知输出形状、模型不符或Schema不符立即停止。本探针不能替代可靠完整输入计数或费用预算验收，不授权开发/正式100用户推荐、评价、统计。
