# 冻结D1/V00/R快照准入修复与一次新尝试

Status: claimed

BASE d4a96c5b00b170f7a2a7d13a8d4bd3f544727fbf；继承84db61f及原failed_protocol/runtime_preflight_failed证据。先复用原审计和真实1493候选的非执行装配/预检复现并核对完整_preflight，修复同阶段已复现缺口，不以完整R试跑定位已知错误。

公共测试边界沿用assemble_task、build_runtime及用户明确指定的RecommendationRun._preflight；如需冻结来源校验，限此准入调用的布尔校验接口。预检不得调用RecommendationRun.run/取证/排序/发布，RootBudget除elapsed外所有用量保持0。诊断输出可在独立临时目录生成初始化日志；真实快照保持原路径，不复制、移入夹具或标为PUBLIC。

冻结来源必须以已验收PILOT_ID/父plan、D1、R task_key、V00 view及snapshot引用为依据，核对实际解析路径、字节和SHA256。不能放行整个data/sim-scenarios目录。合法原引用通过；错误view、引用不匹配、原路径内容改变（长度及等长SHA变化）、越界路径拒绝。保留原身份、来源、完整性及PUBLIC限制，不扩大S/M。

完整真实D1/R装配必须先通过全量_preflight的非执行回归，再固定候选独立Standards/Spec增量审查。既有A/上游/探针/旧全套不重跑。先诊断反馈RED，列出可证伪假设，再逐项TDD修复；首次已通过的行为如实记录。

检查及审查通过后，仅一次新授权：authorization_id=R-FROZEN-RETRY-20261020，run_id=P1-D1-V00-R-R-FROZEN-RETRY-20261020，同一D1/V00/R task_key，不增加样本或正式轮次。复用原R规则、完整候选、有效RootBudget及真实存储guard。原失败audit/receipt/budget/attempt保持原字节；不复活旧许可。新尝试失败/未闭合立即保留具体条件并停止，不自动追加执行或连续修复。

模型/网络/API/实际Key/独立评价标签读取均0；S/M和正式100未授权。所有运行显式Thesis Conda，无新依赖；不更改冻结数据/计划、评价器或论文。

新包240秒含120秒R及40秒收尾，同时继承1532.2982857001368/1800秒，不扩大全局；写入128MiB、R目录64MiB、4GiB。原生全部操作/余额检查/文档/Git/收尾30秒、16MiB保守上界预记，非实测。每次操作前后检查余额；测试留15秒/8MiB，真实R留125秒启动/执行余量及40秒/8MiB收尾，不足停止。旧超限不冲销。
