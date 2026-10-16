# 离线SIM异常场景组件

工单11获批合同为.scratch/data-preparation/ticket11-stage1-evidence-scenarios-review-draft-20261015.md的J1—J8；授权及原稿摘要先于config/sim-scenarios-1.0.0.json归档。仅构造离线证据视图，不运行推荐模型、账本、用户联合任务或正式统计。

唯一准备入口新增evidence_scenarios阶段，三个参数必填，其他阶段参数拒绝：

    conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python prepare_data.py --stage evidence_scenarios --sim-record records/sim/grain-A-1.1.15-sim-normal-1.0.0.json --scenario-config config/sim-scenarios-1.0.0.json --output-root .

正式正常基准及其接受链只读。sha256-order-v1用NUL分隔固定域、20261015及父商品ID，按摘要字节及父ID取ceil(N/10)；1494商品选150，全部原子视图共享S。错配供体为排序中随后不重叠的150对象。16自包含视图包括12类要求、新版本两方向和3种组合，每视图构造一次，复制行不增加业务身份或独立用户。

R1_SIM_Q1是历史指定采样的SIM-Q1报告pass，正反都要完整采样/对象/项目/时间/授权。R1不设TTL。R1_AND_R5_SIM_Q1_ON_SALE额外要求固定τ=1791417600000有有效on_sale零售记录，区间为[from,to)。零售过期不影响R1。合法supersedes选谱系头；独立谱系相反组合为Conflict；头失效不回退旧pass。仍用8个SIM签发主体、模拟allowlist，无真实密码签名；权限视图只收紧选中报告，不增宽授权。

生产代码仅在sim_scenarios.py实现固定构造和外层发布/复用；复用sim_normal.py已有纯JSON/路径工具，故其源码也列入生产依赖摘要，不用正常核查器判异常状态。新稳定JSONL沿用UTF-8无BOM、紧凑排序键、原件摘要不含LF、文件摘要含全部字节。新增源文件和绑定JSON的精确Git换行规则只作用于本次新路径，使检出后摘要保持可核对，旧规则保留前缀。

产物位于data/sim-scenarios/grain-A-1.1.15/sim-scenarios-1.0.0。各视图含batch/event/material/registration/change-action、policy及snapshot；requests、view-index和事实manifest共享，私有mutation-plan不进入模型或参考。主记录位于records/sim-scenarios；stdout返回同一对象。成功退出0/status=evidence_scenarios_prepared，只代表prepared，接受另写记录。失败退出2，用已批准的稳定原因码，不回显宿主堆栈或私有内容。

包发布完整性与业务可采用性分开：完整文件中可以有拿不到的原文、摘要不符的模拟登记、有效fail或正反冲突；外层文件/hash/schema损坏必须失败，不能映射成Refuted。生成器不计算gold状态。所有正式旧版保持只读；新空根发布，一致输入/代码及输出才复用，否则output_conflict，不覆盖或自动拼接半发布版本。

独立S2不导入生产模块、不读私有计划或生产状态，只读公开原件/登记/动作/策略/请求/快照及基准接受链：

    conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis --no-capture-output python .scratch/data-preparation/diagnostics/verify_sim11.py --record records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0.json --audit-root data/sim-reference/grain-A-1.1.15/sim-scenarios-1.0.0/scenario-reference-1.0.0

审计根必须新鲜且与原件隔离。成功输出私有reference.jsonl/check.json并退出0，表示参考重推完成；存在Pending/Refuted/Conflict不是程序失败。包损坏/不支持的结构退出2，保留失败check，不写完整参考。四态参考及推导只在私有侧，不挂到模型会话。

S1复用时从固定输入重新计算稳定组件摘要，既核对实际文件，也核对固定构造应产生的字节；仅把改动文件与旧清单一起重封不能成为一致复用。S2从已接受正常原件只解析请求指定的事件和采样身份，支持/否定仍全部由当前视图原文推导，不以正常pass结论补证。可读且登记摘要有效的前后版本若显示采样、项目或对象范围改变，替代动作无效；合法头原文缺失、拒读、摘要不符或被撤销时仍不回退。check记录外层完整性和实际拒绝原因，计数单位为逐参考条款的跟踪出现次数，两个请求中的共享条款会分别计数。

相关动作已有受信任接收登记而必要动作原文拿不到时，版本/撤销处理仍未完成；即使当前已见正证也不能提前Supported。明确无效且已处理完成的动作可排除，不能把原文缺失当成没有动作。

额外登记不能替另一签发者取得谱系状态权限，也不能把供体原件引入当前声明；谱系主体/对象必须绑定实际原文，采用时再次检查当前父商品、批次与指定事件。A17的公开合成根任务检查仅演示同根句柄和字段不变性，fixture-only分数、输出规模、版本及预算不作为12的默认参数；真实用户关联和工具执行仍留13。

验收必须包含S1/S2公共测试、全量逐对象构造/47,808参考核对、无关对照逐候选不变、新空根字节复现、一致复用、上游保护、完整回归及固定2e6594e两个独立轴审查。当前是否已接受及实际数量以工单11接受记录为准，不能以本说明代替实际门禁。

2026-10-16已独立接受离线组件：270项回归、47,808参考逐对象、116稳定文件和参考字节复现、一致复用、1,003保护文件及两轴0阻塞全部通过。实际正式bundle为833,833,418字节（约0.777GiB）。见[完整验收索引](../../.scratch/data-preparation/ticket11-acceptance-sim-scenarios-1.0.0.md)及[机器接受记录](../../records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json)。

08根任务、组别、评论归属和工具保持原字节。未来联合引用(root_task_id, scenario_version, snapshot_id, request_profile_id)，同根历史/候选/请求/基础分/预算须一致；实际接入留13。权重、样本充分性、模型及预算留12。本组件不新增真实用户，不宣称现实品质或独立机构佐证。
