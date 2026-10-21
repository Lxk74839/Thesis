# 本轮定向TDD

所有手写响应均为合成PUBLIC协议fixture，不是A1/A2真实响应回放。测试仅使用Thesis环境及原Windows Job守护，不读取实际Key，不联网。

- `prodproto_reasoning_red`：合法可选reasoning字段被旧解析器以unsupported_output_type拒绝；修复后GREEN。
- `prodproto_continuation_red`：生产adapter缺少原生上下文续接；增加内存引用及原样映射后GREEN。
- `prodproto_final_targeted`：18项生产prepare/normalize/工具校验、协议诊断及直接受影响回归通过。
- `prodproto_mapper_regression`：2项共享mapper既有行为回归通过；共20项不同定向用例。其他新增拒绝条件首次已满足，如实记录GREEN。
- 审查发现删除protocol_ref可静默重建调用；`prodproto_missing_ref_red`复现prepared错误通过，修复后`prodproto_missing_ref_green`的6项生产协议测试全部通过（包含删引用、篡改、跨session及工具往返）。

测试前后均在原resource-ledger.jsonl追加余额与Job用量；未重跑A/上游全套、Windows worker全套或PUBLIC联网探针。固定候选见review.md；真实PUBLIC结果另存，不能以fixture代替。
