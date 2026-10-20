# 14.真实运行接入与开发集预实验准备：最小接入草案

日期：2026-10-20（Asia/Shanghai）。Status: needs-info（待人类确认方案，尚非正式规格或执行授权）。

本轮只交付本草案。拟确认的内容是接线范围、公共 Interface、验收和下一阶段资源上限；模型参数可以继续为空。确认本草案后先做离线 TDD 和固定候选双轴审查；具体供应商实现还要等待配置确认，真实试跑还要等待独立执行授权。

## 1. 继承与本轮完成标准

- 工作根为 `D:\Work\Codex\Project\Thesis`。BASE 为 `dcd7f1971a41af7dd1b29421e250596af06faffd`，继承 `73914774e2fedd53071c7240c50b28b85be86194`。
- 验收依据：`.scratch/test100-evaluation-20261020/acceptance.md`、`.scratch/ticket12-budget-20261018/acceptance-test100-offline-20261019.md`；迁移按 `docs/operations/project-migration-20261019.md`。研究草案和论文只读，不能覆盖已确认规格。
- 冻结目录 `data/recommendation-runtime-audit/ticket12-100x18/plan/` 保持六个文件原字节。`plan_id=9c37ffec84af6b92b3aa6911666c42ae5d4dc1170afa1b82fd01e6e33e86b088`；`plan.json` 原始文件 SHA256 为 `ced63edbf099271cc9ba5282c6d4f1ee918353c9319b0e4c6bc8d4e927d25316`，两种身份分别保留。
- 100 测试账户、18 场景、1,800 绑定、5,000 方法任务、3,400 计划模型任务沿用原验收。原 `execution_authorized=false` 和 null 模型绑定不回写。开发清单使用另一身份空间。
- 本草案须说明安全装配、单一真实模型 Adapter、输出到独立评价器的转换、开发试点、待填参数、必要文件、公共测试及资源门。只核对关联所需的现有记录和接口，不重跑上游接受程序。
- 不重抽正式用户、不重建正式计划，不重开旧 T0 或非阻塞 P3；不安装依赖、不读凭据、不运行推荐、真实评价或统计，不调用任何供应商 generate/count/other API。论文双模块、六角色和 SIM 披露保持原合同。

## 2. 现有能力与实际缺口

| 现有位置 | 已具备 | 本次接线所需的最小补充 |
| --- | --- | --- |
| `experiment_runner.run_task` | 验计划、按键调度、终态复用、未决 intent 停止 | 目前需调用者先提供 PUBLIC `RecommendationRun`；补单任务来源解析及独立配置／授权记录的检查 |
| `RecommendationRun`、`compose_role_request` | 六角色／S／R、工具、发布门、预算和实际质量组件 | preflight、模型 ID、prepare/count 分支、发布 scope、组件来源及请求次数均有替身绑定；须有单独开发接入分支 |
| `ModelAdapter`、`provider_openai`、`InputCounter` | 公共／原生形状替身、封闭输出、准备摘要、计数回执、usage 保守结算 | 无真实生成 sender；旧模型／价格写死，真实 count 许可又绑定旧 T0 全目录，不能直接沿用 |
| `score_task`、`summarize` | 已接受的纯评分与固定配对汇总 | 缺真实任务、审计、实际 A/G、私有参考的读取与转换；当前 CLI 只允许 PUBLIC |

直接删除 PUBLIC 检查、改 provenance 标签或只注入一个 HTTP transport 都不足以完成接入。保留旧公共路径和其回归；新开发路径须同时检查来源、清单、配置、授权及真实 transport 来源。真实 Adapter 的具体线协议待渠道明确后再定，不在本草案选择供应商。

## 3. 单任务装配及独立记录

### 3.1 来源链与读取范围

1. 正式任务的解析顺序是 `tasks.task_key → binding_id → user-scenarios.root_task_id/view_id → root-references + scenes`。读取被冻结组件并核对其 bytes/SHA；根和候选按已保存 offset/bytes/SHA 定位，只装配这个根，不展开全体请求目录，不调用 `build_plan`。
2. 安全根来自联合包 `model/roots.jsonl`，候选来自 `model/candidates.jsonl`，目录来自 `model/catalog.jsonl`，父商品—SIM 批次关系来自已接受 `candidate-map.jsonl`。保留完整有序 C、H、b 和批次映射，核对 C/H/base 摘要及根 ID，不按预算裁短 C。输入字段白名单继承 `JointSession`，不把管理根记录整体序列化给模型。
3. 原 8 及 Q 场景读取既有 `existing_binding_ref`；新增 8 场景复用已冻结 `scenes` 的真实 snapshot/view 身份和同一已接受请求、权限、核验时点，不生成新事实／参考。共同必要请求为 `R1_AND_R5_SIM_Q1_ON_SALE`，principal 为 `SIM-VERIFIER`，核验时点为 `1791417600000`。读取相应快照的 policy、登记与动作范围；这些是工具会话约束，不能由模型参数改写。
4. 用 `JointSession(root, candidates, catalog, view, opaque_handle)` 提供安全初始请求和候选分页。源投影使用 `history`，运行器读取 `H`；宿主须把初始请求中的 history 原值映射成 H，核 H_sha256 并重新计算 input_fingerprint，新开发分支显式接收这份已验证的初始投影。只改变本次内存投影，不修改源文件或改动分页合同。用 `LocalEvidenceSource(snapshot_ref)`、`EvidenceSession` 提供本快照实际获准读取的材料；新分支仅许可接受记录精确绑定的原快照路径，不能把现有目录守卫整体放开或复制快照到旧允许目录来绕过。宿主将根级 `RootBudget` 同时注入证据会话、模型和运行器，保持原批量取证和发布规则。
5. `RecommendationRun` 的 binding 逐字段装配：task/run/root/view、method/repeat、arm、完整 C/b/batches、H 摘要、请求、snapshot/material_version、principal/verify_at、K、停止规则及 Q fusion。候选 `b` 映射为 base_scores，评价器的 `base_scores_sha256` 对应运行器 `base_score_sha256`；请求的完整条款留在安全请求中，运行 binding 的 necessary_clauses 取其 clause_id。仅做字段转换，不能重新估计分数或丢弃条款含义。
6. `view-bindings.budget_candidate` 是历史候选，`execution_budget=null` 仍代表未授权。实际 limits、final_reserve、输出 cap 和 API 预算只能来自本次经确认的独立记录；缺项先返回 `configuration_required`，不能创建运行预算账或进入 sender。R 的模型次数／token／模型费用必须为 0，本地资源也须获准。

读取绑定所需摘要不等于重复上游验收。对于缺少逐行定位的开发根，确认后仅做一次有界定位并保存选中行引用；原文件不复制，不建立新 T0 目录。材料继续沿用现有按需读取方式。

### 3.2 开发清单、配置与授权

确认后才新增 `data/recommendation-runtime-audit/ticket14-development/` 下的独立记录，禁止写入原 `ticket12-100x18/plan/`：

| 记录 | 必须绑定的内容 |
| --- | --- |
| `pilot/manifest.json`、`pilot/tasks.jsonl` | `source_scope=development_pilot`、独立 pilot_id、任务键、开发成员证明、安全来源行引用、场景引用；`parent_plan_id` 和冻结 plan 文件引用；自身 bytes/SHA |
| `configuration/<config_id>.json` | 唯一渠道／模型、能力及计数／价格版本、预算和请求参数；内容摘要。未填字段保留 null |
| `authorizations/<authorization_id>.json` | 人类确认来源、config 摘要、pilot_id/清单摘要、允许 task_key、阶段、输出根、期限、次数／费用上限、generate/count/other 分项许可；凭据只记录取得方式引用 |
| `runs/<authorization_id>/<task_key>/` | 本次 task intent、run_id、审计／publication／trace 引用和终态；引用配置及授权摘要，不修改清单计数 |

开发 ID 从已接受的 ID/split 管理投影选取；管理投影仅取 `task_id/split`，不读取目标或评分作为选择依据。会话与模型请求不接收此管理来源路径、split、冻结抽样信息、场景标签、mutation-plan、target、参考四态、适用性掩码或评价文件句柄。独立参考正文只允许后续评价侧读取。

运行入口核对 `parent_plan_id + pilot_id + config_sha + authorization_sha + task_key + source_scope`。本阶段授权只允许开发清单；即使误传冻结测试键或配置中填写了真实模型，也在任何凭据读取／网络之前拒绝。正式执行将来须另签精确绑定冻结身份的授权，原计划的 false 不改为 true。

## 4. 真实模型 Adapter 的最小合同

仅接一个确认后的渠道，复用现有 `prepare`／`invoke` Interface 和角色输出 schema；不增加供应商注册表、自动路由或多渠道框架。

| 环节 | 与公开替身的必要差异及验收 |
| --- | --- |
| 请求 | 从确认配置取得精确模型版本、渠道／base_url、输出 cap 等；确定一个 mapper 版本。准备完整请求字节、角色 schema、工具 schema 及摘要，计数与发送绑定同一输入。新分支沿用已验收 on-demand 的事实稳定顺序。不能回退到 `provider_openai.MODEL` 或旧价格 |
| 计数／预占 | 先取得覆盖完整模型输入的可靠计数回执，再按输入、输出 cap 和已确认价格预占。回执绑定模型、渠道、项目、mapper、schema 和正文摘要；真实来源与 fixture 分开。缺可靠计数则 `incomplete_count`，不以字符／合成单位估官方 token。旧 `_external` 的 9,600 根 T0 许可不能套用到本试点；需新增仅本清单的许可分支，付费或免费 count 均需分项确认 |
| 发送 | 只有通过配置及授权检查后才取得凭据。固定确认的端点和方法、显式超时；禁止隐式重定向、SDK 自动重试、备用模型及未申请的服务端工具。一次已持久化 intent 对应至多一次发送尝试，包级预算也先预占，避免逐根都不超额而总额超支 |
| 工具 | 保持 `call_id/name/arguments` 与结果的配对和唯一性；只允许既有 `candidate_page/list_evidence/read_evidence/acquire_batch` 中本阶段获准的工具，宿主执行。模型不能改根、快照、权限或预算；批量上限沿用已验收合同。供应商工具调用结构由单一 mapper 转换，不把模型文本当工具结果 |
| 结构化输出 | 非工具输出须满足该角色／output_kind 的封闭 schema；工具输出与最终内容分支不混用。拒绝非 JSON、额外字段、截断和拒答，不用生产程序替模型补答案。是否支持原生结构化输出、如何映射，在配置明确后查官方文档确认 |
| 错误 | 保留 HTTP 状态、允许的请求标识、有限原始错误体及是否已发送／未知。认证／能力错误停止；拒答、格式、限流、超时等沿用现有分类。只在已知 usage、明确可重试及剩余预算充足时按显式重试参数继续；未知发送、缺 usage、计数漂移、返回模型错配或超额时保留占用并停止，不猜测免费、不自动重发 |
| usage／费用 | 保存原生 usage 原文及规范化 input/output、cached/reasoning 子量；保留未知 null，子量不重复加总。费用按确认价目版本计算，计数费用另记；不采用旧固定公式。原生 token 已知与费用是否绑定分开记录；费用未知时禁止继续放行 |
| 身份／来源 | 本地 request/attempt/run ID 不覆盖供应商 request ID 或 response ID；各自保留，供应商未返回时为 null。只有真实 sender 的实际证据可标真实来源；注入 transport、fixture_count、旧合成返回永远保留 fixture。请求次数来自实际发送记录，未知单列，不能沿用运行器写死的 0 |

顺序为：准备 → 可靠计数 → 根级及包级预占 → 写 intent → 发送 → 规范化 → 结算／保留未知占用 → 封存。计数也是网络操作，不能在配置检查或所谓 dry-run 中偷偷触发。具体字段映射、计数能力和价目证据均待单一供应商明确后实现；本轮不检索或读取凭据。

## 5. 实际输出如何进入已接受评价器

另设很小的评价 I/O 模块，调用既有纯 `score_task`／`summarize`，不放宽现有 PUBLIC CLI。运行代码不依赖该模块；评价模块拿不到模型 Adapter 或可执行取证会话。

### 5.1 task、execution 与实际 A 的转换

| 评价字段 | 唯一允许的来源／转换规则 |
| --- | --- |
| task 的身份与 BINDING | 从已验证的任务装配结果取得 `task_key/root_task_id/view_id/scene/method/repeat`，以及 `material_version/snapshot_id/request_profile_id/principal_id/verify_at_ms/C/batches/H_sha256/base_scores_sha256`；Q 再含实际绑定的 base_scores/fusion。scene 只在评价侧加入 |
| `started/terminal` | 有明确无副作用拒绝记录的 `configuration_required/not_started` 为 false；持久 intent 已开始后为 true。七种 FAILED（`failed_model/failed_protocol/failed_source/blocked_evidence/incomplete_budget/incomplete_count/incomplete_deadline`）原样保留；running／未闭合 intent 为 unresolved。无记录保持 None，不能编造未执行或失败记录 |
| `delivered/G/cursor/stop_reason` | 来自同一次运行终态、实际 state 和审计；与 publication、task/run 身份及其摘要一致。不能从独立参考筛选、补齐或重排生产列表 |
| `assessments/complete_C` | 从实际审计取每候选 evidence_state；未取得者留 Unassessed。complete_C 需要实际 cursor 和完整 C 的闭合评估证明；不能用“清单已读完”替代。合法空列表仍须原发布门及完整 C 空资格证明 |
| `gate_passed/publication_verified` | 核同一次宿主 final/commit/封存结果、publication 文件摘要、draft/delivered/G/A 绑定及终态。成功终态名称或文件存在都不能单独令其为 true；缺必需审计或坏引用是管线错误 |
| `acquired/components` | 使用完整 M 本次实际 A、G、终态和 `full/no_quality/mean_quality` 原组件。Q anchor 核 A/fusion/C/base/H/快照／游标／终态及 publication 身份；不得重跑取证或把参考原件填回 A |
| `usage` | 按尝试／回执 ID 汇总本任务全部成功、失败和重试，区分原生／合成 basis；不要累加每条累计 budget 快照。未知保持 null 和已知小计，Q 三组件不重复计费；原生 usage／请求 ID 原件由引用定位 |

当前 on-demand 审计会把 A 中 `raw_utf8` 换成摘要，不能直接将其当作评价器所需的完整 A。最小补充是：结束时将会话中实际 A 经现有 trace 写入方式封存一次，审计／task 只增加 `acquired_ref`（path/bytes/SHA）。评价侧读取该原件并核 A 摘要；找不到就报管线错误，不能重开源会话或按参考补原文。这只保存实际取得范围，不导出整个证据库，不重封旧审计。

已开始失败按 F1 处理，参考适用处计 0；未执行／未决／缺记录为 null，后三者阻止完整交付；参考 NA 单列原因，不与运行失败混同。坏绑定、缺参考、缺实际产物不能伪装成合法 NA。冻结测试计划的全集外连接和 cohort 不变。

### 5.2 独立参考与汇总

- 评价侧读取联合接受记录 `independent_reference.components`：`preference-reference.jsonl` 取得 target 和来源，`sim-reference-index.jsonl`／`q-applicability.jsonl`／`uq-mask.jsonl` 取得已接受关联及适用性；原 8 沿用该关联。新增 8 按候选、批次、视图、请求、材料版本和快照连接工单 11 接受记录中已存在的独立 `reference.jsonl`。这是读取／关联，不能重跑参考生成器或生产核验器来生成 gold。
- 构造精确 BINDING、完整 C 四态和 `source_ref`；所有组成来源都有 bytes/SHA 引用，不能仅有一个无法覆盖其余来源的路径。缺键／错配立即报 pipeline_error。评价参考与其适用性在看运行成败前固定，不按成功任务重新选 cohort。
- Q 仍由实际 M 锚点派生三组件；复用评价器既有纯质量一致性检查，只传 fusion 和实际 A，不传 reference，不发生 I/O。失败锚点三组件共同按原规则计分。评价器核心函数及 F1/F2 无需修改。
- `summarize` 要求所有 18 场景、每用户 50 个方法任务槽位。本试点只有 8 个调度任务，因此首先验单任务 `score_task` 接线。若核对汇总接口，另建开发集的完整 50 槽评价视图，其余 42 槽明确 not_started，结果应为 incomplete；这不是扩大执行清单，也不调用 `build_plan`。不得缩成 6 场景后冒充完整汇总。
- 开发集视图使用独立 pilot_id，原 8／新 8／Q 分组、用户级权重、种子和 NA 规则沿用；n=1 不造区间。正式计划的 100 人汇总不在本阶段执行，开发结果不回填正式样本。

## 6. 开发集最小试点（方案，未执行）

基线只取 1 个开发账户 D1：`015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e`。该 ID 为已接受 320 个 dev 的 task_id 按 ASCII 升序首项，本轮仅从管理 ID/split 投影核对，未按 target、参考状态或模型结果选择。确认后将成员证明及与冻结 100 账户交集为 0 的检查写入独立 pilot 清单。暂不启用 D2/D3，不因效果不理想更换 D1。

清单 scope 拟为 `ticket14-dev-pilot-0.1.0`，键为 `SHA256(UTF8(紧凑JSON([scope, D1, 已冻结view_id, method, 1])))`，无 BOM／无换行。下列是待确认的完整键，不是已发布计划：

| 阶段 | 场景／方法 | task_key |
| --- | --- | --- |
| P1 | V00／R | `7f9dfd3a6204d33a3c90e3ef0de8cd52bd46bc56ba23e328c479aacb683f0874` |
| P1 | V00／S | `a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4` |
| P1 | V00／M | `4fc09c3d2c7a0ad10bf5af864479975fc62c3d12c7b4f8b8f476094651a9694e` |
| P2 | V01 缺原文／M | `5f6174e27e713189c45fcfd348cb1a22758bf3098bf7baecab10c8eaed10ece8` |
| P2 | V05 有效否定／M | `1f32a41c58c91b83aa5b31d4bfb654a9defb348721569c8f28d5dc1e2177a291` |
| P2 | V06 有效冲突／M | `e1606ef935844cd2324ed4dce4b946ef887171413632bf9ca28996d0ac442b6b` |
| P3 | Q1／完整 M | `158c0644067e77ecfa3435163d9d07789bf0925c09028a540065a68129630a86` |
| P3 | Q2／完整 M | `9a373be927071c842734a0a2b03bc79b133b04cb06dbe8394910da9ec7ed39c8` |

合计 8 个根方法任务，其中 7 个使用模型；每项 repeat=1。7 是模型任务数，不是 API 次数上限或预算估计。

| 阶段／先决条件 | 验收条件 | 停止条件 |
| --- | --- | --- |
| P0：方案确认后的离线接线 | 真实来源只读装配不启动运行；PUBLIC 手写夹具验证完整接线、权限拒绝、错绑定、格式／截断／超时／未知 usage、合法空、未决意图和预算停止。所有 fixture 保持 fixture 来源 | 来源／配置／权限缺项即拒绝；不得为通过测试修改真实源文件或启用网络 |
| P1：供应商实现审查通过且配置、费用和阶段授权齐备 | 依次运行 V00 R→S→M；安全输入一致、角色／工具遵循权限，宿主门禁及终态闭合，实际 usage／请求身份可查，单任务评价输入可独立关联。S/M 正常发布路径须实际成功后才能继续 | 任何未知 usage／发送、坏审计／错绑定、越权、正常路径失败、时限／包额不足即停止后续任务 |
| P2：P1 通过并获本阶段授权 | 依次 V01→V05→V06，保持相同 C/H/b／请求／预算合同；记录实际 A 和回执。异常确实被取得时才核 Pending／Refuted／Conflict 与发布约束 | 真实 A 未触达异常对象则记“路径未覆盖”并停止该阶段；不能把场景标签当覆盖证明，不能改队列、删除正常候选、补证或自动扩账户 |
| P3：必要异常接线通过并获本阶段授权 | 依次 Q1→Q2；核 M 实际 A/G/fusion/终态及三组件、mean 分母、full 发布一致性；组件重排无额外模型调用 | 任一锚点错配、全组件结算错误、参考补证或资源触限即停止，保留失败原件 |

必要臂仍在取得第 10 个合格候选时停止，故异常场景不保证自然触达扰动对象；本方案不预称已覆盖。其余错配／摘要／撤销／拒读等最小接线风险先在 P0 公共夹具验证，不额外安排真实场景调用。若必须补实际异常覆盖，可另提最多 D2/D3 的有界扩展及新任务键，先确认，不自动消耗。评价侧只读参考核验结果，不能向运行侧回送“正确答案”。

试点验收是接线、权限、来源、终态和计账的工程验收，无准确率提升门槛；不以试点替换正式 100 人，不宣称样本充分、真实供应链验证或正式实验完成。

## 7. 真实接入前集中待填参数

以下均未确认，继续为 null；不从环境、旧记录、旧默认模型或价目自动补全。本轮不创建这些配置文件。

| 参数组 | 必填内容／当前状态 |
| --- | --- |
| 模型与渠道 | model_id（精确版本）、channel、base_url、生成／计数端点、项目／租户身份：null |
| 模型能力 | 上下文／输出硬上限、工具及封闭 JSON schema 能力、采样／推理参数、服务层级、超时、请求／响应大小上限：null |
| 计数方案 | 精确输入计数方式、支持证据、回执版本、字段含义及与返回 usage 的比较规则：null；能力不满足则暂停接入，不能放松已接受预算原则 |
| 价格 | 币种、单位、普通／缓存输入、输出／推理计费关系、计数及失败收费、有效日期和官方来源摘要：null；确认免费也须有证据 |
| 根级预算 | RootBudget 的 model_calls/input_tokens/output_tokens/logical_tools/physical_tools/candidates/retries/elapsed_ms/cost_microusd，以及同键 final_reserve、Q prefix_limit、每角色输出 cap：null；停止规则沿用，数值另确认 |
| 包级 API 预算 | generate/count/other 各自调用上限、总费用硬额及分项额度、未知占用处理、重试上限、并发数和总截止时间：null；不得用计划模型任务数代替 |
| 执行授权 | pilot 清单摘要、parent_plan_id、允许 task_key／P1—P3 阶段、配置摘要、批准来源／有效期、独立输出根、资源上限：未签发 |
| 凭据取得方式 | 经批准的本地凭据引用／注入方式、所需权限和日志屏蔽规则：null；凭据值不进入配置、清单、审计或仓库，本轮不读取 |

配置确认不等于执行授权。先依据确定的唯一供应商官方资料实现并离线验证，再签具体阶段的真实试跑授权；缺任何必需项都保持停止。当前所有 API 许可为 0。

## 8. 必要文件和公共测试 Interface

下面是拟实施范围，不是本轮修改清单。A 为确认草案后可做的离线接线；B 为配置明确后才做的具体供应商接入。B 仍需固定候选审查；付费运行另授权。

| 文件 | 最小变化／阶段 |
| --- | --- |
| `experiment_runner.py` | A：新增只读 `assemble_task`；`run_task` 增加可选 execution_record，旧调用行为保留。新路径只接开发清单和精确配置／授权，配置不足不构造运行副作用；B 后才能启用真实 Adapter |
| 新 `experiment_io.py` | A：仅实际产物到评价输入的 I/O、关联及只读转换；提供 `load_evaluation_inputs`。复用纯 score/summarize，不扩旧 PUBLIC CLI |
| `recommendation_runner.py` | A：已验证初始投影的接入、实际 A 的单份引用和必要输出字段接线；B：只在新开发模式接精确来源许可、配置模型、prepare/count/预算、真实来源／scope／计数。保留宿主门禁、六角色、取证／排序／反馈算法 |
| `model_adapter.py`、`token_counting.py` | B：仅新开发模式的单一 Adapter／完整输入计数回执许可及错误、usage 绑定；旧 fixture 和旧 T0 入口仍按原限制执行 |
| 一个供应商实现文件 | B：若确认渠道与现有 wire 合同一致，局部改 `provider_openai.py` 的配置绑定并加唯一 sender；否则新增一个对应具体渠道的文件，现有文件只读。两者择一，配置未定前不实现，不增加选择框架 |
| 新 `tests/test_live_integration.py` | A：手写 PUBLIC task/审计/参考和独立期望覆盖装配→执行替身→评价输入；真实来源仅测只读装配／拒绝。B：追加该供应商的固定原生形状夹具，注入 sender 始终标 fixture |
| `.scratch/ticket12-budget-20261018/diagnostics/run_check.py` | A：只增加新包的来源／输出白名单、计账／源码绑定；不放宽旧包网络或私有读取限制，不改旧检查器业务语义 |
| 本 `.scratch` 目录及新开发审计路径 | 确认后归档 spec/confirmation、单独实现工单、TDD、固定候选、两轴报告及资源结算；开发清单／配置／授权按各自门限另写 |

保持只读：`experiment_evaluation.py` 的纯函数及 CLI、上游数据／参考／接受链、正式六文件、旧 T0/P3；`JointSession`、`EvidenceSession`、`RootBudget` 的现有 Interface 直接复用。若发现必须更改这些合同，应先报告本草案不足，不能借接线顺手扩范围。

拟确认的公共测试 seam：

| Interface | 覆盖什么；不承诺什么 |
| --- | --- |
| `assemble_task(plan, task_key, *, execution_record=None)` | 返回单任务安全装配结果／明确 missing；核来源、history→H 与 b 字段映射、输入指纹、权限、开发身份和 null 配置，无运行／网络副作用。不重算上游数据充分性 |
| `run_task(plan, task_key, *, runtime=None, output_root=None, execution_record=None)` → `RecommendationRun.run()` | 旧路径兼容、新开发分支授权、一次执行／终态复用／未决停止、审计到输出引用；PUBLIC 可注入运行器不能取得真实来源标签。不验证真实供应商服务质量 |
| `ModelAdapter.prepare(request)`、`invoke(request)`；`InputCounter.count(prepared, *, authorization)` | B 的完整请求、工具配对、结构化输出、计数预占、错误、usage 和来源；通过注入 transport 测合同，不能把它当付费接通证据 |
| `load_evaluation_inputs(plan, *, execution_index, reference_sources)` | 评价侧核真实引用后返回 `(evaluation_plan, observations)`，后者含 task/execution/reference；无模型／工具执行能力。缺失／坏绑定按原管线错误处理，不生成参考 |
| 原 `score_task(task, execution, reference)`／`summarize(plan, task_scores)` | 手写期望核适配后的失败／未执行／NA、Q 锚点和 incomplete；不重验 F2 全部统计实现，不宣称开发效应 |

逐行为 TDD：一个公共行为 RED→最小 GREEN，再进入下一个；既有行为首次通过如实记录，不造 RED，不测试私有方法。测试基准用手写夹具／手算期望，不从生产输出生成 gold；只允许在 transport 等外部 seam 注入替身。

直接影响回归限于：`test_experiment_runner` 的固定键／配置拒绝；`test_on_demand_runtime` 的 prepare/schema／终态复用／未决 intent／未知 usage／Q；`test_root_budget` 的最终预留和未知占用；`test_batched_recommendation` 的第十合格停止及 Q 同 A/G；`test_experiment_evaluation` 的绑定、失败／NA／空／缺记录、Q 和 usage 去重及 PUBLIC 拒绝。B 修改 Adapter/count/wire 时再加 `test_model_adapter/test_provider_openai/test_token_counting` 对应公共行为。固定队列之外只有新失败或新增影响才扩检，不跑全库／上游接受／旧 T0。

A 完成后固定精确 candidate；两名独立代理以同一 `dcd7f19...candidate` 分别做 Standards／Spec 审查，各报各轴。仅修范围内阻塞，修后两轴核同一最终 candidate，定向复验；不重开旧 P3。本轮尚未启动 TDD 或代理审查。

## 9. 下一阶段资源上限（提案，非授权）

| 项目 | A：离线接线、清单准备与审查的拟定硬上限 |
| --- | --- |
| 项目命令累计 | 900 秒，包含失败、RED、Conda 启动、原生命令、双轴审查和收尾；其中 180 秒专用于封存／结算，普通阶段最多 720 秒 |
| 累计新增写入 | 256 MiB，含 64 MiB 收尾预留和源文件／文档／Git／临时文件上界；删除不退款，不复制完整候选／参考／旧请求目录 |
| 内存 | 总上限 4 GiB，守护预留 64 MiB；沿用 Windows Job 进程树约束，原生未测峰值不得称全流程实测峰值 |
| 依赖与运行环境 | 新依赖 0；所有项目代码／测试经 `conda run -p D:\Work\Codex\Project\Thesis\.conda\envs\Thesis`，TEMP/TMP 为项目 `.tmp`，包缓存为 `.conda/pkgs`，pip 缓存为 `.cache/pip` |
| API／真实运行 | generate=0、count=0、other=0；不读凭据。仅 PUBLIC 执行／评价夹具，真实 dev/test 均不运行推荐或评价。B 的资源和付费 P1—P3 预算全部待定 |

继承离线原账 `data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl` 当前为 **789.7163418000389 / 1,800 秒**；不得重置。若 A 整包用满 900 秒，总计上界为 1,689.7163418000389 秒；包额与原总额取更严格约束。此算式只是容量检查，剩余不是新授权。上一包 360.3649317 秒余额也不转入本包。

继承累计写入上界 **1,572,133,042 字节**（上一包 resource-closeout），不清零、不退款；新包另列增量。本轮原生准备／文档写入拟在 A 获准后以 30 秒及 1 MiB 保守上界纳入其额度，不能称实测，不能在 A 启动时漏记。

T0 是独立历史账，本轮只读不追加：其当前末行为 `recovery_pilot_G1_005_native_closeout`，累计 **2,127.9285680998332 秒**。迁移交接中的 1,797.3523884 秒是较早快照，不据此重算可用额；旧恢复失败／未接受状态不变，不借其资源。本轮不改任一原账。

| 只读保护锚点 | bytes | SHA256 |
| --- | ---: | --- |
| 离线 resource-ledger.jsonl | 767278 | `4b49b8ede46c80f9b18c2f237d3674b28f45cba1fa7eedc7477e722af6635207` |
| T0 resource-ledger.jsonl | 25417 | `61364efd7e619517c23377d76ee138b9736ea23805cb47cf08e30697265e70ca` |

到包额、总额或预留门即停止普通工作，保留未完成状态；不自动扩额或借款。900 秒只是离线接线提案，不承诺未知供应商实现、真实任务次数、API 价格或实测效果。

## 10. 确认点与本轮自检

请确认本草案的 A 范围、公共测试 Interface、单开发账户 8 任务试点设计、验收／停止规则及 900 秒／256 MiB／4 GiB 的下一阶段提案。确认后再归档正式 spec/confirmation 和工单，开展 A 的 TDD／双轴审查；本草案的确认不填写模型空值、不启动 B 或付费试跑。

本轮自检：只新增本 `draft.md`；生产代码、冻结计划六文件、两份验收、研究稿／论文和两账未改；不运行项目代码／测试／推荐／评价，不调用 API，不读取凭据，不派审查代理。当前只是待确认接入方案，不能写作真实接入通过、预实验完成或正式实验完成。
