# 手动配置入口与PUBLIC探针准备

Status: ready-for-agent
来源：2026-10-20最新用户确认；本轮收敛范围优先于旧B整包方案。

## 最小公共接口与验收

- `fourrouter_probe.py check`：复用既有公开配置，读本地凭据文件，只输出api_key_filled/local_config_valid；不输出Key、片段、长度、摘要、异常原文，不联网。空Key是合法占位；格式检查不证明Key在服务端有效。
- `fourrouter_probe.py prepare`：纯离线返回少量PUBLIC虚构输入的首个Responses工具请求及2次生成/0次计数的探针提案，不读凭据、不读真实用户/商品/评论/标签，不生成生产答案。
- `fourrouter_probe.py probe`：当前明确返回contract_confirmation_required、实际请求0，且在读取凭据之前拒绝；填写Key不授予权限，不提供绕过旗标。未来启用真实sender仍需单独确认。
- `run_fixture_probe(transport, *, public_path=...)`：外部transport夹具仅演练最多2次Responses往返：固定read_evidence(PUBLIC-REF-1)→手写PUBLIC-OK结果→strict封闭JSON。错误立即停止，无重试；始终标fixture、真实请求0、费用null。只验证本准备代码的协议处理，不宣称渠道能力已接通。
- `check_config(*, public_path=..., credential_path=...)`、`prepare_probe(*, public_path=...)`及`main(argv, *, public_path=..., credential_path=...)`为上述行为的可注入文件边界，测试不读实际凭据文件。

固定4Router、https://4router.net/v1、gpt-6-luna；正式目标仍是冻结100用户18场景repeat=1，只引用不修改。公开配置沿用旧B的config.draft.json，不复制旧价格/分组。新建`.secrets/4router.json`仅api_key空字符串，整个.secrets加入Git忽略；公开示例`config/4router.credentials.example.json`同样空Key。创建只在缺失时进行，不覆盖已存在的本地文件，不在验收/资源账中读取或摘要凭据内容。

## 尚需确认的最小合同差异（当前不启用）

1. 独立PUBLIC协议探针与正式实验分开，拟免除可靠完整输入计数前置，count请求上限0；不探测或修复未经证实的count端点，不能把探针替代正式计数验收。
2. 若未来在分组/费率未知时允许人工启动，须显式确认接受未知费用，并批准最多2次生成、0次其他API、并发1、重试0及单次输出上限提案256 token。当前仍为null/未授权；实际费用不得填0。该提案不构成正式实验的费用硬额保证。
3. 探针只用固定PUBLIC工具/Schema，测试Responses协议，不运行六角色推荐/取证/评价。未知reasoning续传或额外输出立即停止；不据探针结果改已冻结计划。

## 本轮文件与验证边界

只新增fourrouter_probe.py、tests/test_fourrouter_probe.py、空凭据/示例、本目录记录，并给.gitignore增加.secrets规则。旧运行器/Adapter/count/provider/评价器及数据不改。逐公共行为TDD；复用A验收，仅新增必要行为。固定本轮BASE...candidate后两个独立代理并行Standards/Spec审查；不读.secrets、不重验A、不扩大框架。

实现自限：命令累计300秒（留60秒收尾），新增写入上界16MiB（含4MiB收尾），Job进程树4GiB（含64MiB守护预留）；同时受原离线1800秒总额约束。此为本轮获准本地工作的自限，不转用A余额，也不授权B整包或任何API。原账仅追加，T0不动，新依赖0；所有项目代码显式使用Thesis Conda。
