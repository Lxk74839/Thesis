# PUBLIC探针8KiB边界与本条独立授权

Status: claimed

BASE：83a5b38a8b057efdbecd2051f5d0f3e3b77f7d34。上一条授权已执行2次请求且回执保留；本条用户重新明确要求执行一次，按本条新增8KiB正文约束独立封存新回执，不删除或覆盖旧回执，不把旧成功当成本次结果。

本条只授权4Router / https://4router.net/v1 / gpt-6-luna的既有PUBLIC虚构协议：最多2次生成，count/其他API=0，并发1、重试0、无重定向/模型回退。每次256输出token、reasoning.effort=none，单次30秒、联网总60秒。有效函数调用后才能发送固定工具结果并校验严格JSON；错误、超时、模型或协议不符、发送状态未知均停止，不追加。

## 最小增量接口

- 复用check，先仅报告api_key_filled/local_config_valid；本条已执行且两者true。测试不读实际凭据。
- run_live_probe既有sender边界：第一或第二轮正文序列化后超过8192字节时，派发前拒绝；记录实际派发正文的字节数，不消耗该次HTTP尝试，不记录正文。共享请求与协议校验保持现状。
- send_response与http_response既有外部进程/HTTPS边界：同一JSON字节编码与上限检查，真实POST使用已检查的字节；8192可发送，8193拒绝，不能以字符数代替字节数。
- CLI probe默认回执指向本目录result.jsonl，独占创建后只允许本条一次启动，存在即拒绝。旧回执留在原目录，旧授权不复活。

仅改fourrouter_probe.py与必要测试，新增本次小型规格/审查/脱敏结果/资源归档。先逐行为TDD，固定同一candidate独立Standards/Spec，通过后执行一次。输出实际HTTP、次数、返回模型、工具/JSON、原生usage/两类ID；缺失和费用null，不输出Key或Authorization。不改推荐运行器、数据、正式冻结计划或A验收，不安装依赖。

本条本地自限300秒、16MiB、4GiB；继续继承原离线累计1282.9015672001367/1800秒，T0不动。原生读写/Git/收尾追加30秒、4MiB保守上界（非实测），守护/Conda启动/独立审查另外计入原账；不重置任何总额。
