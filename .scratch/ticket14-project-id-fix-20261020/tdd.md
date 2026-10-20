# project_id定向TDD与准入回归

BASE：1550051ef6d2e24f17e281c887f2526e74186ef5；继承b3b56a5。公开接口为prepare_p1/execute_p1，固定测试文件tests/test_p1_project_id.py。

001 RED：修改生产代码前运行新增2项。完整配置的R/S/M控制组均ready；缺失、null、空串、纯空白、整数、bool、list、dict共8种变体×3方法均错误返回ready，24个subTest按预期失败（unittest 0.167秒，exit 1）。有效配置测试首次即通过，不制造RED。RED只复现准入遗漏，没有继续真实装配。

最小修复：仅在p1_runtime.prepare_p1的R/S/M共用准入中增加三行project_id类型/strip非空校验；未改变有效值、未更改provider、运行器、预算、PUBLIC或数据路径。

002 GREEN：原新增2项通过（0.164秒）。每个无效变体只改变project_id，其余条件与先ready的有效基线完全相同；prepare及execute均not_started、started=false、missing恰为[project_id]、provider_requests_sent=0。逐变体断言装配、凭据/私有文件读取、count、send均0；完整有效配置仍ready，尚未开始，token/usage保留null。测试counter、费率、授权仅为PUBLIC准入夹具，不构成真实配置或真实计数回执。

003 定向回归：仅重跑此前3项直接相关准入测试（0.076秒，3项通过）：原草案拒绝R/S/M、fixture不能授权D1、空RootBudget/reserve仍缺失。原11项新增和29项直接回归结果复用，不重跑整套或真实流水线。

三次测试均由本包check.ps1显式conda run -p .conda/envs/Thesis，复用原run_check.py的4GiB Windows Job/全局1800秒守护；resource-checks.jsonl逐次保存before/after剩余秒与写入，前置保留20秒/16MiB测试和30秒/8MiB收尾，不足则不启动。003结束新包累计36.713942秒，保守写入8,534,827字节；仍余143.286058秒、58,574,037字节。原生30秒/8MiB保守上界已预付，非实测。

所有本轮生成/count/其他API=0，真实凭据读取=0，真实P1执行=0。测试有socket及私有路径审计阻断，装配与HTTP仅边界哨兵；没有读取实际用户或评价标签。原账只追加p1idfix_，上一包超限原样保留。
