# P1执行条件与一次授权草案（未授权）

本文件是唯一集中条件清单。当前只完成离线接线，API/真实开发推荐/评价/统计授权均0；两次PUBLIC探针的许可已消耗，不能用于P1。下列资源提案没有写成有效执行配置。

固定身份：pilot_id=6353afe1bf05e4eadd56216d64bb5d29181798e29c6edf9468f9d537e10c1af1；父plan_id=9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088；D1=015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e。只读引用冻结pilot，不重抽样、不回写正式计划。

| P1任务 | task_key | 生成硬上限提案 |
| --- | --- | --- |
| D1/V00/R | 7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874 | 0 |
| D1/V00/S | a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4 | 12，含final |
| D1/V00/M | 4fc09c3d2c7a0ad10bf5af864479975fc62c3d12c7b4f8b8f476094651a9694e | 12，含final |

PUBLIC的S/M九次调用仅是夹具结果，不承诺真实D1也九次。真实流程保留完整C、六角色/单智能体、分页/批取证、G推进与发布校验；到12次仍未完成则停止并记录incomplete，不截断C或补跑。

## 当前阻塞项：补齐后才具备启动条件

1. 独立P1执行授权：execution_authorized、authorization_id，严格绑定上述身份与三个任务。当前false/null，不能因Key已填写或配置文件存在而启动。
2. 可信完整输入计数：每个实际prepared请求都要覆盖messages、tools、strict schema和原生输入映射，回执绑定model/project/prepared_id/wire_sha256，basis必须verified_full_input。现有InputCounter的旧模型计数分支未接入4Router，没有已证实的4Router计数端点；CLI不伪造计数器，当前counter未绑定。PUBLIC计数/费用豁免不适用于P1。
3. 渠道费率和API预算：三类费率单位为microUSD/百万token，必须注明渠道/分组、证据和生效时间；api_budget_microusd应覆盖S/M两个RootBudget成本上限之和。不得套旧费率，也不得把未知费率填0。当前pricing、api_budget均null。
4. 模型能力/请求边界：确认gpt-6-luna的上下文上限；明确批准max_output_tokens和正文上限。当前context_token_limit、max_output_tokens、max_request_bytes均null。完整C或历史导致请求超限时拒绝发送，不裁切输入。本轮只为共享sender增加显式上限参数，PUBLIC入口默认8KiB和已消耗回执不变。
5. 每根RootBudget完整limits/final_reserve：九个资源字段均须显式整数且reserve≤limit。R的model/input/output/cost全为0，S/M费用预留必须用确认的4Router费率计算。当前两个表三方法均null，空字典也不算配置完成。
6. 原生usage策略：建议require_native。field_absent、value_null、parser_rejected立即停止，保留未知占用和已知小计，不重试；正文不可用为unknown。缓存数缺失且费率不同则成本null并停止，不按0缓存或0费用结算。旧PUBLIC回执不足以判断三态，保持unknown。
7. 受控执行环境：存储额度与真实可执行写入守护必须同时绑定。prepare/execute不会把一串配置数字视为守护；execute_p1需由已确认控制入口注入可信counter与storage_guard（limit_bytes/root须匹配）。CLI当前未绑定这两者，保持not_started。不存在通过JSON布尔值绕过它们的开关。

## 后续一次确认可采用的边界提案

范围只为以上R/S/M各一次，先R正常流程，再S，再M；上一任务失败/未知/未闭合即停止整包，不进入异常场景、Q1/Q2或正式100用户。

- 固定4Router / https://4router.net/v1 / gpt-6-luna；并发1、重试0、不重定向、不回退模型。生成最多24次；若可信计数需联网，计数最多24次且必须另批已验证端点/回执契约；其他API=0。当前计数API仍0授权。
- 普通角色输出最多8192 token，final_submit最多1500；每模型根总输出额度提案98304，final预留1500。输入token额度与人民币/USD预算仍待可信计数和费率，不填估计或旧默认值。
- 单次HTTP≤30秒；R根≤180秒、S/M各≤360秒，全P1≤900秒；RootBudget覆盖主机取证/工具与发布收尾。到限停止，未开始槽保持未开始，不补0或补跑。
- 请求正文≤2MiB、HTTP响应≤64KiB（沿用已验证sender读取上限）；超限停止。输出目录固定data/recommendation-runtime-audit/ticket14-development/p1/<run_id>，每根≤64MiB、整包≤192MiB，须由受控写入守护实施。当前storage_limit_bytes=null、storage_guard未绑定。
- 审计复用原运行器、实际A封存和publication；不写Key/Authorization，不将独立参考放入模型请求。模型响应诊断只保留HTTP/模型/ID/usage三态与验证结果；不为诊断额外发送。

## 现合同下最小决策，不重复提交同一方案

保持现合同：无需更改正式实验条款；一次补齐上述计数来源、渠道费率/预算、上下文与边界、RootBudget/存储守护、P1授权即可安排受控执行。可信counter与storage_guard必须真实绑定，当前启动入口明确拒绝。

如希望在计数/费率仍未知时执行：必须单独批准“仅P1的精确计数前置豁免”和“仅P1的未知费用接受”，并另行确认P1预算策略实现；现RootBudget要求数值预留，不能把cost/input的null改0来放行。该调整需保持调用/输出/时间/存储硬界及final预留，native usage缺失仍停止，token/费用指标保持unknown/incomplete。正式100用户合同不变。本轮不实现或启用此豁免，避免把PUBLIC许可扩大为开发许可。

## 具体入口命令

工作目录D:\Work\Codex\Project\Thesis，先沿用项目TEMP/TMP与Conda缓存设置：

```powershell
conda run -p .\.conda\envs\Thesis python -B p1_runtime.py prepare --method R
conda run -p .\.conda\envs\Thesis python -B p1_runtime.py prepare --method S
conda run -p .\.conda\envs\Thesis python -B p1_runtime.py prepare --method M
```

候选启动入口为同命令的`execute --method R/S/M --config .scratch/ticket14-p1-wiring-20261020/p1.config.draft.json`（三方法分别执行）。**当前全部not_started、退出码2、API 0**；这是启动条件拒绝，不是模型故障。CLI不会自行加载未验证计数器或未绑定的写入守护；真实启动还需确认后的受控控制入口注入它们，不能把本命令当成已具备付费执行条件。
