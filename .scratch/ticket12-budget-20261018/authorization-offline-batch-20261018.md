# 离线批处理子项独立确认与实施授权

日期：2026-10-18（Asia/Shanghai）。固定审查BASE：`ac4874c7218ea1a795ddf992a9c23d133766a293`。来源：本聊天人类用户明确指令“继续本任务，开展‘离线批处理最小实现与验收’，不新开任务”及其六项范围。

**只确认B01主案A及本子项必需的公共接口和文件变更，不确认整张B01—B12表。** 原提案spec/evidence/confirmation/map/issue五份Markdown、历史接受和原工单保持原字节。本记录单独界定新授权；旧提案的待确认文字不回写。

## 已授权范围

- 模型显式申请，批上限32；宿主按固定候选顺序执行list/read/assess/advance，当前候选未闭合不跳过，必要臂批内首10合格立即停止，不预读第11项；质量臂保持共同固定前缀。
- 六角色各自实际输出；追溯申请与读后续轮、逐候选画像、反馈修订与复核可查；完整C、H/S、信息权限、账户及证据范围保持。去除重复传递，不以hash冒充已读事实。
- 逐项取证计量、同一根预算、失败/重试/额外续轮实计、超限停住留账；最终提交预留受保护。受控路径4/12候选9调用、64候选13调用仅作离线行为验收，不证明自然协作或真实token容量。
- 按mattpocock-skills:tdd逐个公共行为RED→最小GREEN；禁止批量预写测试。已确认测试Seam仅RecommendationRun.run、EvidenceSession.dispatch和必要的ModelAdapter.invoke映射；通过返回结果/其指向的审计交付核对，不测私有方法或单独RootBudget实现。
- 只运行新行为及直接受影响的必要回归；旧全库、13公开组合和上游生成不重跑。完成后固定候选提交，以固定BASE开展相互独立的Standards和Spec代理审查，修复阻塞并定向复验/复审。

## 文件与资源白名单

生产只可修改`recommendation_runner.py`、`evidence_access.py`、`model_adapter.py`中本子项必需逻辑；不改变E2资格、质量公式、JointSession或旧公开fixture边界。新增`tests/test_batched_recommendation.py`，其中包含脚本模型/事实辅助，既有fixture及测试保持只读。新增本目录`diagnostics/run_check.py`及按需`protect_scope.py`/`check_delivery.py`和`verification/`文档，独立授权/分项接受另存。

项目根仍为`C:\Users\Kane\Documents\CodexProject\Thesis`。本轮固定唯一计算账根`data/recommendation-runtime-audit/20261018-batch/`，公开临时事实根`.tmp/recommendation-runtime/`；全部Python/子进程/失败/保护及验收累计不超过1,800秒，Windows Job进程树4GiB（含64MiB守护预留）。后续修正继续同一账，不换目录清零；中断占用未知先停住。所有项目命令显式使用既有`.conda/envs/Thesis`、Python3.13.16，无安装。此额度属于本次独立授权的新子范围，不重用旧专项余额。

本轮只提交必要源码/测试/诊断和本目录文档。开始时已有`reports/`及前轮五份提案未跟踪；reports原字节只读并排除提交，原五份提案仅随授权归档，不修改内容。不暂存其他既有产物。

## 未授权与保留门禁

B02/B03中的真实可执行数值不因本记录获批；测试资源/限额只作合成公共行为，不写生产预算配置。B09依赖锁、B10完整消息计数继续未决；不新增provider/counter模块、不安装依赖、不实现联网发送，不调用推理/计数/其他供应商API。

不执行T0/P1，不读取正式测试推荐表现，不部署链、不冻结预算、不关闭工单12。只验收本批处理子项，不宣称G1/G2整体通过；正式模型费用（包括USD6,000候选）没有获批。

## 完成标准

本授权前置归档；逐行为RED/GREEN及必要回归有原始记录；受控调用数、停止/计量、角色、额外工作和final保护符合上述公共行为；全部失败入同一资源账；候选提交固定、两轴审查分别报告；另写独立子项接受与剩余问题，不覆盖原提案/旧接受。
