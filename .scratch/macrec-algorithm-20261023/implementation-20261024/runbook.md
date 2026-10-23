# 独立启动与查询

本轮仅交付，不发送真实API。最终run-plan与review-seal完成后，以下Start为用户显式付费启动。脚本在独立隐藏PowerShell/受控Python进程运行，退出Codex对话不影响其正常生命周期；机器休眠/关闭的时间仍计入原截止。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Status

# 仅在决定实际发送时手动执行：
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Start -ConfirmLive

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Resume
```

默认会话目录：D:\Work\Codex\Project\Thesis\data\recommendation-runtime-audit\macrec-agri-dev-task16。所有阶段、请求意图/响应/终态、组件、forecast、评价与日志持久保存在这里。Status是只读；Stop在边界停止新请求，硬截止由原监督器处理。已成功请求复用，未决请求保持未决；Resume不补发。原时间、总调用与新增字节账均不重置。

offline→parameters→features-v00→v00-main→evaluate-v00→q1→q2→semantic→confidence→quality→feedback→auxiliary→evaluate-final。32业务核对后无通过配置、估算剩余时间不足或出现未决会按合同停止，保留partial。不能据partial声称全部16人/全范围验证完成。

原日本时间2026-10-24 18:28:03停止新派发，20:28:03总截止。过期后Start/Resume不会获得新窗口。查看evaluation、forecasts与Status即可核对进度，无需Codex持续发送消息；尚未运行的算法收益及渠道effort执行情况均未验证。
