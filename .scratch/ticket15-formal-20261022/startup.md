# 15.100用户全场景正式实验：启动清单

2026-10-22，Asia/Shanghai。**待一次统一启动确认，尚无生效授权；本轮供应商生成/count/其他API均为0。**

| 项目 | 冻结内容 |
| --- | --- |
| 范围 | 原100测试账户，18场景，一轮；5000方法任务=1600 R+1600 S+1800 M；3400模型任务 |
| 原计划 | `9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088`；六文件保持原字节 |
| 执行配置 | [config.json](config.json)，`52af1e5c161ed7cc7617716236f20245d1da475a8778d40648f448ab72c764af` |
| 版本 | 基线`1a2419db4d10e641b3c97548ea51c1a9fc327338`，继承`75f5943dfbf53301cf48217e4b11d1c734c3e8b0`；实际代码逐文件SHA及code_identity在配置中 |
| 提示词/协议 | composer 0.15.0，4Router runner 0.3.0，mapper 0.4.0，batch32 0.1.0；键控画像0.3.0、排序问题证明0.1.0；正式协调协议formal-test100-0.1.0 |
| 模型 | 4Router，`https://4router.net/v1`，`gpt-6-luna`；沿用本地凭据，费率/费用均为null |
| 调度 | 原冻结顺序，每批50任务、共100批，同批最多2个独立进程；首批属于原正式样本并计入全部统计 |
| 输入/输出 | 每task_key按需装配；独立输出`data/recommendation-runtime-audit/ticket15-formal/`；不复制完整数据、审计或预生成请求 |

## 调用、Token与时间

普通模型任务3200项，Q模型任务200项。普通路径9次/项，Q路径16次/项，三种Q评分组件共用同次运行的真实A/G/发布锚点，不另调模型。

| 预算 | 正常路径外推 | 保守场景/执行上限 |
| --- | --- | --- |
| 生成次数 | `3200×9+200×16=32,000` | 每模型任务18次，总共61,200次发送意图；失败、超时、不确定发送均不退还 |
| 输入Token | 5,811,130,300 | 128,345,702,400的保守情景值，按61,200×2MiB×1 Token/UTF-8字节；此映射未验证，严格Token上界未知，不能冒充计数结果 |
| 输出Token | 31,683,560 | 478,597,600请求配额上限；每run的17×8192+1500，最终预留包含在总量内 |
| 串行任务耗时 | 756,953秒，约8.76天 | 单任务看门狗1800秒；累计任务活跃时间9,000,000秒，约104.17串行天 |
| 并发2 | 理想约4.38天，另加协调、评价、限流等开销 | 任务活跃额度仍按两进程之和扣减；理论约52.08天，不是交付日期承诺 |

依据是任务14八项已选实际产物：5项普通模型均值1,509,007输入/8,557.8输出Token、205.899秒；2项Q均值4,911,539.5输入/21,493输出Token、440.367秒；1项R为6.252秒。详见[budget.json](budget.json)。历史失败不从总历史资源账移除，也不拿历史余额抵扣正式预算。Reasoning属于输出子量，缓存属于输入子量，不重复相加。

该外推仅来自1名开发用户，其余场景、用户、重修和限流未实测。普通任务若需多批取证会消耗更多调用；达到18次或时间上限即保留失败/未完成，不跑到成功。并发2的两个Job各限4GiB，当前机器约31.84GiB内存；不同任务的审计守护不在线程间共享。未探测供应商并发额度，429等模型失败按统一规则保留。

## 磁盘与停止规则

- 正常产物外推47.38GB，约44.12GiB：审计17.03GB、请求追踪12.07GB、发布8.99GB、预算账4.81GB、单份实际A约4.18GB，其余响应/元数据约0.30GB。R采用旧产物形状外推；新正式追踪形状的偏差由执行配额控制。
- 单任务128MiB（其中2MiB用于父进程控制/日志/终态）；5000任务逐项上限合计625GiB。总目录640GiB，另预留2GiB控制/评价空间；启动新任务时磁盘空闲还须保有20GiB。当前D盘约761.8GiB空闲，启动前重新检查。
- 生成次数61,200是发送前持久化意图的硬上限；R生成配额0。每任务一次执行，HTTP不自动重试。已验收的一次草稿修订及全run一次显式核验纠错仍共用18次额度。
- 单HTTP最长120秒，最终核验预留1次/1500 Token/145秒；单任务看门狗1800秒，Job内存4GiB。超限终止Job及HTTP子进程，原始产物保留。
- 任一代码/协议/原计划摘要变化、配置或授权不匹配、账本损坏、累计活跃时间/存储不足或`STOP`存在时停止新任务派发。没有自动换模型、换用户、重抽或追加额度。
- 中断任务记`unresolved_attempt`，已完成、失败和未决任务均不重发；未开始任务继续原顺序。未决项在统一统计中明确报告，不能伪称完整成功。
- 每批终态和逐任务发送账保留；全部原任务终态后自动独立评价并调用原score_task/summarize。评价按用户关联、逐个加载真实审计，保留全部5000槽位及失败；不按结果选样。摘要显示incomplete时如实报告。

## 执行与续跑

以下授权与执行命令只能在本聊天收到一次明确启动确认后运行。无需再逐批请求许可。

```powershell
Set-Location -LiteralPath 'D:\Work\Codex\Project\Thesis'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:TEMP='D:\Work\Codex\Project\Thesis\.tmp'
$env:TMP=$env:TEMP
$env:CONDA_PKGS_DIRS='D:\Work\Codex\Project\Thesis\.conda\pkgs'

# 仅首次明确确认后：生成独立生效授权；不修改原plan或冻结配置
conda run --no-capture-output -p 'D:\Work\Codex\Project\Thesis\.conda\envs\Thesis' python -B formal_experiment.py authorize '确认启动15.100用户全场景正式实验'

# 连续运行所有原批次；全部终态后自动评价
conda run --no-capture-output -p 'D:\Work\Codex\Project\Thesis\.conda\envs\Thesis' python -B formal_experiment.py run

# 只读状态
conda run --no-capture-output -p 'D:\Work\Codex\Project\Thesis\.conda\envs\Thesis' python -B formal_experiment.py status
```

续跑仍使用同一条`run`命令，不再次authorize，不重新创建配置、目录或会话。协调锁由Windows文件锁管理，进程退出自动释放；新协调器将未决尝试封存后跳过，继续未开始任务。

操作停止：在正式输出目录创建空`STOP`文件，当前最多2个任务完成后不派新任务。恢复时仅删除该空标记，再运行`run`；时间、调用或存储额度不会重置。需要单独重算评价时执行同环境的`python -B formal_experiment.py evaluate`，只新建评价输出、不发送供应商API。

## 验收证据

必要公共接口测试见[tests.json](tests.json)，同候选Standards/Spec审查见[review.md](review.md)，保护校验见[preservation.json](preservation.json)。旧外层测试守护依赖与新测试选择的说明均保留，不重跑上游全套。

[开发侧零命中核对](development-zero-hit-audit.json)显示八项的目标都在C但均未进入G/发布，独立HR/NDCG计算与历史记录一致；未发现本次核对范围内的关联或计分错误。不以提高指标为启动条件，也不针对正式用户调参。

当前[authorization.draft.json](authorization.draft.json)只记录待确认预算与身份，不授予发送能力；`authorization.json`尚不存在。
