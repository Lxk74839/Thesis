# 必要行为TDD记录

BASE：ee58d44244b7f86f958ecf8f9e92b61dc7704b1e（仅归档前轮已有B草案，其内容未改）。继承A验收，不重跑A。

| 公共行为 | 实际结果 |
| --- | --- |
| check区分空/已填且不显示Key | 001缺模块RED→002 GREEN |
| prepare复用既有公开模型/地址，仅PUBLIC，无凭据/数据读取 | 003缺接口RED→004 GREEN |
| probe在读取凭据前明确拒绝联网 | 005错返回invalid_command RED→006 GREEN |
| PUBLIC工具结果配对及封闭JSON往返 | 007缺接口RED→008 GREEN |

6项首次已经通过，没有制造RED：畸形凭据不泄漏、未知工具/续传停止、额外JSON字段拒绝不重试、错误模型/端点拒绝不沿旧默认、缺失/危险Key及未知命令不回显、prepare CLI仅PUBLIC。009全集10项通过（unittest 0.044秒）。

项目Python经本目录check.ps1→显式Thesis Conda→原Windows Job守护运行，使用manual4router_独立标签计入原离线账，未转用A包余额，未改旧守护或T0账。测试审计钩子拒绝网络及data/research/manuscript/.secrets读取，所有凭据用PUBLIC临时夹具。无新依赖，真实请求0。

实际本地凭据只以CreateNew写入空占位，从未作为测试或资源证据读取/摘要；git check-ignore确认.secrets路径被忽略。公开示例为空。新模块不含HTTP sender、计数调用或凭据发现逻辑；费用保持null。
