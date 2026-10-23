# 已确认方案的业务实施记录

用户于2026-10-24明确确认原macrec-algorithm-20261023方法、320/16范围及S1—S5接口；费用/阶段/S4以task16-execution-v2-20261023为准。本轮授权业务实现、真实计划准备、离线测试与必要审查，真实API未授权。

实际完整审查基线：0545af7ebbec4e72ac604a67ed6d5cd9811b4880。保留原草案字节、原控制验收及100用户结果。仅新增三业务模块macrec_experiment.py、macrec_recommendation.py、macrec_evaluation.py和tests/test_macrec.py；必要接线阻塞另记。

S1 prepare使用允许数据投影；开发选择和评价标签在独立评价进程，导出仅含root/split_hash的开发索引。320离线选择CB/RRF/M后冻结模型可见H/C/D/b。S2在真实工具和可替换模型边界逐行为TDD；S3复用EvidenceSession及原资格/质量规则；S4接execute_unit复用现有入口；S5独立参考/全部用户指标，不导入推荐/资格算法制造真值。

不读取凭据，不调用真实模型，不重划分/清洗，不改论文或Fabric。原预算start=2026-10-23T11:28:03Z，派发截止=2026-10-24T09:28:03Z，总截止=2026-10-24T11:28:03Z，10GiB均不重置。
