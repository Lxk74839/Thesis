# A7及HTTP错误取证

BASE3a087b2。仅冻结D1/V00/S完整1493，许可S-COMPLETE-ONCE-20261021-A7，旧A1—A6及费用/计量未知状态保留。继承原解析、画像、续接、工具和发布规则。

公共测试接口为既有http_response/send_response/生产ModelAdapter及prepare_p1/RecommendationRun/控制账。HTTP408、非JSON、缺失ID、凭据回显、超时/连接/worker未知均用PUBLIC fixture；4项HTTP测试+4项A7（含1493非执行发送链及完整S9轮/失败3轮）+2原marker/worker回归，10项PASS。HTTP缺诊断先RED后GREEN；A7历史12调用新额度先RED后GREEN，其他已满足行为不制造RED。

每次HTTP保存UTC毫秒起止、单调耗时、真实HTTP状态；本地超时/连接异常/未知worker结果分类，未知发送不记0。错误仅code/type/message白名单（message≤512字符）、非JSON≤256字符片段，诊断≤4KiB；原始读取≤65537字节，超65536标截断/长度非精确，不解析成成功。缺失、过滤、省略明确标志，Key/认证头/内部推理不归档；复用既有标识过滤，错误仍停止，无默认工具数据。

A7本地12/91612，共享24/189916，历史12/98304不清零；普通8192、最终1500且保留1/1500/145秒。共享执行1800扣历史207.3560245，余额1592.6439755；根-20秒1572643ms、Job-10及回收5，HTTP120不延长，并发1/retry/count/other0。P1共享128MiB/run64MiB真实守护，包128MiB/4GiB。900秒离线新包/180收尾，累计10500，继承9461.94140040054和历史超限，真实执行单记。双轴同候选PASS后直接A7，无PUBLIC联网或A8；新错误保存并停止。
