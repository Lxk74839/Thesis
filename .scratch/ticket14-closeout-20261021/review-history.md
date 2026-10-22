# 固定候选审查记录

BASE b4d5cb2，首次候选cf512ca661d91b252034544e2d10d24755a875ee。

## Standards

独立代理closeout_standards：FAIL，1个P1。prepare_task先装配、后启用守护；旧_source_row免读分支仅覆盖R/S，M会读取私有评价成员行，违反输入/评价隔离。建议复用冻结安全成员证明及公共禁读回归。无另列P3；静态审查，没有API、凭据、评价文件读取或测试重跑。

## Spec

独立代理closeout_spec：FAIL，P1同上；P2为父进程stdout、execution-resources及worker-error不受共享1GiB实际写入限制约束，须预留并检查控制空间。无范围扩张或P3。静态审查，没有API、凭据、评价文件读取或测试重跑。

两项已定向修复、记录真实验证，再固定候选复核；本记录不代表PASS。

候选47f85a4双轴各发现同一P2：评价派生标签目录不含精确evaluation路径组件，后续运行侧守护可读。真实评价尚未执行，未生成标签投影。PUBLIC实际路径回归先RED，再将全部评价产物移入OUTPUT/evaluation/<run>。后续复核关闭前不执行评价。

5f641a503dc292090d16bddd3628b5ca41bb4393: Standards PASS / Spec FAIL P2. Value equality could accept Boolean/numeric aliases in legacy PUBLIC adapters lacking full role Schema. No actual send under this candidate. Added local existing shape/matches check and production-run legacy regression; changed raw synthetic response is deep-copied to avoid mutating expected context. Genuine Boolean-alias RED released -> GREEN invalid_profile; equivalent-number production flow still releases.

959051ed7a99b814b0bd5b44b00bbb12cd61ab58: Standards FAIL / Spec FAIL, same P2. Reusing the existing R sidecar/A inside a new evaluation guard lacked its exact read-only paths. No actual request or evaluation under this candidate. PUBLIC actual-entry regression reproduced R_evaluation_forbidden; pinning only the selected old sidecar and its sibling R-acquired.json before the guard made all 4 evaluation tests pass. Canonical actual-A comparison and original R file hashes remain required; normal runtime evaluation reads remain denied. New194 grant review found no blocking issue; history158 and the two exact Q run IDs remain unchanged.
