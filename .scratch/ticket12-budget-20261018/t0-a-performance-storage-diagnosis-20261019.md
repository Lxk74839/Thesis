# 工单12：T0-A性能与存储止损诊断及最小修复提案

日期：2026-10-19（Asia/Shanghai）。续接基线：`69918e613fd700fd33c53a0ded5557b604487fcc`。**状态：诊断交付完成，R01—R05待集中确认；本文不是正式规格、实施许可、额度追加或A验收。** 原离线批处理、离线模型适配、T0-A程序子项接受全部继承；实际A仍为`T0_A_incomplete`。

推荐先修复已经证实的存储冗余：每个prepared对象只保存一份完整W，逐对象zlib level 1压缩并拼包，按既定mapper规则重建P。先验收存储子项；不把小样压缩率当作全量容量或性能保证，不引入片段仓库或改变请求内容。本包不安排9,600计划重跑、原91.6GB目录转码、缺失计划续编译或全量对象扫描。

## 1. 依据、完成标准和继承状态

已读取AGENTS、三份代理约定、迁移交接、本工单主规格/集中表、各阶段确认和授权、相关接受及T0-A执行记录。迁移和清理按已完成事实继承，没有重做迁移检查。本轮是代码存储诊断，不开展数据规格或新实验；论文、研究材料及既有正式合同保持只读。项目名与环境继续为Thesis，环境位置按迁移交接继承。

已检查会话提供的插件/Skill目录，采用`mattpocock-skills:diagnosing-bugs`与`mattpocock-skills:research`；依后者要求，由后台证据代理整理本地一手资料。本任务不需要外部服务、模型资料更新或新增插件。无`GLOSSARY.md`及`docs/adr/`，按项目约定不补占位文件。

本轮可验证终点：已有测量与未知分开；单W方案的字节/摘要/身份依据可定位；文件、公共测试接口、验收和资源上限明确；待确认项集中。只新建诊断文档，项目Python/测试/诊断重跑/API均为0。后续确认来自本轮用户的明确要求“确认后再进入TDD实施与验收”，不是Skill额外设置的权限门。

主要原件：

| 编号 | 原件及用途 |
| --- | --- |
| E1 | [迁移交接](/D:/Work/Codex/Project/Thesis/docs/operations/project-migration-20261019.md)：继承基线、两账和未完成状态，不重新迁移核验 |
| E2 | [A确认稿](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/t0-a-implementation-confirmation-20261018.md)、[人类授权](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/authorization-t0-a-20261018.md)：原范围、物理格式、公共Seam及A/B共账 |
| E3 | [实际A执行记录](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/verification-t0-a-execution-20261018.md)：已覆盖部分及未完成的复现/交付检查 |
| E4 | [既有诊断证据附件](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/t0-a-existing-evidence-20261019.md)：逐项JSON字段、全部阶段时间、I/O、两种原型及历史计时 |
| E5 | [诊断脚本](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/diagnose_t0_costs.py)、[载荷分析脚本](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py)：复用原反馈与原型定义，本轮只读 |
| E6 | [编译器](/D:/Work/Codex/Project/Thesis/t0_catalog.py:570)、[mapper](/D:/Work/Codex/Project/Thesis/provider_openai.py:141)、[独立检查器](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py:73)：现有实现的一手依据 |
| E7 | [原离线账](/D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl)、[原T0账](/D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/ticket12-t0/resource-ledger.jsonl)、[PUBLIC计划占用](/D:/Work/Codex/Project/Thesis/.tmp/ticket12-t0/diagnosis-20261019/state.json)：沿用原累计，不退还、不补记本轮运行 |

| 继承项 | 实际状态 |
| --- | --- |
| 原目标 / 已列计划 | 9,600 / 2,403；完整2,402、中断1、缺7,197；未完成或缺失共7,198 |
| 原请求N / 唯一对象U | 22,113 / 22,113，无严格对象去重收益 |
| 原引用ΣW / ΣP | 20,673,171,075 / 20,671,424,148 UTF-8字节 |
| 原目录存储 | 91,556,152,080字节、22,125文件；直接引用E3，不重新扫描 |
| 稳定摘要复现 | 原尝试因`complete_original_required`拒绝，未完成 |
| 独立完整交付检查 | 超时，没有完整delivery结果；原收尾只核对清单、集合及字段合计，未重读全部对象正文 |
| 原离线账 | 198条，累计217.7244063001417秒；总额1800秒，余额1582.2755936998583秒 |
| 原T0账 | 4条，累计1797.3523884000024秒；原总额1800秒，余额2.6476115999976173秒 |
| PUBLIC既有计划门 | 原`reserved_plans=12`及四个case原样继承，不能再领12份、删除case或重建样例 |

原代码/合同中的`88e8b80`是当时的A程序审查BASE；本次增量审查起点是`69918e6`。二者不混用，也不批量改写旧记录。

## 2. 已测结果：存储原因已证实，全流程性能尚未定位

诊断流程复用迁移前已经运行过的反馈命令`diagnose_t0_costs.py --case baseline`及repeat/profile/longH日志。它们通过真实`python -m t0_catalog prepare`路径生成PUBLIC目录后核查四份完整表示，记录`RED_repeated_complete_payloads`；191—194的退出1是该反馈信号，不是供应商失败。本轮遵照不重复生成/不动原计划门的要求，跳过重新执行、重新最小化和新探针，使用已留原件评估方案，不宣称已完成修复GREEN。

| 判断 | 证据及边界 |
| --- | --- |
| **已验证：同一对象重复存储完整载荷** | baseline/repeat/profile均为3计划、26对象；W=386,237B、P=384,183B，却写1,710,684B对象文件。每个对象含`wire_body/count_body/wire_utf8/count_utf8`四份完整表示；两份冗余纯载荷合计770,420B。外层JSON还需要转义已序列化字符串，最终文件不是恰好四倍。（E4§1） |
| **已验证：P高度复用W内容** | 当前mapper仅从W删除四个顶层字段得到P；消息、历史、工具与角色schema均相同。样本逐字节验证了这一关系，不需要持久化第二份完整P。（E4§4、E6） |
| **已验证：历史增长会扩大这组载荷** | longH对象总量3,861,096B，W/P分别923,837/921,783B；该实验追加高度重复的PUBLIC文本，仅说明表示膨胀及可压缩，不能代表真实历史分布。（E4§1） |
| **已测：文件数量有局部I/O成本** | v2固定1,710,684B、26文件/单包各3次，中位0.0097964/0.0006488秒；无fsync，固定预编码字节。第一版方向一致，详见附件。支持小样打包有收益，不能定位原A主瓶颈。（E4§3） |
| **已测：重复序列化有成本** | 三件原对象W/P序列化中位约0.00488/0.02472/0.01853秒，完整外层序列化约0.01137/0.05402/0.04289秒；不是原A端到端剖析。（E4§5） |
| **尚未验证：性能主因及修复后吞吐** | profile/longH插桩总时间2.153809/2.101121秒，回调开销达1.497762/1.548769秒；file_write反而是较大longH更短。无法据此排序全量磁盘、JSON/copy、trace重绑定或依赖计算的实际贡献。（E4§2） |
| **尚未验证：规模增长后的资源** | 原A后段复杂度、完整新目录大小、持续写入、压缩后整体时间及峰值内存均无总体测量。不得由小样压缩率乘91.6GB，或按已列计划线性预测剩余时间。 |

需要保留的不同假设是：重复持久化直接造成字节膨胀（已证实）；大量文件放大I/O（仅局部成立）；序列化/copy/重绑定或依赖计算主导全程（未证实）；规模、缓存和设备负载改变阶段比例（未证实）。本轮没有为这些未知再跑实验。

## 3. 单份完整W压缩方案的证据、规则与局限

### 3.1 既有原型实际证明了什么

原件：[whole-W-controls.json](/D:/Work/Codex/Project/Thesis/.tmp/ticket12-t0/diagnosis-20261019/whole-W-controls.json)。各对象完整W分别执行`zlib.compress(W, 1)`，压缩段顺序拼入`requests.pack`；manifest保存每段offset、压缩bytes、raw_bytes与原metadata，以及pack SHA。**没有长度前缀，也没有跨对象片段去重。**

| 已测组 | 对象 | 原对象字节 | 单W压缩pack+manifest字节 | 核验范围 |
| --- | ---: | ---: | ---: | --- |
| PUBLIC baseline | 26 | 1,710,684 | 110,485 | 两文件落盘重读，W/P字节、SHA及prepared_id全部一致 |
| PUBLIC longH | 26 | 3,861,096 | 117,607 | 同上 |
| 原A首条轨迹三件对象 | 3 | 22,234,142 | 739,480 | 只在内存往返，未落盘验证 |

这些数字只统计对象pack和manifest，不含roots/requests/dependencies、来源索引、probe、coverage和审计。片段方案对应为121,558/125,178/739,759B；在这组对象上没有显示出值得增加片段管理复杂度的存储优势。（E4§4）

PUBLIC两组编码压缩约0.003807/0.002672秒，重建核验约0.011386/0.023633秒；三件原对象约0.020957/0.175067秒。它们不是替换生产writer后的端到端性能对照，核验路径也不同于片段原型，不能据此承诺提速倍数。

### 3.2 推荐的固定语义

1. 原生`ModelAdapter.prepare`及`openai-prepared-0.1.0`保持；只替换目录存储。保存prepare已经给出的完整canonical `wire_utf8`原字节，不重新摘要消息、不删历史、不合并角色或不同请求，不省略工具结果。
2. 对W逐对象独立压缩，使用现有原型的offset/bytes索引拼包方式。metadata保留原prepared字段中除四份完整正文表示以外的内容，包括source、模型/mapper、项目命名空间、工具/角色摘要、`catalog_metadata.tool_versions`和角色schema生成器指纹。精确P字节量另记，不用压缩大小替代W/P统计。
3. 解压得到W后，以现有canonical规则解析并生成P：只删除顶层`max_output_tokens, service_tier, store, stream`。规则固定版本，绑定现有`openai-responses-mapper-0.1.0`；遇未知mapper/投影版本拒绝。不可从文件自带的任意omit列表决定删除字段。
4. 重建`wire_body/count_body/wire_utf8/count_utf8`后，对照原W/P SHA及字节量。`prepared_id`仍由`wire_sha256,count_payload_sha256,mapper_version,tool_schema_sha256,role_schema_sha256,project_id`六字段的canonical摘要计算，不纳入压缩offset或物理路径。
5. N仍保留所有原请求引用，U仅按原prepared_id严格去重；相同ID重复加入必须核对绑定，不能丢attempt/source。修改W、输出cap、模型、工具/角色schema或项目绑定仍按原合同重新prepare，不能利用P偶然相同复用旧身份或回执。

canonical固定`ensure_ascii=False,sort_keys=True,separators=(',', ':'),allow_nan=False`，保留数组顺序、字符串、Unicode及换行。压缩包、manifest及catalog外层摘要会改变；不能宣称与旧0.1目录物理摘要一致。同输入的新格式稳定摘要另行比较，记录Python及编译/运行zlib版本，不能承诺跨codec版本压缩字节一致。

### 3.3 证据不能支持的结论

- 三件原对象来自首条轨迹，不是随机或最坏样本；其原component SHA匹配、读取前后size/mtime一致，只证明这三件原件的对应关系。当前whole-W JSON没有完整枚举它们的ID/摘要；后续验证须按同一有界选择器固定清单并保存绑定，不能把现有布尔结果当作全体证书。
- prepared_id重算验证了六字段的自洽，不能单靠该重算证明元数据出处或逻辑工具schema的全部正文。独立检查仍须核对原component绑定、schema/版本及来源；旧全范围检查并未完成。
- PUBLIC已落盘往返不等于生产读写器、独立检查器或开发原件落盘流程已接受。损坏段、索引错误、partial关闭及资源中断行为仍需TDD。
- 当前项目命名空间是`UNBOUND-T0-DEV-CATALOG`；换真实供应商项目时prepared_id会变化，后续C仍需另行授权和转换。存储压缩不减少W的实际上传字节、token、供应商调用数或费用，不补齐官方计数。

## 4. 待确认的实施范围与公共接口

推荐新产物采用`T0-request-catalog-0.2.0`，对象存储为`T0-single-W-store-0.1.0`：`objects/requests.pack`与`objects/manifest.json`替代逐个对象JSON；保留根/请求/依赖/coverage的语义和未知值。manifest使用上述原型的记录布局，增加正式schema/固定投影/codec版本及必要摘要；这部分新增封装仍须验收，不能称原型已经验证最终正式格式。

CLI仍是目录准备入口`python -m t0_catalog prepare ...`及原`--recompute-digests`，新输出格式必须显式绑定新合同和新程序接受；旧0.1目录只读可识别，不原地升级。原开发授权有硬编码合同/确认/接受SHA及源码指纹，改代码后必须继续拒绝旧授权，不能拿原A01—A08为新存储格式背书。新格式的开发准备授权本包不签发。

为在不再生成PUBLIC计划的条件下测试真实存储边界，建议增加同模块内的窄公共Seam：`PreparedObjectWriter(output_dir).add(prepared)`及关闭操作，和`iter_prepared_objects(output_dir)`。它们只消费/还原已prepare对象，不定位开发根、不展开轨迹、不调用模型。目录编译器使用同一writer；独立检查器自行解码，不导入生产代码。此Seam是对原“生产函数留在Module内部、只测CLI”约束的明确增量，须由R02确认后实施，不通过测试私有helper绕行。

| 必要文件（均位于本项目） | 确认后的最小改动 |
| --- | --- |
| [t0_catalog.py](/D:/Work/Codex/Project/Thesis/t0_catalog.py) | 单W writer/reader及新存储Seam；接入现有输出/摘要重算与partial关闭；版本和新接受绑定。源选择、轨迹、组合、预算候选及mapper不改 |
| [tests/test_t0_catalog.py](/D:/Work/Codex/Project/Thesis/tests/test_t0_catalog.py) | 仅新增存储行为并调整直接读取旧objects路径的相关断言；用既有PUBLIC对象测试新Seam。其余已接受测试不重跑、不顺带重构 |
| [check_t0_catalog_delivery.py](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/check_t0_catalog_delivery.py) | 独立识别旧/新格式、校验pack/索引及W/P身份；新增`check-objects`操作，仅出`object_store_verified_only`，不把抽样当完整A交付。原`check`覆盖门保持 |
| [run_check.py](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/run_check.py) | 仅增加本修复文件指纹、经确认的累计限额扩展读取与本包时间/磁盘门。旧账逐行保留；不允许任意CLI/env扩大LIMIT |
| [analyze_t0_payloads.py](/D:/Work/Codex/Project/Thesis/.scratch/ticket12-budget-20261018/diagnostics/analyze_t0_payloads.py) | 复用既有单W原型及三件选择规则，增加受本包授权约束的有界落盘验证模式，使用生产writer及独立`check-objects`；不再调用旧生成/profile/I/O模式 |
| 本工单新增授权、TDD、双轴审查、子项验收记录；原T0账根内新增额度扩展记录 | 仅确认后新增；旧规格、确认、接受、执行记录不回写。两份既有诊断脚本先归档当前字节/SHA；不把新归档反称历史守护已绑定 |
| 新输出目录 | PUBLIC在`.tmp/ticket12-t0/storage-repair-20261019/`；三件开发对象在`data/ticket12-t0/storage-repair-validation-20261019/`；正文、pack及宿主关联不进Git，旧诊断目录只读 |

`diagnose_t0_costs.py`本轮及本修复包只复用定义/原件，不重跑或修改；实现无需新增第三方依赖或通用存储框架。`provider_openai.py/model_adapter.py/recommendation_runner.py/evidence_access.py/token_counting.py`、全部上游/配置/环境、业务算法、论文和旧接受保持只读。发现还需修改这些文件时，先交付具体合同缺口，不能静默扩范围。

## 5. 公共行为测试与验收条件

确认后按`mattpocock-skills:tdd`一次一个公共行为RED→最小GREEN，已有满足行为如实记首次GREEN。使用原baseline/longH的已落盘对象作为输入；复制、损坏测试输出不增加根计划，不能删除`state.json`或重新调用fixture/prepare生成样例。存储Seam是本次缺陷的直接边界，不测私有hash/parser helper。

| 顺序 / 公共接口 | 验收条件 |
| --- | --- |
| 1 新writer→reader | 对两套既有PUBLIC对象分别逐件保存/重读；W、P与原件逐字节相同，原W/P字节量、SHA、六字段prepared_id、metadata及source均一致；物理只存一份完整W，P按固定规则重建 |
| 2 writer及输出文件 | 每套`pack+manifest`不超过对应旧对象总字节的10%；这是对两套冻结PUBLIC原件的止损目标，依据已有约6.5%/3.0%结果留封装余量，不是总体保证。roots/requests等另报，不把它们排除后称完整目录压缩率 |
| 3 writer重复引用与绑定 | 相同prepared只存一段，所有原引用及source不丢；改变cap或绑定不得合并。沿用原26/26的实际N/U，不归一化ID取巧 |
| 4 reader + 独立`check-objects` | 新/旧格式都能识别；坏pack SHA、截断段、重复ID、越界/重叠索引、错误长度、错误投影/mapper、W/P/身份不符必须非成功退出并留原因；只按受支持固定规则派生P |
| 5 关闭、中断、超限 | writer按对象有界处理，不汇总全部W/P进内存；停写后保存可定位的partial及已完成记录。正常body界限仍16MiB；超界不能截断凑通过，保完整失败原件或明确记录因磁盘门无法保存，不能伪称正文完整 |
| 6 确定性 | 同一冻结PUBLIC输入两次经存储Seam写入不同新子目录，稳定pack/manifest摘要一致；不展开新根计划。时间/运行审计不进入稳定内容；每次失败与尝试仍累计计时/磁盘 |
| 7 直接受影响的旧门 | 选最小现有用例确认prepare-only不可invoke、原count CLI仍拒绝未登记目录；新存储格式不能取得发送资格。无真实counter/sender/credential访问 |
| 8 三件既有开发对象的有界落盘 | 仅R05批准后执行§6的选择/读取/落盘/独立检查；对三件逐字节、摘要、身份及原件保护全通过，新输出记录确切ID和component SHA。只可接受这三件存储往返，不接受9,600目录或剩余7,198计划 |

组件摘要应同时核对物理pack/manifest与重建后的W/P语义摘要。重建/解压按声明长度与16MiB正常body界限有界读取，拒绝错误索引，不能先无限解压再检查；超界失败原件与可用prepared分别记录。独立`check`仍要求完整根覆盖、全部对象、来源、保护及稳定复现，不能因为`check-objects`退出0就放宽。

实现后固定candidate，以`69918e6...candidate`做独立Standards/Spec双轴增量审查，原报告保留；阻塞修复按公共失败→最小修复→定向复验→固定新candidate复审。只审存储、守护、检查及授权增量，继承旧模块接受。不借复审重跑已接受全库/4、12、64组合/13公开组合/上游生成。

本包验收终态建议为`T0_A_storage_component_verified_only`。它不构成新格式prepare全链路或实际开发目录完整验收；本包没有运行新目录prepare及真实轨迹展开，相关端到端证据仍待后续受控方案。原A复现/完整交付的未完成事实继续保留。

## 6. 后续执行包的时间、磁盘与停止上限（全部待确认）

| 项目 | 推荐硬上限与账务 |
| --- | --- |
| 离线实施/TDD/必要回归及验收命令 | 原离线账内本包累计≤300秒，含失败、启动、子进程和检查；不增加原1800秒总额。若用满，本账累计≤517.7244063001417秒。每次取实际原累计，遇inflight未结先停 |
| 新增T0额度 | **仅申请+60秒**，用于已有三件开发对象的落盘及独立核验；未确认时仍是1800秒和2.6476115999976173秒余额。不得先跑再补授权 |
| 批准后的原T0总额 | 同一账由1800增至1860秒，历史1797.3523884000024秒不动。理论共同余额62.6476115999976秒；本修复验证包自身累计≤60秒，失败/重试/收尾共用，不能每次重领60秒。其余阶段不因此取得执行许可 |
| 内存 | 两域仍为Windows Job进程树4GiB，含64MiB守护预留；零新依赖 |
| 新增磁盘 | 本包所有新PUBLIC/开发验证/测试副本/staging/日志/审计合计≤256MiB（268,435,456B），其中8MiB留收尾，数据写入门≤248MiB。跨两域、目录及失败累计；本包内删除产物不退还写入额度，不复制91.6GB目录 |
| PUBLIC计划 | **新增0**。原12份占用保持；仅重写既有prepared对象、损坏副本及存储重现，不展开根/轨迹或生成新事实样例 |
| 开发验证读范围 | 原requests只读首条S/M轨迹前缀，至首个final即停，最多17行且≤1MiB；选择首个analysis、final前最后一个acquire、该final，共3件。只读取它们及必要catalog元数据，总读取≤64MiB，其中三件原对象合计≤24MiB，逐件一次读入复用，不枚举objects目录；大小/绑定不符即停，不另选样本 |
| 收尾 | 离线本包预留15秒、T0验证包预留10秒，均在各自上限内；达门停止启动新工作并保存partial，不用包装器退出0代替子检查成功 |
| 外部与其它阶段 | count/generate/other供应商API=0；C/B/P1、9,600全量重跑、原大目录转码/扫描、缺计划继续生成均为0 |

磁盘门须在写入pack/metadata及测试大副本前核对预算，日志有独立收尾预留；guard监控不能替代写入前门。额度用不可变人类确认记录及SHA绑定，在**原T0账根**新增一份扩展记录（基础1800、追加60、有效总额1860、用途、基线、确认SHA），守护读取后才能启用；旧ledger行及原`limit_seconds=1800`历史字段不改。不得开放任意`--limit`或环境变量扩额，不建立另一本“新T0账”。

三件原件既有总量22,234,142B、小样核验小于1秒，支持把60秒作为有宽裕的停止上限；它不是完成保证或全A时间估计。读取/绑定、运行器保护或磁盘门若无法在此包内闭合，保留失败并报告，不能从离线账挪用真实开发验证时间。

本包不承诺补齐A。完整A仍须另交付能复用原部分成果的受控恢复方案，解决最后中断计划、对象与来源完整性、稳定复现和资源问题；不能把本次+60秒当作恢复/全量执行许可。现有token、费用、自然运行和总体充分性未知继续保留。

## 7. 一次集中确认表及推荐选择

| ID | 需确认的具体内容 | 确认后的边界 |
| --- | --- | --- |
| R01 存储合同 | §3、§4单W独立压缩拼包，固定四字段投影，新catalog/store版本及完整metadata/身份不变量 | 仅改变目录物理表示；旧目录/旧接受只读，mapper和请求内容保持 |
| R02 公共接口 | 确认窄存储writer/iterator公共Seam与检查器`check-objects`；CLI仍为目录准备入口 | 明确修订原CLI-only测试边界；对象子项结果不能冒充完整A，旧count/invoke门保持 |
| R03 实施范围 | §4精确白名单、§5逐行为TDD及以69918e6为BASE的独立双轴审查 | 原接受继承，只运行新增/直接影响的必要行为；本包只验收存储组件 |
| R04 本地资源与PUBLIC复用 | 原离线账本包≤300秒、4GiB、跨域新增磁盘≤256MiB；PUBLIC新计划0 | 沿用实际累计，不复算/重领原12份，不重跑生成/profile/I/O诊断；两份脚本原字节先归档 |
| R05 仅三件开发验证 | 原T0账明确追加60秒，总额1860；验证包≤60秒，按§6有界读取和落盘；新授权及扩展记录先归档 | 此项未确认绝不追加/运行；先程序TDD和双轴审查无阻塞，再依据同次确认直接做三件核验，无需重复索取同一许可。没有全量A、续编译、C/B/P1/API授权 |

**推荐一次确认R01—R05这一有限修复包。** 若不确认R05，保持原T0额度和未完成状态，只能做已确认范围内的离线存储修复，不能用那2.65秒尝试真实开发验收。无需确认论文/六角色/原数据范围等已接受事项，也不申请正式费用或预算冻结。

## 8. 本轮交付自检

- 已按四项要求给出结果分级、最小方案及一致性局限、文件/公共接口/验收、时间/磁盘及一次确认表；证据详表另附。
- 只新增本提案、证据附件及交付核对记录；生产、测试、两份诊断脚本、旧规格/确认/接受/执行记录没有修改。未提交Git或变更工单12状态。
- 项目Python/测试/诊断脚本执行、样例生成、原大目录扫描、供应商API均为0；没有清零、追加、重复计时或重跑全量。原状态保持`T0_A_incomplete`。
- 写交付前后对17个重点文件作摘要核对，含核心实现、两份诊断脚本、原A合同/授权/执行记录、两本资源账及PUBLIC state；结果保存于同目录的交付核对JSON。这是文档只读保护，不能代替原A未完成的全量保护/交付检查。
