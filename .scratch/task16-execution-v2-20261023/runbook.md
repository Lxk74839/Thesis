# 独立PowerShell运行说明

## 当前交付边界

`run-task16.ps1`、根目录`task16_control.py`及离线公共夹具测试可独立运行。控制模块的双轴审查只覆盖本修订；不能充当整个推荐算法的最终审查。当前无生产worker、冻结16人计划、生产双轴封存或付费授权，因此生产`Start`/`Resume`拒绝，无网络及API意图。用户本轮明确要求“不启动真实API”。

## 环境和启动

工作根固定为`D:\Work\Codex\Project\Thesis`；脚本显式使用`D:\Work\Anaconda\Scripts\conda.exe run -p <项目>\.conda\envs\Thesis`，TEMP/TMP为项目`.tmp`，包缓存为`.conda/pkgs`。不安装新依赖。

在普通PowerShell运行，不需要保持Codex对话：

```powershell
Set-Location -LiteralPath 'D:\Work\Codex\Project\Thesis'
$task16Runner = '.\.scratch\task16-execution-v2-20261023\run-task16.ps1'
& $task16Runner -Action Status
# 完成后续算法实现、真实计划封存，并明确授权付费启动之后：
& $task16Runner -Action EndDevelopment
& $task16Runner -Action Start -ConfirmLive
```

如本机脚本执行策略阻止入口，可使用当前进程级命令，不修改全局策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  'D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1' -Action Status
```

Start启动独立隐藏PowerShell→Thesis监督进程→Windows Job受控worker；前台返回JSON。最多两个不同用户根并行，同根方法按计划顺序串行；整个阶段完成才进入下一阶段。重复Start不会取代活动worker。监督进程按原剩余墙钟约束worker及子进程，工作集提交额度4GiB、单worker标准输出1MiB；这是运行保护参数，不是推荐效果判据。

## 查询、停止与续跑

```powershell
& $task16Runner -Action Status
& $task16Runner -Action Stop
& $task16Runner -Action Resume
```

Status只读。返回就绪状态、活动worker、阶段/方法槽进度、成功/失败/未决请求数、usage已知量及未知请求数、已知Token费小计、原截止、新增字节和分项耗时。`complete`表示所有计划槽有已知终态，失败仍公开保留，不代表算法有效或调用全成功。未决/未启动不能标完成；应结合各阶段和失败数判断结果。

Stop只给当前worker代次写停止指令，不按任意PID杀进程。正在发送的请求允许结束并持久保存，再停止派新请求；若到原硬期限由监督器终止，在途请求按未决处理。Resume沿用预算、绑定计划、显式启动授权及已有结果，新worker代次不继承上次停止指令。计划/源码/来源/封存发生变化后拒绝续跑；需要先检查变更，不能通过重新建目录刷新额度。

请求写入顺序为：完整请求→发送意图→传输→响应→终态。成功结果按namespace、完整请求和材料依赖哈希复用；失败终态不反复请求直到成功。意图存在但无明确终态，或传输异常不能确认服务端状态时，保留unresolved并拒绝自动重发。同阶段其他不相关槽可完成，但有未决时不进入下一阶段。未决只能依据供应商可核对的真实记录另行处理；本入口没有“一键重试未决”或reset功能。

材料/场景/模型/额度/提示版本变化必须进入完整请求或dependencies。不得只换文件名、复用旧模型决定。未来worker必须用内容引用处理变化后的下游决定，且保留原结果；已封存计划不允许静默修改。请求<=128KiB、响应<=256KiB、单槽解析结果<=64KiB；超长响应保留终结失败与已知usage，不再发送。写入采用临时文件落盘后原子发布；方法槽把内容校验值与结果放在同一文件，避免跨文件半提交。

## 持久文件及时间

唯一原账目录：`data/recommendation-runtime-audit/macrec-agri-dev-task16/`。

| 文件/目录 | 用途 |
| --- | --- |
| budget.json | 不可重置的原起算、24小时、10GiB、6944次、给定单价 |
| storage-baseline.json | 既有共享.git/.tmp按文件大小基线，后续新增/增长计入；任务16专有产物全量计入 |
| run-plan.json / review-seal.json | 后续真实计划、来源及代码哈希、Standards/Spec报告；目前不存在 |
| run-binding.json / authorization.json | 首次启动绑定原账/计划/封存及显式付费授权；目前不存在 |
| calls/ | 不可覆盖的request/intent/response/terminal记录 |
| units/ | 原子提交的方法槽终态、内容校验及计划绑定 |
| worker.json / worker.lock / commands/ | 当前代次、独占锁及安全停止指令 |
| activity/ / supervisions/ / logs/ | 分项活动、监督终态、独立进程输出 |

开发、测试、必要审查和离线准备计开发活动；模型阶段的服务等待计模型运行墙钟；独立评价计评价。其余原起算至当前的墙钟为等待，包括暂停、关机和人工确认。活动并行时报告重叠，不将分类简单相加；逐API已完成时延之和另列。worker每秒写活动心跳；异常死亡以最后心跳结束活动，之后仍计总墙钟中的等待。正在开发时可用`BeginDevelopment`，交付或等待用户时用`EndDevelopment`，均不改变原起算。首段开发从原账活动起点计算。

所有新产物共同计10GiB：任务16原草案/源码副本、本修订、根控制代码/测试、模型实验目录、专用临时目录、共享.git/.tmp的新增增长及后续算法文件。每次发送前检查调用、阶段、单槽、22小时派发线和存储，预留32MiB收口及每次464KiB；24小时终止仍由独立监督器执行。Status会重新统计存储；应用内计数每30秒复核，给定预留与原2GiB估算余量不能当作可重置额度。暂停、关闭Codex、重启机器均不停止预算钟。

## 后续真实计划的必要接口

后续S1—S3实现`macrec_experiment.py:execute_unit(unit, session)`；所有模型发送经过`session.invoke(request, send, dependencies=...)`。`send`返回统一的`status: completed|failed`及供应商真实usage；不确定传输抛异常，不能在该适配器内自动重试。每根内串行调用公开接口，不能绕过控制器另起模型发送。返回`status: ok|failed_model|failed_protocol`和必要排名/结果引用。离线评价不发送模型、模型输入不含标签。

真实计划schema=`task16-run-plan/1`、kind=`live`；固定本规格13阶段、6944次上限，阶段槽数依次为`1,32,16,32,1,32,32,16,16,32,16,32,1`。每槽有id/root_id/phase/limit；同根单位在数组中的先后即派发顺序。32个参数槽每槽1次；特征16槽每槽18次；B0/I1和系统消融槽每槽37次；S/M各16槽分别1/6次；离线和评价槽0次。根数和用户/方法/场景内容最终由正式计划与算法验收核对，不能用空槽凑完成。

sources至少含panel/candidates/recall/evidence/model/algorithm_spec/upstream_lock/evaluation_contract八类来源引用；每项path相对项目、sha256固定。完整代码封存至少覆盖控制器、PowerShell、既有formal_process、生产worker及全部算法模块；两个实际报告分别axis=standards/spec、result=PASS，并经确认规格标记。控制器验证引用哈希、阶段及关键完整性；它不替代算法正确性审查。首次Start绑定plan/seal/budget，后续改动拒绝复用旧实验决定。现有控制审查报告不能被写成最终算法PASS。

## 离线控制验收

```powershell
$env:TEMP = "$PWD\.tmp"; $env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = "$PWD\.conda\pkgs"
$env:PYTHONUTF8 = '1'
& 'D:\Work\Anaconda\Scripts\conda.exe' run --no-capture-output `
  -p "$PWD\.conda\envs\Thesis" python -B -m unittest discover -s tests -p test_task16_control.py -v
```

测试只创建`.tmp/task16-execution/`公共夹具，不读模型凭据、不作推荐性能实验。夹具子worker另有禁止socket和子进程的审计钩子；独立监督器自身负责创建受控Python进程。保留red/green日志和固定候选双轴报告，实际生产调用账必须保持0。
