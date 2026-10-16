# 工单12离线公共接口与验收索引

固定审查起点：`7bd12cd`。依据：[授权归档](ticket12-quality-offline-authorization-20261016.md)及原报告第8—9节。本文件解释实际字段，不替代或重新确认实验配置；整个工单12保持打开。

## 实际入口及边界

```powershell
conda run -p .conda/envs/Thesis python prepare_data.py --stage quality_fusion `
  --sim-record records/sim/grain-A-1.1.15-sim-normal-1.0.0.json `
  --quality-config config/quality-fusion-0.1.0.json --output-root .
```

CLI只允许上述三个输入参数；新增配置只绑定获批质量臂。正常、16异常视图、原S、分组、账户与论文不写入。新数据路径为`data/sim-quality/<catalog>/sim-quality-fusion-0.1.0/`；新prepared记录为`records/sim-quality/<catalog>-sim-quality-fusion-0.1.0.json`。独立接受写另一个记录，prepared不改字节。错误另存忽略路径`data/sim-quality/failures/<uuid>/failure.json`，原输出不覆盖。

生成规则、完整配置、输入记录与生产文件摘要均绑定。Q1/Q2有不透明view_id，独立快照绑定六类文件及每父对象完整登记范围摘要；原件按无LF规范JSON核登记摘要，文件按UTF-8/LF核组件摘要。作用域摘要证明这份封存范围的闭合，不代表外部实体签名、真实供应链真实性或已部署账本。分配不读取用户、目标、历史、b或模型输出。

## rank_quality(binding, acquired)

两个参数均为内存对象，返回新字典；不访问宿主文件、网络、参考或其他候选源。

`binding`必需：`schema_version=fusion-binding-0.1.0`、task_id、完整有序C及其SHA-256、H_sha256、同顺序base_scores及版本、`SHA256(canonical(list(zip(C,b))))`、snapshot_id、verify_at_ms、principal_id、contract_sha256、K、alpha、beta、mode、preference。b由调用方按获批完整C归一化后输入，不在此函数读历史或留出标签。preference为`source=experiment_design`、dimensions列表及weights映射；未知维度保留权重、贡献0并给原因。D空或权重总和0贡献0；β为非负有限数，按总和归一化，总和0则q=0并说明。α=1只作为边界。

`acquired`必需：封存snapshot、policy_bytes、actions_bytes；candidates映射中每对象提供完整`registrations`与已取得的`originals={target_id:canonical_bytes}`。完整登记存在不代表原文已取得。未提供对象/原文时不补读；同ID的跨快照旧原文因摘要或快照绑定失配而拒绝。已取得的原件、权限、登记、事件、版本及时间必须匹配；替代/撤销或异常复杂范围不在本正常v1臂内，明确失败关闭，不声称接入16异常生产核验。

结果版本`fusion-score-0.1.0`，包含绑定指纹、逐对象x/z、固定分母C(1)与A(2)、T及原始时间分子分母、q、effective_q、m、软贡献、必要资格、同属性字段引用、原因、G及完整/TopK稳定次序。库存冲突保留Conflict；未取得/未闭合保留Unassessed，不能写成参考Pending。合法在售与检验支持不替代库存原文。A需要到货与其发运依赖；缺件A=0/2，不重分配分母。

模式：full用实际q；no_quality保持资格/m/α/w，令effective_q=z；mean_quality用同完整C中z=1对象的q均值，分母和raw q单独返回。分数舍入12位、父ID UTF-8升序消解同分。纯数学及质量结构的差异不能当推荐效果。

## advance_action(state, event)

版本`collaboration-action-contract-0.1.0`；仅接`fixture=public_deterministic_adapter`，禁止非零模型/输入/输出token/费用额度。init绑定上述FusionBinding与AcquiredScope、mode、同范围槽位清单、根limits、final_reserve、deadline_ms与at_ms。六角色名称保持不变，但不填造六条角色消息。

事件采用`kind/task_id/snapshot_id/role/at_ms`；支持init、acquire、settle、assess_current、submit_draft、verify_draft、revise_and_resubmit、finalize。acquire只提出请求，产生pending与原子预留；公开适配器实际返回原字节后经settle核摘要和槽位、结算，失败不退已消耗额度。assess_current依据实际已取得证据移动固定b队列游标，不能越过尚未完成的当前对象。草案、问题定位、修订old/new、父子草案、计量前后状态均保留。状态摘要防止意外改写控制状态；这是本地一致性检查，不是抵抗恶意调用方重新计算摘要的认证机制。

完整/无反馈/固定使用同合法槽位并集与根预算。固定路由顺序为采样→报告→零售→发运→到货，记录建议与实际槽位；无反馈把Issue保留在受信任审计状态的issues中，给管理者的visible_issues为空，关闭修订及取证旁路。外部未来适配器只能把管理者视图交角色，不能把受信任完整ProtocolState交模型。本轮没有该模型适配器。

根预算维度：model_calls、input_tokens、output_tokens、logical_tools、physical_tools、candidates、elapsed_ms、cost_microusd、retries。初始公开夹具提供每父对象一个胶囊及快照/权限/动作三个胶囊；每返回的登记和原件各计一个逻辑单位，胶囊各计一个物理请求。四对象完整夹具为123逻辑、7物理，不免费隐藏初始依赖。此计量描述公开适配器请求，物理请求不等同操作系统磁盘读取数。后续每原件计逻辑单位，批量不按一次免费，多角色不扩额；submit/verify/patch/assess/final每程序操作计1逻辑单位。此公开fixture预算不是正式方法预算。

时间来自公开事件的单调毫秒时钟；迟到事件保留观察时间和overrun并停止新工作，不能把超限记录清零。它不替代真实模型运行的墙钟测量。保留最终门禁预算；终态区分released、valid_empty、incomplete_budget、incomplete_deadline、failed_protocol、blocked_evidence。共同门禁不自动修改解释或补证，检查整张实际交付及G/排序。正常质量臂无必要否定状态；本轮可公开核对的valid_empty仅是完整C为空，不把正常数据中的未完成空输出当合法空。

## 验证链及保留项

公共TDD：`tests/test_quality_fusion.py`、`tests/test_recommendation_actions.py`；公开原件夹具为`tests/quality_fixtures.py`。RED/GREEN原始结果与资源账在忽略的`data/quality-fusion-audit/20261016/`。相关回归通过后按固定起点双轴独立审查，再独立全量参考、空目录复现、一致复用、上游保护和范围接受。报告中记录实际数量，不以测试方法数替代场景覆盖。

独立参考`verify_quality12_raw.py`仅用标准库，从实际原件/登记/事件/权限/时间重推；先持久化参考再检查分配。`export_quality12_scores.py`单独穿过生产rank接口，只用无账户的合成目录b；`compare_quality12_independent.py`不导入生产函数，逐字段及稳定次序核对。公开原件算例及负例由`verify_quality12_public.py`先验证。不读取私有评价目标或旧诊断答案，不重做320账户/8,320次开发试验。

仍未实现/未接受：16异常视图的生产核验和真实取证适配器、真实六角色及模型效果、账本部署/完整性与审计/延迟/费用实测、13联合包。质量臂纳入正式比较、统计family和模型预算仍待一次决策；D6保持条件近似精度路线，样本充分性待判定。
