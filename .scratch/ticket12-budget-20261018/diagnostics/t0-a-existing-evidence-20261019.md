# T0-A 既有诊断证据研究说明

日期：2026-10-19（Asia/Shanghai）。本附件只整理迁移前已存在的一手证据，供本轮诊断与修复方案审阅；不是批准规格、额度追加、生产实施或验收。继承基线 `69918e6`、原接受记录及 `T0_A_incomplete`。本次只读取既有 JSON、日志、脚本和原账，并写本附件；没有执行 Python、测试、诊断脚本、供应商 API 或重新生成样例，也没有遍历 91.6 GB 原目录。迁移和清理已经完成，无须重新验证。

## 证据索引与记号

以下 `D/` 指 `.tmp/ticket12-t0/diagnosis-20261019/`，`S/` 指 `.scratch/ticket12-budget-20261018/diagnostics/`。每项结论后的路径与 JSON 字段是原件定位，表内数值作有限小数显示，原件保存完整精度。JSON 的 stdout 镜像已读取，但不作为独立重复实验。

- 目录编译、四个 PUBLIC 情形：`D/baseline-result.json`、`repeat-result.json`、`profile-result.json`、`longH-result.json`；对应 `*-cli.txt`。
- 分阶段：`D/profile-stages.json`、`longH-stages.json`；定义见 `S/diagnose_t0_costs.py::Stages`。
- 载荷、片段原型、重复控制、三件原对象：`D/payload-analysis.json`；定义见 `S/analyze_t0_payloads.py::{worker,compact,verify,benchmark}`。
- 同字节 I/O：`D/io-controls.json`、`io-controls-v2.json`；当前脚本的修正控制为 `S/analyze_t0_payloads.py::io_controls`，只写 v2 输出。
- 完整 W 原型：`D/whole-W-controls.json`、`PUBLIC-whole-W-baseline/manifest.json`；定义见 `S/analyze_t0_payloads.py::whole_wire`。
- PUBLIC 计划门：`D/state.json`；实际计时归属：`data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl`。
- 原 A 状态与已有大目录统计：`.scratch/ticket12-budget-20261018/verification-t0-a-execution-20261018.md`；迁移交接：`docs/operations/project-migration-20261019.md`。本附件引用这些已有统计，没有重新扫描或重算覆盖。

`W` 是原供应商完整请求的 canonical UTF-8 字节；`P` 是原计数请求的 canonical UTF-8 字节。诊断脚本的 `raw` 使用 `ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False`。字节量不能换算 token 或证明模型容量。

## 1. 文件膨胀：已经验证的事实

| 情形 | plans / N / U | W 字节 | P 字节 | 对象文件总字节 | 文件 / (W+P) |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline | 3 / 26 / 26 | 386,237 | 384,183 | 1,710,684 | 2.220456 |
| repeat | 3 / 26 / 26 | 386,237 | 384,183 | 1,710,684 | 2.220456 |
| profile | 3 / 26 / 26 | 386,237 | 384,183 | 1,710,684 | 2.220456 |
| longH | 3 / 26 / 26 | 923,837 | 921,783 | 3,861,096 | 2.092032 |

原件：四份 `D/*-result.json` 的 `plans,N,U,wire_bytes,payload_bytes,object_file_bytes,storage_over_W_plus_P`。CLI 四份日志均为 `status=PUBLIC_synthetic_catalog_prepared_only`，`provider_api_calls={count:0,generate:0,other:0}`；`complete=true` 仅指这三个 PUBLIC 声明计划，不能用来接受原 A。

**已验证的膨胀原因：**每个对象同时保存 `wire_body`、`count_body`、`wire_utf8`、`count_utf8` 四份完整表示。`S/diagnose_t0_costs.py::observe` 对每个已测对象断言 `raw(wire_body)==wire_utf8.encode()`、`raw(count_body)==count_utf8.encode()`，并返回 `full_W_P_representations_per_object=[4]`。其中两份重复表示的纯载荷量为 baseline 770,420 B、longH 1,845,620 B（`redundant_full_representation_bytes`），这是 `W+P` 的重复份额，不含外层 JSON 转义及元数据。因此“四份完整表示”不能直接解释为最终文件恰好四倍。

**同一 PUBLIC 运行内没有严格摘要去重收益：**`D/payload-analysis.json::within_run_identity` 为 `N=U=26,unique_wire_sha256=26,unique_count_sha256=26`；没有做正文归一化或合并不同身份。原 A 的 `N=U=22,113` 属于既有执行记录，不能据此把近似正文当作重复请求。（原件：同 JSON 与原 A 执行记录“请求、字节与实际取证”。）

**历史长度会扩大已测载荷与文件：**longH 只在 PUBLIC 历史首项追加固定重复文本并重算 `H_sha256`，其他运行仍为三个 PUBLIC 计划；W/P 与对象文件均增加。该文本高度重复，适用于证明表示冗余和可无损压缩，不能代表真实历史的压缩率分布。（原件：`S/diagnose_t0_costs.py::fixture`；上述四份结果。）

## 2. 重复控制与分阶段性能：已测但不能外推的结果

baseline 与 repeat 的外层 CLI 时间分别为 0.482364200 s、0.227218500 s；profile 为 2.228583400 s、longH 为 2.346718600 s。（`D/*-result.json::cli_seconds`。）`D/payload-analysis.json::repeat_binding` 同时验证 repeat/profile 相对 baseline 的 `same_prepared_ids=true,same_object_file_bytes=true`。baseline/repeat/profile CLI 的 `catalog_sha256` 均为 `901c13945cbfaa8d839badfb6dfdfdd72d2c850e1926ad37d3e4cd053f6e9040`；longH 为另一个摘要。（对应 `*-cli.txt`。）这说明重复 PUBLIC 输入可重现原对象字节，不说明系统已经提速；baseline/repeat 仅各一次，也没有控制缓存、磁盘负荷或启动差异。

以下阶段只对 profile（与 baseline 同输入）和 longH 有插桩。没有无插桩 baseline 的同口径阶段时间，不能补填或推测。

| JSON `exclusive_seconds` 字段 | profile 秒 | longH 秒 | 两情形 entry_calls |
| --- | ---: | ---: | ---: |
| `dependency_probe` | 0.033631099 | 0.037792098 | 3 |
| `message_compose` | 0.004516200 | 0.005169000 | 20 |
| `serialization` | 0.028062601 | 0.043678101 | 2,120 |
| `digest` | 0.003820600 | 0.006076801 | 868 |
| `adapter_mapping_copy` | 0.117961704 | 0.124071795 | 52 |
| `trace_rebind_plan` | 0.079326296 | 0.082009099 | 7,904 |
| `file_write` | 0.212770000 | 0.068142800 | 140 |
| `other` | 0.175949601 | 0.185403500 | 无独立 entry_calls |
| `callback_overhead_seconds`（不计入上列独占阶段） | 1.497761800 | 1.548768605 | 不适用 |
| `instrumented_cli_seconds` | 2.153809200 | 2.101120800 | 不适用 |

原件：`D/profile-stages.json`、`D/longH-stages.json` 的同名字段；`accounting=exclusive wall; nested recognized phases override their caller; callback overhead excluded`。

解释与限制：

- 阶段是诊断 `sys.setprofile` 的嵌套独占归因，深层被识别的序列化、摘要、写操作从调用者阶段扣出；`adapter_mapping_copy` 不是完整 prepare 总耗时，`dependency_probe` 不是供应商 API。`file_write` 是脚本识别的写入、打开/关闭等调用墙钟，不是物理落盘带宽测量。（`S/diagnose_t0_costs.py::Stages`。）
- 插桩回调开销本身约 1.50–1.55 s，超过这里任一业务阶段；不能将 profile/longH 总秒数当作无插桩运行速度，也不能把其阶段占比直接套到原 A。`other` 混合了未识别活动；诊断的写门等包装也可能增加开销。（同脚本及上述字段。）
- longH 比 profile 文件更大，但已测 `file_write` 反而更短，说明这组单次测量不足以识别稳定的规模规律；不能声称长历史导致磁盘主瓶颈。（两个 stages 原件。）
- 原 A 全量的阶段耗时、热点随对象/计划增长是否恶化、后段压缩率、真实存储设备上的持续写入和 fsync、压缩后端到端时间与峰值内存，均未完成验证。本附件不提出“已定位唯一性能根因”。

## 3. I/O 对照：文件数量确有成本，主瓶颈尚无结论

两个已有控制均固定 26 个原 PUBLIC 对象的预编码字节，总量 1,710,684 B，每种写法各三次；比较 26 个文件、一个 pack、内存写入，并验证 pack 拆分后的原字节一致。无序列化变量、无 fsync。（`D/io-controls*.json::{objects,identical_total_bytes,new_plans,packing_round_trip_bytes_match,semantics,seconds}`；当前 `S/analyze_t0_payloads.py::io_controls` 对 v2 三轮旋转操作顺序。）

| 原件 | 26 文件中位秒 | 一个 pack 中位秒 | 内存中位秒 |
| --- | ---: | ---: | ---: |
| `D/io-controls.json` | 0.010491800 | 0.000752900 | 0.000002700 |
| `D/io-controls-v2.json` | 0.009796400 | 0.000648800 | 0.000308200 |

第一版与 v2 是两次既有运行，不能把 stdout 镜像再算一次，也不能用当前脚本推断第一版未记录的完整操作顺序。它们支持“此小样中减少文件数量可降低 buffered open/write/close 时间”。两次内存结果差异较大，且样本只有三次、没有持久化屏障、没有大数据集持续写入或原 A 阶段对照；这些结果不证明原 A 91.6 GB 的慢主要由文件数量或硬盘决定。（上述 JSON `seconds.*.samples`、`semantics`。）

## 4. 完整 W 压缩与按规则派生 P：现有一致性证据

### 已有 whole-W 原型的实际布局

原型对每个对象的完整 `wire_utf8.encode()` 独立执行 `zlib.compress(body,1)`，把各段压缩字节依次拼到 `requests.pack`；`manifest.json::records[]` 为每段保存 `offset`、压缩段 `bytes`、未压缩 `raw_bytes` 与原对象 `metadata`，manifest 另保存 `pack_sha256`、`count_omit`、`codec=zlib-level1`。这不是整个 pack 一次性压缩，也没有跨对象片段去重。**pack 内没有长度前缀；长度由 manifest 的 bytes 与 offset 指定。**不能将它描述为已验证的长度前缀格式或独立 `.zlib` 多文件实现。（`S/analyze_t0_payloads.py::whole_wire`；`D/PUBLIC-whole-W-baseline/manifest.json`。）

PUBLIC baseline 和 longH 各落盘两个文件 `requests.pack`、`manifest.json` 并重新读回；three_existing 只构建内存 pack/manifest，没有将原真实对象重新落盘。manifest 明确 `schema_version=DIAGNOSTIC-whole-W-pack-0.1.0,provenance=diagnostic_only_not_accepted`。（同脚本；`D/whole-W-controls.json::groups.*.persisted`。）

### 字节、摘要、身份往返结果

| `groups` | 对象数 | 原对象文件字节 | pack+manifest 字节 | 编码压缩秒 | 重建核验秒 | 是否重读落盘文件 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline` | 26 | 1,710,684 | 110,485 | 0.003806700 | 0.011385900 | 是 |
| `longH` | 26 | 3,861,096 | 117,607 | 0.002672100 | 0.023633000 | 是 |
| `three_existing` | 3 | 22,234,142 | 739,480 | 0.020957000 | 0.175067000 | 否，仅内存 |

原件：`D/whole-W-controls.json::groups.*.{objects,legacy_object_bytes,pack_and_manifest_bytes,encode_compress_seconds,rebuild_verify_seconds,persisted,W_P_bytes_sha_and_prepared_ids_match}`。三组最后一项均为 `true`；`new_plans=0`。这里 byte 数只含原型 pack 与 manifest，不含目录总账、索引、catalog、coverage 或日志，不能当作修复后完整目录字节。

脚本的核验逻辑具体是：

1. 先核对 pack 的 SHA256，再按 offset/bytes 解压每个完整 W，核对 raw_bytes、原 `wire_utf8` 的逐字节相等及 `wire_sha256`。
2. `P = raw({k:v for k,v in json.loads(W).items() if k not in OMIT})`；固定顶层删除集为 `max_output_tokens,service_tier,store,stream`。不裁剪 input、角色消息、历史、工具定义或 schema。重建 P 与原 `count_utf8` 逐字节相等，再核对 `count_payload_sha256`。
3. 使用原 metadata 的 `wire_sha256,count_payload_sha256,mapper_version,tool_schema_sha256,role_schema_sha256,project_id` 六字段，按原 canonical 规则计算 SHA256，与原 `prepared_id` 比较。它证明存储表示改变后这六字段身份仍一致；不证明外层 pack/catalog 摘要保持不变。（`S/analyze_t0_payloads.py::whole_wire`。）

### 与片段原型比较

另一已有原型按字段/完整 input item 制作内容寻址片段再压缩。`D/payload-analysis.json::public` 中 baseline 为 121,558 B、longH 为 125,178 B；各自 `round_trip` 验证 26 个对象、`W_P_bytes_and_sha_match=true,prepared_ids_match=true`。三件原对象合并为 739,759 B，`three_existing_objects_combined.round_trip.verified_objects=3`；只在内存核验。（同 JSON 及 `S/analyze_t0_payloads.py::{compact,verify}`。）

相同已测对象上，完整 W 原型的最终字节没有劣于更复杂的片段原型。因此现有证据支持优先评估“每对象保存一份完整 W、压缩、固定投影重建 P”的简单存储方向，不支持为本轮引入片段仓库、跨对象合并或改变请求身份。两套重建时间的实现路径不同，不能把其秒数差异当作严格算法对比，更不能承诺生产提速。

## 5. 三件原对象的真实性与范围边界

`payload-analysis` 从原 `requests.jsonl` 首条 trace 附近选择首个 analysis、到首个 final_submit 前最后一个 acquire 和首个 final_submit；不是随机样本、最坏对象或全体对象。三个原文件通过原 catalog 的 component SHA256，读取前后文件大小和 mtime 均不变。（`S/analyze_t0_payloads.py::worker`；`D/payload-analysis.json::existing_object_samples[*].{kind,component_sha_matched,size_and_mtime_unchanged}`。）

| kind | 原文件字节 | W 字节 | P 字节 | W/P 序列化中位秒 | 外层完整对象序列化中位秒 | W/P SHA中位秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| analysis | 2,579,600 | 602,440 | 602,361 | 0.004880600 | 0.011373500 | 0.000487500 |
| acquire_after_read | 10,949,991 | 2,529,048 | 2,528,969 | 0.024718300 | 0.054022400 | 0.002004400 |
| final_submit | 8,704,551 | 2,021,687 | 2,021,608 | 0.018533600 | 0.042890800 | 0.001587100 |

原件：`D/payload-analysis.json::existing_object_samples[*].{legacy_file_bytes,microbenchmark.{W_bytes,P_bytes,serialize_W_P_seconds.median,serialize_full_envelope_seconds.median,sha_W_P_seconds.median}}`；各微基准 `repeats=3`。原样本只读核验与 fragment 原型往返均成功；没有把压缩副本写回原目录。样本表明重复完整对象序列化具有可测成本，但不是原 A 的端到端热点证明。

尚未验证：完整生产 reader/writer/独立检查器对新格式的接受、旧格式兼容、磁盘损坏与越界/重复索引拒绝、跨版本 codec 与投影规则约束、压缩/解压及重建 P 的全流程峰值内存、所有原 A 对象的 W/P/身份一致、原 A 的完整来源核对和稳定摘要复现。原稿的完整 A 验收、供应商可达性、token容量仍未通过。现有三件样本没有总体边界，严禁把 739,480 / 22,234,142 的小样比率乘到 91.6 GB 上承诺容量或耗时。（同 JSON `three_existing_objects_combined.scope`；原 A 执行记录“复现与独立核对的实际边界”。）

## 6. 历史计时、计划门与原账归属

`D/state.json` 的实际内容是 `cases=[baseline,repeat,profile,longH],reserved_plans=12`。它只保存 PUBLIC 计划占用，没有累计秒数、预算剩余或 T0 完成状态；不得解释为新增 12 份额度，也不能改写状态后重新生成。`payload-analysis`、I/O、whole-W 的 `new_plans=0` 表示复用对象，不代表不计时或新授权。

历史诊断已经在原离线账中记录。以下直接抄录 `data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl` 的 `label,seconds,cumulative_seconds,exit_code`，未重算计划、重置两账或补记任何活动。

| label | seconds | cumulative_seconds | exit_code |
| --- | ---: | ---: | ---: |
| 189_t0_program_acceptance（诊断前） | 0.12246779998531565 | 207.9693715001922 | 0 |
| 190_t0_cost_feedback | 0.18594649998703972 | 208.15531800017925 | 1 |
| 191_t0_cost_feedback | 0.8193179999943823 | 208.97463600017363 | 1 |
| 192_t0_cost_feedback_repeat | 0.7644902999745682 | 209.7391263001482 | 1 |
| 193_t0_cost_stages | 2.5368067999952473 | 212.27593310014345 | 1 |
| 194_t0_cost_history_control | 3.0002583999885246 | 215.27619150013197 | 1 |
| 195_t0_payload_lossless_audit | 1.2671284999814816 | 216.54332000011345 | 0 |
| 196_t0_cost_io_control | 0.3336851999920327 | 216.8770052001055 | 0 |
| 197_t0_cost_io_control_corrected | 0.24393960001179948 | 217.1209448001173 | 0 |
| 198_t0_cost_whole_W_control | 0.603461500024423 | 217.7244063001417 | 0 |

各行 `accounting=guard_start_to_child_completion_wall_time_including_failures`；失败/RED同样计入。诊断 `parent` 对 baseline/repeat/profile/longH 在冗余存在时主动退出 1，因此 191–194 的 exit 1 与 `RED_repeated_complete_payloads` 一致，不等同于供应商或 CLI 崩溃。190 的单独失败阶段在这些 result 原件中没有独立结果，不根据相邻成功样例补造细节。（`S/diagnose_t0_costs.py::parent` 与原离线账。）

各 CLI、阶段、序列化/摘要/I/O微基准、压缩与核验秒数是对应守护任务里的内层测量；现有账有相应运行记录，不能再把这些内层秒数累加一次，也不能因它们来自诊断而退还。账中 `source_changed_during_check=[]` 及 `source_sha256` 绑定当时列入守护的生产文件和旧检查器；**未包含这两份诊断脚本本身的摘要**。因此以当前脚本解释字段是现有源码证据，但不能宣称两份脚本的精确字节已由历史账不可变绑定；stdout 与 JSON 镜像一致也不能弥补这一点。

本轮继承原离线账累计 **217.7244063001417 s**；原 T0 账累计 **1797.3523884000024 s**、仅余 **2.6476115999976173 s**；保持 `T0_A_incomplete`。后两项沿用迁移交接和原执行记录，不由本附件重新执行核查。历史 PUBLIC 诊断使用原离线账，不构成 T0 新额度。后续生产实施、公共接口变更及任何新增 T0 总额须由主方案集中提出并经用户确认。

## 附件自检

- 已逐份读取现有 result/stages/payload/I/O/whole-W/state JSON及相关CLI/stdout；只使用本地一手证据。
- 已区分文件表示冗余的实证、局部 I/O 与 CPU 成本的实测、全流程性能和总体压缩率的未知。
- 已说明 whole-W 的实际 pack/manifest 布局、无长度前缀、独立对象压缩，以及 W/P 字节、SHA256、prepared_id 逐项一致性与落盘/内存差别。
- 未运行项目程序、未扫描大目录、未生成样例、未修改生产代码、诊断脚本、原材料或两本资源账；只新增本附件。
