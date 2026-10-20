# 一次PUBLIC协议探针结果

2026-10-20。结论：本次PUBLIC协议闭环通过；本次启动许可已消耗，不再发送请求。

BASE：64ebc5155683a2ba3116e4c54a029f068d9f5a02。已审查、已执行candidate：6a5a2bf803123a49880993d09bfbd9646df22431。后续只归档记录，不变更已执行源码。

## 执行与证据

1. 先通过现有Thesis环境check，只报告`{"api_key_filled":true,"local_config_valid":true}`，不输出Key或异常原文。该检查不联网。
2. 增量逐公共行为TDD：5组真实RED→GREEN，新增8项与直接受影响10项共18项通过，最终unittest 0.220秒；其他已满足行为如实记录首次通过。没有A或上游验收重跑，见tdd.md。
3. 独立Standards与Spec对同一精确BASE...candidate均0项发现，见review.md；通过后才执行一次CLI探针。执行前静态diff确认候选源码未变。
4. 探针通过Thesis Conda及原4GiB Windows Job守护执行，标签manual4router_027_authorized_PUBLIC_once；无新依赖。唯一真实HTTP发送由sender完成，生成2次、计数0、其他API 0，并发1、重试0，无重定向或模型回退。

| 请求 | HTTP | 返回模型 | 工具/输出校验 | 原生usage | HTTP x-request-id |
| --- | --- | --- | --- | --- | --- |
| 1 | 200 | gpt-6-luna | 唯一read_evidence函数调用、PUBLIC-REF-1参数有效 | null | null |
| 2 | 200 | gpt-6-luna | 工具结果按call_id回传；严格封闭JSON为PUBLIC-4ROUTER/PUBLIC-OK | null | null |

两次请求均使用max_output_tokens=256、reasoning.effort=none、stream=false、store=false。单次监督超时30秒、剩余总截止时间60秒；实际整个联网阶段6.566999秒。只有第一轮工具验证成功后才派发第二轮。结果为protocol_passed；tool_call_valid、tool_result_sent、strict_json_valid均true。

原生usage与HTTP请求ID没有取得可封存值，均保持null；response_id已按实际记录于result.jsonl。原始响应正文按规则未保存，不能仅据这份回执判断服务端绝不返回usage或请求ID。没有额外请求来获取它们，也不估算token或费用。

## 脱敏与停止边界

result.jsonl仅2,875字节、6行：独占创建、每次尝试前/收到响应后记录、最终摘要；不保存Key、Authorization、请求或响应正文。Key只从本地文件读入内存，经子进程stdin传递，不放命令行或环境。子进程单POST、不重试；超时则父进程终止，未知发送状态保留null并停止。回执存在即拒绝再次启动，不删除回执，不补发或恢复该次许可。

测试使用PUBLIC临时凭据与网络/进程边界夹具，不读取实际凭据；测试审计钩子拒绝socket及真实数据路径。真实执行仅使用既有PUBLIC虚构输入，没有用户、商品评论、参考标签或生产推荐答案。

费用、分组和费率继续未知，cost=null，无人民币费用硬上限。此结果仅证明这一次Responses函数调用与严格JSON往返；可靠完整输入计数、原生usage核算、费用预算与正式实验授权仍未完成。没有执行真实开发或100用户推荐、评价、统计，冻结计划/数据及旧模型Adapter/count/评价器未修改。

## 资源结算

原离线账只追加，T0不动。继承1218.6089785001368秒；本次新增64.2925887秒，累计1282.9015672001367/1800秒。其中新增原生30秒为保守上界（非实测）；其余含13次守护/Conda启动及独立审查。与上一手动入口包累计145.4144074/300秒自限，没有扩额或余额转授权。

本次原生写入4MiB保守上界（含收尾，非实测），子树/守护write-transfer 53,185字节；与上一包合计保守计费12,645,599/16,777,216字节。此次守护子树峰值commit 29,925,376字节，守护预留64MiB，4GiB限制生效；原生进程全局峰值未测。详见resource-closeout.json及原账。API实际调用数2仅在真实探针启动账记录一次，不将夹具回调计作真实请求。
