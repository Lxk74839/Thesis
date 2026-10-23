# 固定候选双轴审查：第一轮

Base：`7cf851e95b2254a76547d2785678f0056c1e1ff9`。Candidate：`eb77702f0e9af63376214766eeb5e346cc1dfb61`。

命令：`git diff 7cf851e95b2254a76547d2785678f0056c1e1ff9...eb77702f0e9af63376214766eeb5e346cc1dfb61`。两个独立代理只读审查，不执行真实API。

## Standards

**FAIL（1项P3，清理即可通过）**。

- `run-task16.ps1:53`：Start/Resume分支新增`$launchId`未使用；Worker分支另行赋值并实际使用。违反用户准则第4条“只清理自己修改产生的无用导入/变量”。删除Start分支赋值即可，无需重构。

其余未发现有据可确认的标准违规或值得报告的Fowler smell。范围集中、原材料只读、Thesis隔离、本地规格与工单符合项目约定。代理`/root/task16_standards_review`。

## Spec

**FAIL（2项）**。

1. **P1 丢失发送意图会刷新请求余额。** `task16_control.py:127、390–398`只统计现存intent，未检查孤儿响应/终态。完成一个夹具请求后误删intent，新进程查询/续跑少计调用、错误增加余额。违反`spec.md:19`“禁止通过重建目录/删收据获取新调用余额”和`:55`“收据篡改拒绝”。须独立持久请求账与交叉完整性检查。
2. **P2 到限状态未封存，后续查询恢复为ready。** `task16_control.py:430–440、553–558`只在监督调用当次返回stopped；后续Status不读监督终态/原限额，未完成显示ready。违反`budget.md:76`“封存partial状态，报告…剩余槽”。须持久partial、原因及剩余槽。

费用、V00优先、独立PowerShell、成功复用与未决不重发主体设计符合S4范围，未发现应处理的范围扩张。代理`/root/task16_spec_review`。

Standards共1项，最高P3；Spec共2项，最高P1。两轴分别保留，不合并排序。

## 修复证据索引

后续候选删除无用变量。P1新增持久`request-index/`并核对请求/意图/结果，缺失即拒绝；P2持久`halt.json`，返回partial与剩余/未启动槽，按worker代次处理。另补同进程相同在途请求等待共享及无模型本地工作的存储监测。对应red/green日志保留于本目录上级；修复候选另行固定与复审，本报告不改为PASS。
