# 接入诊断（真实对照，非试点结果）

3次生成全部通过生产prepare→冻结reserve→invoke→既有HTTP sender，串行、HTTP120秒、无重试/count/其他API。每次发送前持久记账。诊断不会执行真实取证工具，也不构成完整S。

| 输入与差异 | HTTP/解析 | 产物run |
|---|---|---|
| 短PUBLIC，生产四工具，工具Schema含uniqueItems，严格文本JSON | 408；同A7的流提前断开错误 | PUBLIC-T14-diag-short_tools-1792571069048 |
| 同一短PUBLIC，四工具及strict保持，只移除工具Schema的uniqueItems | 200；生产工具校验通过 | PUBLIC-T14-diag-short_tools_supported-1792571187702 |
| A7已保存的完整首acquire逻辑输入，保留1493候选，同样移除工具Schema的uniqueItems | 200；acquire_batch有效；实际POST607196字节 | T14-D1-V00-S-DIAG-1792571209297 |

证据在P1共享根下各run/result.json，Job资源在T14-DEVELOPMENT-CLOSEOUT-20261021下各同名控制目录。完整输入不是PUBLIC数据，未标成fixture。未恢复或声称重放A5失去的正文，也未恢复A7未封存的推理密文。A7失败逻辑请求没有protocol_ref，因此本次完整输入对照不需要伪造原生上下文。

结论：该工具Schema关键字是可重复观察的触发因素；输入规模本身不足以解释短输入也出现408。完整输入在相同修正下通过，支持将此必要映射用于本轮生产试点。渠道内部把Schema问题表现为流断开408的具体原因未知。没有禁用strict工具、文本Schema或本地去重/冻结条款校验。无须消耗其余3次初始诊断额度。

协议依据：
- [4Router手动配置](https://docs.4router.net/guides/manual-config/)及[Codex Windows](https://docs.4router.net/guides/codex-windows/)公开指定Responses和既定base_url；未公开逐关键字兼容性。
- [OpenAI函数调用](https://developers.openai.com/api/docs/guides/function-calling)：strict工具要求封闭对象及所有属性required。
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)：支持JSON Schema子集，数组约束列出minItems/maxItems，没有列出uniqueItems。公开资料不能单独证明4Router内部实现；上面的实际对照提供本渠道证据。

版本：4Router mapper 0.3.0，本轮配置启用wire_schema_subset；本地工具Schema仍含原约束、原始逻辑请求不被改写。composer 0.4.0将完整1493项base score以独立映射保留，仅对当前/G中需要引用的项重复长citation；全部batch映射及必要历史保留。真实非执行预检请求约179KiB，未缩小C或召回。

预算分配：单run先给24次上限（始终受本轮160次总账约束），普通8192、最终1500、预留最终1次及145秒。Q1/Q2基于既有批处理上限统一冻结同一base排序前缀32项的取证预算，不按标签挑选对象，仍暴露完整1493候选；沿用既有fixed_prefix机制、融合系数和同锚点三组件，不改变评分规则。

针对性离线验证：新增6项（含S/M子例）及直接受影响解析、HTTP诊断、冻结预检/截止窗口回归共43项通过，11.332秒。未重跑A或上游全套。旧PUBLIC测试产生的可变fixture诊断文件恢复原字节，真实旧尝试不改写。

首次审查cf512ca发现：旧装配成员检查仅对R/S免读私有评价行，新M预检曾实际走该读取分支。值未进入安全输入、未输出或用于选择对象；没有M生成请求。这是本轮前置隔离缺陷，不能声称此前预检评价读取为0。修复为精确冻结pilot_id、tasks文件SHA及安全D1成员证明；不扩大目录准入。运行准备与非执行预检现在也处于禁读守护内。公共io.open禁读回归先在旧路径RED，再GREEN，七个完整装配/预检均不读Key或评价行。

另按Spec审查为父进程stdout/回执/worker-error保留2MiB共享空间，并从子run存储上限同样预留；父启动先检查磁盘占用，接近1GiB时不创建控制目录或启动worker。新增外部文件系统虚拟占用回归通过（首次运行GREEN，未虚构RED）。修复后新增及直接受影响冻结/截止窗口20项通过，25.178秒。
