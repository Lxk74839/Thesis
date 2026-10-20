# D1/V00/R一次工程试跑

Status: claimed

BASE ed69dc2b2a6630d424e263fd3b43eb1879432669。用户仅授权冻结D1/V00/R任务7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874一次；S/M及其他任务、场景、P2/P3、正式100均未授权。

沿用prepare_p1、execute_p1、assemble_task和RecommendationRun。公共测试边界：P1StorageGuard真实文件写入限额；prepare/execute的精确任务授权、真实守护准入和一次执行声明；冻结成员证明复用；原R的PUBLIC贯通及真实产物来源标记。先TDD后固定候选独立Standards/Spec，通过后才执行一次真实R。只跑新增和直接相关回归，不重复旧修复、A、PUBLIC探针、上游或整套。

R的四项模型额度和actual usage均0；计数、模型和其他API均0；实际Key读取、独立评价标签读取0。完整C不裁切，复用原必要条件取证、base排序和发布门禁。必要条件首次取得10个合格项即按原规则停止，不等同核验完整C，不做效果评价。

授权记录单独绑定R task_key。误选方法或任务在装配前返回not_started；属性空壳guard不得准入。真实guard在写入前计费、超额拒绝，限制输出根及64MiB，阻断网络/凭据/私有评价路径。已有冻结成员证明身份和SHA均验证后，仅本冻结D1/R允许复用证明，不再打开其指向的private/evaluation.jsonl；不更改冻结文件或旧来源验收。

运行产物按实际development_pilot标记，不冒充PUBLIC或真实模型。execute进入真实装配前先落一次attempt声明；任何错误/超时/未闭合保留证据并停止，不自动重试、补答案或修复后重跑。固定run_id=P1-D1-V00-R-R-ONCE-20261020。

整包240秒，40秒收尾；真实执行全阶段120秒计入整包。原离线1468.8550727001366/1800秒继续累计。输出64MiB、整包保守写入128MiB、4GiB Job，Thesis Conda、无新依赖。每次测试/执行前后检查余额，须容纳该次运行及收尾。原生文档/源码/Git/收尾30秒、16MiB保守上界预记，非实测，旧超限不冲销。
