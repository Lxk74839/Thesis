# 本条8KiB PUBLIC探针结果

2026-10-20。本条独立PUBLIC协议验证通过；许可已消耗，不再发送请求。旧探针回执保留，未覆盖或作为本次结果使用。

BASE：83a5b38a8b057efdbecd2051f5d0f3e3b77f7d34；审查并执行的candidate：0d99eea5573dad2ee7e2641d911d58238f6b7927。执行前后源码未偏离该候选，收尾只归档。

- 先执行既有check，仅输出api_key_filled=true、local_config_valid=true，不联网、不输出实际凭据。
- 三组真实RED→GREEN；新增3项与直接受影响8项共11项通过，unittest 0.173秒。无A、上游或无关入口测试重跑，详见tdd.md。
- 同一BASE...candidate的独立Standards和Spec均0项发现，详见review.md。完成后才执行本条一次CLI探针。

| 请求 | HTTP | 返回模型 | 实际POST正文 | 协议验证 | 原生usage | HTTP请求ID |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 200 | gpt-6-luna | 945字节 | 唯一read_evidence调用及PUBLIC-REF-1参数有效 | null | null |
| 2 | 200 | gpt-6-luna | 1278字节 | 固定工具结果按call_id回传；严格封闭JSON通过 | null | null |

实际生成2次，count=0、其他API=0，并发1、重试0，无重定向/模型切换。两次请求均max_output_tokens=256、reasoning.effort=none。单次30秒及总联网60秒监督限制保留，实际联网5.039823秒。

8KiB限制按实际JSON序列化字节检查：派发、子进程与HTTPS边界复用同一编码，HTTP直接发送检查后的字节；超过8192字节在发送前拒绝。第一次工具校验通过后才有第二次派发。tool_call_valid、tool_result_sent、strict_json_valid均true，最终protocol_passed。

result.jsonl为6行、3,064字节的脱敏回执，包含response_id；没有Key、Authorization头或请求/响应正文。原生usage及HTTP请求ID未取得可封存值，保持null；不据此断言渠道绝不支持这些字段。费用、分组与费率仍未知，cost=null，不估算token、人民币金额或费用硬上限。

回执独占创建且存在即拒绝再次启动；没有删除、补跑或追加请求。本次仅使用既有PUBLIC虚构输入，未接真实推荐运行器，未读真实用户、评论、参考/评价标签，未改冻结数据或正式计划。生产代码只改探针与必要测试，无新依赖。通过只代表本次PUBLIC协议验证，不启动开发预实验或正式100用户实验；正式计数/预算合同不变。

## 资源

继承原离线累计1282.9015672001367秒；本条记账54.3667992/300秒，总累计1337.2683664001365/1800秒。原账仅追加router8k_标签，T0不动。30秒原生读写/Git/收尾为保守上界，非实测；其余为9次守护/Conda启动和两轴只读工具墙钟。

写入保守计费4,242,301/16,777,216字节，包含4MiB原生上界（非实测）及守护/子树write-transfer 47,997字节。子树峰值commit 29,667,328字节，另留64MiB守护预留，4GiB Job限制生效；原生全局峰值未测。所有Python经Thesis Conda运行，TEMP/TMP/缓存均在项目内，无依赖安装。详见resource-closeout.json与原账。
