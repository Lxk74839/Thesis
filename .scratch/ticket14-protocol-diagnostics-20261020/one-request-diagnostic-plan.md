# 最多一次首请求诊断方案（等待最终授权，本轮不发送）

需要确认的是新响应的具体协议分支。旧响应原文、completion status及output项类型未归档，不能恢复；reasoning_tokens=157不证明存在reasoning输出项。PUBLIC手写fixture仅证明新诊断行为，不是旧HTTP回放。新响应也可能与旧响应不同。

授权后仅重新装配D1/V00/S首请求，复用安全装配、完整1493候选、既有S首角色上下文/工具/strict角色Schema及Responses mapper。保留冻结计划9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088身份，不缩减输入，不运行取证工具、第二请求、完整S推荐或publication。使用新诊断authorization/control/run，不复用已消耗许可。

固定4Router / https://4router.net/v1 / gpt-6-luna。旧首请求实际POST602,539字节；新ID和输入指纹会令新字节数略有变化，须离线重算实际序列化字节及SHA，≤2MiB才允许发送，超限停止不裁切。max_output_tokens=8192，reasoning.effort=none。最多1次Responses POST，count/other=0，并发1、重试0、无重定向/回退。单次HTTP≤30秒，网络阶段≤30秒，留15秒保存脱敏结果，响应≤64KiB。产物上限1MiB；独立目录并计入共享P1根64MiB（含旧目录），不删除旧证据。单独确认免发送前精确计数、费用未知且无人民币硬上限；费率/费用仍null。

拟保存白名单：task/plan/run/prepared ID、输入/工具/角色Schema/实际POST哈希与字节数、配置输出上限；HTTP状态、返回模型及脱敏request/response ID；completion状态枚举；逐output索引及已知type类别（未知字符串仅记unknown）、content类型与必要字段存在标志；tool校验结果和位置（不存参数值）；JSON成功标志或字符position/line/column；strict角色Schema成功标志；稳定stage/code及deadline诊断；已验证usage数值、缺失/null/拒绝状态，费用null；实际发送计数/时限/存储结算。

不保存Key、Authorization、原异常文案、请求/响应全文、评论正文、text内容、tool参数或工具结果原文；不忽略未知输出项，不关闭strict Schema，不从独立参考补证。首响应后即结束；错误/超时/未知发送也停止，不能补发。该方案未产生执行授权、凭据读取或API请求，本轮不创建发送入口。
