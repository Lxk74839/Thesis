# 可重复反馈与定向验证

最小命令（项目根PowerShell）：

    .\.scratch\ticket14-message-parsing-20261021\check.ps1 repro -m unittest tests.test_fourrouter_message_selection

包装器使用Thesis Conda、项目TEMP/TMP及既有Windows Job 4GiB守护，测试审计钩子禁止网络和真实凭据/评价目录。无需新依赖。全部响应为PUBLIC合成协议样本，绝非A5原响应回放。

先执行phase_red：唯一合成commentary+final_answer在原生产normalize触发invalid_role_JSON；最小仅两message、一个最终JSON，无真实用户输入。phase_green：改为唯一业务message选择后PASS。

三项可证伪假设依次核对：跨message混phase导致拒绝（合成已证实）；同message分块逻辑错误（原已支持，定向GREEN）；JSON本身损坏（原就拒绝，A5正文未知）。不将第一项推广为A5真实根因。

edges_red：重复key原会被json.loads覆盖；拒绝重复key及非JSON常量后GREEN。其余单message、分块、多个业务项、未知phase/type、incomplete message、工具+commentary/工具+业务分支首次已满足或本次最小选择修复已通过，不制造RED。

capture_red：经真实ModelAdapter.prepare/reserve/invoke的失败PUBLIC响应没有business_output（KeyError）；新增有界失败捕获并在工程/严格适配器失败路径接入后capture_green共8项PASS。记录原分块、原索引/phase/status和UTF8文本哈希；文件写出→读回→生产normalize可得到同一JSON错误位置。reasoning正文/密文、HTTP头及凭据样式/实际认证回显不归档，超限不声称可回放。

call_status_red：已completed响应内的incomplete function_call原可执行；补状态检查后GREEN。

final_directed：25项PASS（当时12新增+6生产协议+6既有诊断+1完整S PUBLIC流程）。完整S合成9次、经生产reasoning/工具续接/画像引用/发布，费用及缺失usage保持未知。随后strict_and_echo：15项PASS（最终13新增+2直接影响的原sender/严格usage拒绝回归），新增的唯一认证回显例使用临时PUBLIC虚构Key及注入transport，无真实HTTP。两组并集28项，后组仅新增测试，生产代码未变；无需重跑未受影响上游、R、worker或冻结装配。

包内各测试前后budget.ps1均已检查；详细时刻/Job写入/内存在原追加资源账，摘要resource-checks.jsonl。未新增真实claim或调用，A1—A5证据与余额只读。
