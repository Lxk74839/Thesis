# 一次PUBLIC探针增量TDD

BASE：64ebc5155683a2ba3116e4c54a029f068d9f5a02。A与上游验收复用，不运行其测试。

| 公共行为 | 真实RED→GREEN |
| --- | --- |
| prepare请求reasoning.effort=none | 014缺reasoning→015通过 |
| live入口两轮及原生元数据脱敏封存 | 016缺入口→017通过 |
| 超时/发送未知仍记录null且停止 | 018缺失该次元数据→019通过 |
| sender子进程硬超时、Key不进命令参数、不重试 | 020缺sender→021通过 |
| CLI仅消耗一次回执、存在即拒绝 | 022缺CLI注入参数→023通过 |

024仅运行tests.test_fourrouter_probe和tests.test_fourrouter_live_probe：18项通过，unittest 0.220秒。新增8项，直接受影响既有10项；没有A或上游测试。4项新增必要拒绝/边界行为首次通过（重定向/错误模型/工具、总截止时间、第二次未知及不可信元数据、HTTP边界与子进程拒绝其他地址），未制造RED。既有空凭据CLI拒绝条件按最新确认更新，首次运行即满足。

测试全部使用PUBLIC合成Key与临时文件；审计钩子拒绝socket及真实数据/凭据路径。唯一真实子进程测试使用被固定地址校验拒绝的PUBLIC.invalid，无HTTP请求；进程时间边界测试注入外部process_run。实际密钥只由用户明确要求的现有check和后续一次探针读取；测试不读取。

守护及Conda启动全部追加原离线资源账manual4router_标签；check.ps1同时绑定新测试源码，执行真实探针时从脱敏回执读取实际请求数，避免沿用离线0。新增原生30秒/4MiB为保守上界，非实测。
