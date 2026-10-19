# Spec

Reviewer: independent /root/pilot_spec. BASE05889b6, candidate98c09de187b40add76d14ea6e60b52391bf974d0. blocking_findings: 2.

1. [P1] G1程序准入遗漏实际编译依赖。合同4.2要求每次运行校验源码SHA、candidate差异及变化即停；t0_catalog.py:394—405使用evidence_verification.py/quality_fusion.py，PILOT_FILES、程序接受/差异门及guard缺失。G0后变化直到最终保护才拒绝。应纳入生产器、独立检查器、守护和candidate差异绑定，并验证编译前拒绝。
2. [P1] 输出路径在授权前可改变旧只读目录。限缩确认旧目录只读、合同4.2拒绝路径覆盖；t0_catalog.py:1402—1417及独立检查器756—760先mkdir，guard只截文件打开。应在变更前限定对应包/域输出，零编译测试副作用不存在。

其余已审范围未发现新增阻塞；四根、120键、首三键/续接、旧正文禁止读取、pilot与完整A隔离均有对应实现。仅静态审查，未运行测试或读取大对象/身份键/评价数据。
