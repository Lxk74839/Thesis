# 工单08验收：文本画像输入与A通道试制

2026-10-15。最终规则为preference-task-1.0.1，沿用已确认的text_portrait_trial_v1、finite-text-1.0.0、preference-model-input-1.0.0及api_only_no_host_io_v1。实现冻结于f3adc26ba9a08f7306f1bb990a2f8e66a1d89cc9，Standards／Spec比较起点固定90ecec3c9b7d2edb7a2c9f46aa8b8523dbb6a4c8。

结论：工单08本轮试制及所选API通道验收通过。1,494商品、1,603根任务、320开发／1,283测试、1,845条合格历史正文均完整投影，没有删除账号、历史或候选凑通过，无法构造计数均为0。原稿、研究材料、06／07及其他707项保护文件摘要一致。推荐模型调用0；互动训练、SIM与正式联合实验包均未构建，D10充分性待判定，07未知暴露继续保持未知，不宣称新盲测。

## 批准依据与修订边界

冻结[审核稿C1—C9及6.2／8／9节](ticket08-stage1-field-isolation-review-draft-20261015.md)，SHA-256为21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a；[实施确认](ticket08-implementation-authorization-20261015.md)先于代码提交06cf2b6。真实数据复用已接受的grain-A-1.1.15、review-cleaning-1.0.0、user-split-1.0.0，原文件保持只读。

首轮实现480551b生成1.0.0：独立全量数据、SQL、文本、目标变更、字节复现及保护均通过，但Standards发现失败明细路径可跟随junction写入。行为19的真实CLI RED在项目.tmp夹具中观察到1个额外私有文件，故[首轮不通过](verification/ticket08-first-acceptance.md)，原版本及其拒绝接受清单保留。只使用**一轮**集中修订：将完整失败文件路径交给既有project_path，在创建前检查所有祖先，GREEN确认0个额外文件；提交f3adc26。为避免覆盖升规则1.0.1，复用原私有32字节密钥与批准语义；版本域变化导致根HMAC ID变化，账号资格与组别未变。没有第二轮工程修订；P3重复常量建议留存，不扩大本轮范围。

## C1—C9逐项交付

| 确认项 | 实际结果与证据 |
| --- | --- |
| C1 商品与有限文本合同 | 全1494父商品恰保留parent_asin、处理后title、crop；其他属性及details关闭；采集时平均分、评论数、当前价格及其变换关闭。严格UTF-8、有限HTML／一次实体解码、固定隐私／外链遮罩、全文无截断，独立全行核对通过 |
| C2 历史正文／标题／评分及已见 | 全1845条严格较早合格正文及真实评分保留，5分1651／4分194；历史标题关闭，不拼入正文；合法评分、当时价格、商品名不自动删改。06资格不变，S包含更早低分及空正文等原始互动 |
| C3 背景及训练政策 | 整账号排除全部1603个E及其3490条clean事件，基础池52937事件／51973来源账号；逐T严格截断，最小214／最大52855事件。三个批准计数对全部C逐项SQL对账2393008行；互动训练未启用 |
| C4 候选顺序与完整性 | 全目录P减S，UTF-8父ID字节升序，不采样。每任务1488—1493候选，共2393008引用；零统计商品也完整保留，目标自然在C内，无标记或特殊排序 |
| C5 请求／身份／私有追溯 | 固定无标签试制请求；全64位HMAC与原账号一一核对；密钥、原账号、组别、目标／参考及暴露只在受信任侧。源组件摘要、源行、JSON pointer、原文／输出摘要及阶段编辑位置全行核对。其他候选为unobserved_unlabeled |
| C6 A通道及验收范围 | 真实请求构造器只收到白名单视图，实际消息只有当前user JSON，tools与indices为空。26次探测：1次取得完整实际请求，25次资源、工具、路径、假评价角色、跨会话等挑战一致access_denied；私有哨兵命中0。文本不提升权限 |
| C7 公共Interface／schema／配置输出 | 唯一prepare_data.py新增preference_tasks和已确认参数，配置绑定profile／文本版本／接受链／密钥／合同。临时完整构造后发布；同版本一致复用，损坏或变化拒绝覆盖，文本失败汇总具体影响且不静默删输入，失败无完整成功主记录 |
| C8 公共测试及独立验收 | CLI手算夹具、合法历史信息、目标变更不影响输入、真实权限分派、全行SQL／文本、新空根6组件直接字节比较及真实复用均通过；公共seam不导入生产内部函数 |
| C9 实施流程及停止位置 | Thesis环境，19轮逐行为RED→GREEN、197项回归；固定90ecec3双轴审查0剩余阻塞、唯一集中修订1轮，707保护摘要通过。止于08试制；不调用推荐模型，不进入SIM或正式联合实验 |

API结论仅覆盖实际请求构造与默认拒绝分派，不声称NTFS对当前宿主账号拒读，也未验证未来供应商接入、推荐效果或模型上下文容量。真实模型运行以后必须复用该路径，不得把当前宿主聊天工具、旧索引、旧缓存或评价权限挂接给推荐会话。

## 文本实测与信息损失

| 文本 | 字段数 | 原始码点 | 处理后码点 | 处理后UTF-8字节 | 变化字段 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 商品标题 | 1494 | 104467 | 104443 | 105302 | 6 |
| 合格历史正文 | 1845 | 380217 | 373956 | 374562 | 687 |

标题总计减少24码点，其中仅1条命中批准的满额免运费尾句；其余为文本呈现／空白归一。历史正文减少6261码点，约1.64669%；观察到878个HTML br标签、62个实体形式和1处外链遮罩，其余变化包含空白归一。邮箱、电话和自身原账号在本批真实投影中未命中；这不代表穷尽PII。独立参考对全部标题／正文逐值比对并核查每阶段原文／输出摘要、长度和编辑坐标，未用生产投影函数求期望。参考的实际HTML范围为br，标题字面量<500g>原样保留；复杂HTML由公共手算字符串夹具覆盖，未开发通用文本安全解析器。

冻结草案诊断的历史正文374230码点比实际多274：旧诊断让自闭合br同时触发起止处理、重复产生换行，再经空行归一留下净274个额外LF。本实现及手算公共合同每个br只产生1个LF，独立br替换参考核对通过；未据此修改冻结草案，也未读取目标或删除历史事件。最长正文处理后5705码点，单任务历史总长最高7977码点；无经验长度截断。码点减少是转换规模，不能解释为语义无损率。历史标题关闭的取舍仍遵循批准稿，不开放其他details。

## 组件、接口与复现

当前[版本化规则](../../config/preference-task-1.0.1.json)、[公共接口说明](../../docs/data-sources/preference-tasks.md)、[主记录](../../records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1.json)及同目录acceptance.json保存来源、生产器和组件摘要。模型目录为data/preference-tasks/grain-A-1.1.15/preference-task-1.0.1/model/；私有评价、task-audit和access-probe在同版本private/。私有组件和密钥不入Git，不在聊天或公开报告展示真实逐账号标签。

| 稳定组件 | 读取用途 |
| --- | --- |
| model/catalog.jsonl | 全目录三字段商品投影 |
| model/tasks.jsonl | 根任务、H／S／完整C与逐T三项背景计数 |
| model/manifest.json | 仅模型两个组件名及摘要、schema／文本版本 |
| private/evaluation.jsonl | 原账号、07组别、目标和偏好参考，仅准备／评价 |
| private/task-audit.jsonl | 文本、来源、背景排除和时间证据，仅验收 |
| private/access-probe.jsonl | 真实构造请求及一致拒绝响应，仅验收 |

稳定组件均UTF-8无BOM、显式LF、紧凑键排序JSON；新空output-root与原目录6组件逐字节一致。运行时间等主记录元数据不要求字节相同。实际同目录重跑公共JSON与主记录字节完全相同；原1.0.0主记录和6组件保持原摘要，两配置引用同一冻结密钥。

独立验收脚本[verify_preference08.py](diagnostics/verify_preference08.py)不导入任何生产模块，使用SQL与原始已接受组件计算期望，私有挑战副本位于项目.tmp。它修改一个真实开发目标的父商品、变体、4／5评分、正文和源绑定，固定账号／T／历史／已见／目录／分组／密钥；全部模型组件及实际请求探测字节不变，私有评价确实变化。正式上游写入0，夹具不计真实样本。

在Thesis环境运行该独立脚本可重做全量、字节复现和目标挑战；[verify_preference08_reuse.py](diagnostics/verify_preference08_reuse.py)复查真实同目录复用及旧版字节。项目.tmp中的707项基线保护清单留作本地审计输入；配置中的私有密钥路径必须保留或从原始安全副本恢复，不可重新随机生成冒充同一版本复现。

707项保护基线另冻结私有副本于data/task-inputs/preference-task-1.0.0/protected-baseline-90ecec3.json，摘要由正式接受清单绑定；它与独立验证使用的原.tmp清单字节相同。br诊断差额另有[双LF／单LF实测对账](verification/ticket08-text-diagnostic-reconciliation.json)：1845正文非空白内容差异0，净额外LF为274，未把这一比较解释为原始文本语义无损。

主要证据：

- [TDD逐行为证据](verification/tdd-08.md)；[197项最终回归](verification/ticket08-final-all-regression.txt)，82.034秒。
- [全行SQL／文本／API独立核对](verification/ticket08-1.0.1-independent-full-check.json)；[完整运行日志](verification/ticket08-1.0.1-independent-acceptance-run.txt)。
- [新空根直接字节比较](verification/ticket08-1.0.1-reproduction-check.json)；[私有目标变更不变性](verification/ticket08-1.0.1-target-mutation-check.json)。
- [真实一致复用与旧版保留](verification/ticket08-1.0.1-reuse-check.json)；[707项保护](verification/ticket08-1.0.1-protection-check.json)。
- [两个独立审查汇总](verification/code-review-08.md)：Standards硬违反／阻塞0，P3非阻塞建议1；Spec发现0。实际代码冻结点f3adc26，交付附录仅增加已补审的独立复用检查脚本和验收记录。

本轮止于08批准范围，正式联合包、SIM、推荐模型调用、场景／K／预算及D10充分性等仍由后续工单处理。
