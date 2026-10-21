# 固定候选审查记录

BASE b4d5cb2，首次候选cf512ca661d91b252034544e2d10d24755a875ee。

## Standards

独立代理closeout_standards：FAIL，1个P1。prepare_task先装配、后启用守护；旧_source_row免读分支仅覆盖R/S，M会读取私有评价成员行，违反输入/评价隔离。建议复用冻结安全成员证明及公共禁读回归。无另列P3；静态审查，没有API、凭据、评价文件读取或测试重跑。

## Spec

独立代理closeout_spec：FAIL，P1同上；P2为父进程stdout、execution-resources及worker-error不受共享1GiB实际写入限制约束，须预留并检查控制空间。无范围扩张或P3。静态审查，没有API、凭据、评价文件读取或测试重跑。

两项已定向修复、记录真实验证，再固定候选复核；本记录不代表PASS。
