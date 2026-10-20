# 手动入口与最小PUBLIC准备验收

2026-10-20。验收仅限本轮离线准备；不表示4Router真实接通、开发预实验或正式实验完成。

实现候选：`f2f00f46ba62788521b6882bd45cd998baa9bd85`；审查基线：`ee58d44244b7f86f958ecf8f9e92b61dc7704b1e`。后者仅归档上轮既有B草案。继承任务14的A阶段验收，不重跑A或上游验收。

## 本轮结果

- 本地`.secrets/4router.json`以CreateNew创建api_key空占位，供用户在第2行手动填写；未覆盖旧文件，未读取、输出、摘要或哈希实际凭据。公开示例为空。`git check-ignore -v -- .secrets/4router.json`命中.gitignore:11的`/.secrets/`；`git ls-files -- .secrets/4router.json`为空。
- `check`仅检查本地填写状态/结构与既有公开固定模型地址，打印两个布尔值；不联网，不证明服务端认证。测试使用PUBLIC凭据夹具，不执行对实际凭据的检查。
- `prepare`纯离线输出PUBLIC虚构工具与strict JSON提案。夹具往返始终标fixture、真实请求0、费用null；错误停止且无重试。
- `probe`保留后续入口，当前无真实sender，在读取凭据前返回contract_confirmation_required。未读取Key，生成/计数/其他API均0；未运行真实开发或测试账户的推荐、评分或统计。
- 公开配置继续读取原B的config.draft.json；分组、费率、API预算与费用仍未知。最多2次生成、0次计数/其他API、并发1、重试0、每次输出提案256 token只是待确认的PUBLIC探针边界，不构成费用硬额或执行授权。

未来启用只需先确认两项必要差异：独立PUBLIC探针免除可靠完整输入计数前置（count=0）；明确接受未知费用并批准上述请求边界。之后补受控sender，才能人工执行。正式实验的计数、价格和预算合同不变。Key填写不等于上述确认。

## 必要验证与边界

仅运行tests/test_fourrouter_probe.py：10项通过，最终unittest 0.044秒；4组真实RED→GREEN，6项首次通过如实记录，见tdd.md。项目Python显式使用Thesis Conda，测试审计钩子拒绝socket及data/research/manuscript/.secrets读取。无新依赖。原Windows Job限制继续生效。

Standards/Spec对同一BASE...candidate均0项发现，见review.md。收尾静态diff确认新模块、测试、忽略规则、公开示例和既有B配置未偏离已审查候选。未修改旧Adapter/count/provider/运行器/评价器，未修改冻结数据或计划；不重复冻结数据验收。

源码SHA256与最终测试启动账一致：

- fourrouter_probe.py：`a566cad2a3e5bf211c8bea64a0646039eaabae3cadec6d905b6425542ec38750`
- tests/test_fourrouter_probe.py：`e40f4d66f2dbfba583e0f75b4e36a37f3a5bc0a1996d588fd78269221c56fef1`

精确模型账户权限、Responses工具/Schema兼容性、原生usage/请求ID、可靠完整输入计数均未实测；未知reasoning续传或额外输出停止，不扩展框架。

## 资源结算

原离线账仅追加manual4router_标签，T0账不动。继承累计1137.4871598001369秒；本轮记账81.1218187秒，累计1218.6089785001368/1800秒，同时低于本轮300秒自限。其中原生文件/Git/收尾等60秒为保守上界，非实测；其余为9次守护/Conda启动及两项独立审查的工具墙钟。无余额转授或新API授权。

本轮写入保守计费8,398,110字节：8MiB原生写入上界（含收尾，非实测）加9次守护/子进程write-transfer共9,502字节；低于本轮16MiB自限。守护子树峰值commit 13,586,432字节，守护预留64MiB，4GiB限制生效；原生进程全局峰值未测，不冒称全局实测。详见resource-closeout.json和原资源账。
