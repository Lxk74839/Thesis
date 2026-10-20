# 固定候选独立双轴审查

BASE：1d688a3ddee04f634773ad62204a69f45fd55f19
candidate：b3b56a5916909f4d3bd8cb2a9df3993df55af557
范围：同一精确BASE...candidate；仅本轮增量。以下为两个独立代理的审查结果，未合并或调整严重性。审查后没有修改代码或再运行测试。

## Standards — p1wire_standards

0项明确违反，1项非阻塞异味。

- [P3，判断性建议] 可能的Repeated Switches：model_adapter.py:249的if router与recommendation_runner.py:446的if self.fourrouter重复选择provider、计费和计数策略；prepare/invoke等处还重复判断同一execution_kind。继续修改这些策略时容易漏改其中一处。后续出现同类改动时可集中provider操作与绑定规则。本项仅为Fowler启发式；仓库“保持实现简洁、修改范围最小”优先，不建议本轮扩大重构。

未发现项目目录、材料只读、显式Thesis环境或工单路径方面的可证实违规。资源超限是root已独立核实的验收失败，静态标准结论不覆盖该失败。

只用原生只读PowerShell/Git，未运行代码、测试或API，未读取凭据、环境变量、private或论文。原生工具wall_time_seconds合计1.1018005秒（9次调用）。

## Spec — p1wire_spec

阻塞2项，非阻塞0项。

1. [P1] 写入资源验收失败。spec.md:19要求写入32MiB。按root提供的保守账为46,105,370字节，超过上限12,550,938字节；本包不能标为完整验收通过。
2. [P2] 合同缺项检查仍可能放行到真实装配。spec.md:11要求“缺失时，必须返回not_started/具体missing”，第15行要求未满足不装配真实任务；provider_fourrouter.py:15未检查project_id。其余条件满足而缺少该字段时，prepare_p1可返回ready；execute_p1在p1_runtime.py:117先装配真实任务，再于build_runtime第88行直接索引该字段抛KeyError。应在准入阶段枚举该缺项并停止。此结论为静态路径核对，未执行项目代码。

未发现新增越界功能；真实counter/storage_guard尚未绑定已在集中草案中明确披露，不另算遗漏。现有默认配置保持未启动，六角色、完整候选与发布路径得到复用。

API、Key读取、项目执行、文件写入均0。原生工具可见测量累计1.7796291秒；另一次元数据因输出截断缺失，全部合计保守上界2.1796291秒，非完整实测。

## 处置与资源口径

P1、P2均未解除；P3不扩大范围修复。资源写入账在审查前已超限，因此只完成只读审查和已预先计入的最小归档，没有继续修代码、测试或扩额。写入46,105,370字节是原生8MiB保守预留加Job/守护写传输量的保守计费上界，不是实际文件系统新增字节测量，不追溯折减以宣称合规。收尾文档不改变上述代码候选。
