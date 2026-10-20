# 冻结快照准入修复及真实R新尝试验收

结论：本轮准入修复、增量审查和实际R工程链路通过。BASE d4a96c5b00b170f7a2a7d13a8d4bd3f544727fbf；固定代码候选e07175e4b2e65c19c1b2b4254a0b51c43a69fadc。没有以测试通过替代真实执行；下列发布结果来自新授权的一次真实D1运行。

## 实际任务与产物

- task_key：7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874
- authorization_id：R-FROZEN-RETRY-20261020
- run_id：P1-D1-V00-R-R-FROZEN-RETRY-20261020
- 终态released，reason=null；stop_reason=first_10_qualified。
- 完整候选1493，C_sha256=6ce1fa2372935c80f0a66fc035b466acdc2c703726cedb56cecb82dc69f9a874；已核验10、合格10、推荐10，余1483未核验。按原R规则获得首10个合格项后停止，不称已核验完整C。
- 审计：[audit.json](../../../data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-R-R-FROZEN-RETRY-20261020/audit.json)
- 发布：[publication.json](../../../data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-R-R-FROZEN-RETRY-20261020/publication.json)
- 同目录attempt.json、budget.jsonl与上述两文件共2,385,316字节；SHA索引见resource-closeout.json。publication字节SHA与audit.publication_record_sha256相等；预算44项预留全部settled，无unresolved，末条seal结算ok。release_scope=development_pilot。

前三条实际推荐（顺序来自publication，名称从同一冻结catalog核对SHA后补充，仅展示，不再执行推荐）：

| 顺序 | parent_asin | 商品简名 |
| --- | --- | --- |
| 1 | B0B5L9Y7HQ | Organic Quick Cooking Rolled Oats，6磅 |
| 2 | B08C9J2F39 | Bob's Red Mill 无麸质速煮燕麦片 |
| 3 | B078BMGDYV | Bob's Red Mill 有机钢切燕麦 |

商品及历史评论为真实开发来源，检验和在售支持来自同商品SIM供应链；发布理由明确SIM，不代表现实商品认证或推荐效果已验证。原理由、citation和batch ID保留在publication及result.json，不另写生产答案。

## 修复与预检证据

复用原失败audit先建立0.09秒级非执行循环，两次稳定复现runtime_preflight_failed。完整_preflight条件表仅旧来源根为false，其余适用条件为true。诊断按3项可证伪假设收敛，详见diagnosis-and-tdd.md及preflight-conditions-before.json。

新增frozen_snapshot_error只接受已验收PILOT/parent/D1/R task/V00及原snapshot精确ref，核对C/H/base hash、view/snapshot身份、实际安全解析路径、bytes和SHA及快照时点。原路径、身份、输入、预算和PUBLIC限制保留；没有放行整个data/sim-scenarios、复制快照或把真实对象标PUBLIC。唯一同阶段复现缺口已解除，完整真实1493候选装配通过原_preflight后才固定候选。

6项新非执行回归及5项直接相关回归，共11项通过。覆盖合法快照、错view、双侧自洽但错ref、等长SHA变化、长度变化、越界/同目录其他快照/临时目录拒绝；内容变化仅在读取边界注入，冻结文件未修改。直接相关测试确认真实PUBLIC R仍可运行，而PUBLIC夹具套D1身份不能借冻结准入发布。未重跑A、上游、PUBLIC联网探针或旧整套。

同一BASE...candidate独立Standards/Spec均0项问题，见review.md；代码审查后未修改。随后才执行本轮真实R一次，6.6138413秒，非测试输出替代。

## 零模型、隔离和旧证据

RootBudget额度及实际model_calls/input_tokens/output_tokens/cost_microusd全0，audit消息数0，R的model=None；无counter/sender调用。进程全程和存储guard的network/credentials/evaluation访问计数均0；生成/count/其他API、网络请求、实际Key和独立评价标签读取均0。渠道/价格/计数未知项仍保留，不借R零模型用量给S/M填0。

原失败run P1-D1-V00-R-R-ONCE-20261020的audit、receipt、budget和attempt逐一核对字节/SHA不变，保留failed_protocol/runtime_preflight_failed，不覆盖、删除或复活旧许可。本次是同一D1/V00/R工程任务的新尝试，task_key和repeat_id=1保持；不增加独立样本或正式轮次。两份工程尝试证据并存。

## 资源与完成边界

新包49.6786353/240秒，包含原生所有操作/余额检查/文档/Git/收尾30秒保守上界（非实测）；R实际6.6138413/120秒；原离线累计1581.976921000137/1800秒，余218.023079秒，不重置或扩大全局。每次测试/执行均前后检查，5组；额度初始化后的原生操作前后另记operation-balances.jsonl，首次建立账纳入原生上界。

整包保守写入21,549,574/134,217,728字节（含16MiB原生预记），新R目录2,385,316/67,108,864字节。真实guard采用更严格的P1输出根总额度，计入原目录已存在512,986字节；本次guard总上界3,113,564字节，其中新写上界2,600,578字节。Job峰值162,394,112字节，另64MiB守护预留，4GiB限制；原生全局内存未实测。以上为既有保守口径，不冒称完整文件系统写入实测。

原离线账历史字节前缀SHA和T0账SHA均不变，只追加新包记录；旧超限未冲销。资源验收通过，新许可已消耗，无自动追加尝试。S/M、其他场景、P2/P3和正式100仍未执行。本轮成功仅表示R基线工程链路走通，未运行独立评价或验证推荐效果。

末次Git归档操作的后置余额采用只读终端回执，不追加已提交操作账；数值应与resource-closeout.json一致。
