# D1/V00/R单次工程试跑：未走通，已停止

代码候选84db61f2d1959b6c53e5d87b1c831e6936ab1c2e，BASE ed69dc2b2a6630d424e263fd3b43eb1879432669。

实际任务键：7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874
run_id：P1-D1-V00-R-R-ONCE-20261020
真实执行次数：1；未重试，许可已消耗。S/M、其他场景、P2/P3和正式100均未启动。

## 实际结果

终态failed_protocol，reason=runtime_preflight_failed。完整候选1493，C_sha256=6ce1fa2372935c80f0a66fc035b466acdc2c703726cedb56cecb82dc69f9a874；已核验0、合格0、最终推荐0。运行器的模型、工具和候选用量均0，实际没有进入取证/排序/发布阶段。publication_path=null，没有可展示的已发布推荐，不补答案。

实际审计：[audit.json](../../../data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-R-R-ONCE-20261020/audit.json)。同目录保留attempt.json和budget.jsonl；本目录result.json为小型脱敏执行回执。实际产物共512,986字节；三个文件SHA256记录于resource-closeout.json。审查通过后才执行，执行前后均检查资源，之后仅只读归档，未修改代码或再次测试/运行。

失败环节是RecommendationRun._preflight。只读核对已能确认一处路径不匹配：冻结V00 snapshot位于data/sim-scenarios/.../views/q_286b0847b020a9d2cb5baa04a756d4fac00299e9f17fa1756df55ca7a32a03f8/snapshot.json，而当前_preflight来源路径条件仅允许.tmp/recommendation-runtime或data/recommendation-runtime-audit。这一条件不包含该快照路径；不据此宣称已排除其他前置条件问题。本轮没有修改白名单或重跑，缺口保留供后续另行授权处理。

## 接线与离线验证

本次仅补精确task授权、真实P1StorageGuard、装配前一次attempt、冻结D1/R成员证明复用（不再打开其private评价来源）及development_pilot产物标记。候选完整性、原取证、base排序和发布校验没有重写。R RootBudget四项模型额度为0，120000ms总时限、10000ms收尾预留；费率、计数和S/M配置仍null，不套旧默认。

新增5项及直接相关5项，共10项通过；5个实际TDD循环及两次如实记录的夹具设置失败见tdd.md。此前A、11+29整套、旧PUBLIC探针、上游验收均未重跑。独立Standards/Spec审查同一固定BASE...candidate，均0项问题，见review.md；静态与离线通过不替代本次真实执行结果。

## 零模型、网络与评价隔离证据

- 审计messages为空；RootBudget实际model_calls/input_tokens/output_tokens/cost_microusd全部0，额度也全部0。R工厂model=None，未创建真实sender或counter。
- result.json的进程全程边界和运行中guard计数：network=0、credentials=0、evaluation=0。生成/count/其他API和网络请求全部0；实际Key/Authorization未读取、未输出、未归档。
- 真实执行使用已冻结D1模型输入及完整C；未读独立评价标签，成员资格复用已验收冻结证明。PUBLIC测试结果单独保留，不用来替代本次失败输出；未运行评价器。

## 资源结算与完成边界

本包63.443213/240秒，包含30秒原生操作/文档/Git/收尾保守上界（非实测）；原离线累计1532.2982857001368/1800秒。实际R执行0.3416361/120秒；该次守护及启动耗时均计入整包，精确值见原账和resource-closeout.json。每次测试/执行前后共15组余额检查，执行前保留125秒启动/执行准入与40秒收尾。

本包保守写入18,238,587/134,217,728字节（含16MiB原生预记）；R写入守护上界663,164/67,108,864字节，实际目录512,986字节。Job实测峰值26,042,368字节，另64MiB守护预留，4GiB限制；原生全局内存峰值未实测。原账字节前缀与T0账SHA复核不变；旧包超限记录保持，不冲销。

资源验收通过；代码增量离线验收和双轴审查通过；真实R工程链路验收失败。一次试跑交付已记录完成，但不得标记R已贯通、推荐效果验证、开发预实验或正式实验完成。任何后续修复与再次试跑都需新的明确范围和授权，本次余额不自动转为新执行许可。
