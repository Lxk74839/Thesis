# 工单10正常SIM供应链生成：实施前集中确认稿

日期：2026-10-15（Asia/Shanghai）。**工单09协议总体方案已确认并归档；本稿的工单10具体配置、字段/字节、Interface与验收合同仍待用户一次确认。** 本轮只归档和写作，没有写正式配置、生产代码、测试或数据包。

工作根目录：`C:\Users\Kane\Documents\CodexProject\Thesis`。

固定代码比较基线：`755f277e9a971a517e8b4a5bb94e747b46f3f640`，本轮开始HEAD与之相同。后续实现审查固定从此点比较，不改用滚动HEAD~N。新增归档文档不改变该代码比较起点。

论文题目“一种基于区块链与多智能体技术的农产品可信推荐方法”、双模块及需求解析、推荐管理、用户画像、农产品画像、生命周期追溯、推荐依据核验六角色保持不变。

## 1. 已确认协议的归档

用户本轮明确确认：“我确认工单09草案第12节C1—C11的总体方案及其适用边界。尚未给出的具体配置值不视为已确认。”

已将[工单09](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/09-evidence-protocol.md)作为**规则确认类工单**归档为resolved，协议版本为`sim-evidence-protocol-1.0.0`；正式数据规格与进度索引已追加这一确认及剩余边界。原[09审核草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket09-stage1-sim-evidence-request-review-draft-20261015.md)不回写，保留其当时的待确认措辞。

| 绑定对象 | SHA-256 |
| --- | --- |
| 原09审核草案 | `6ae2dd42b943b65eda899560be8cffa68fac8570ad362439b2a100de76720461` |
| 09工单中的确认/归档记录 | `ef7f34e0868c879963287c4085418ed2748939f394ea61ea1751635b4da7abc6` |

归档覆盖C1—C11：一父商品一批次、六事件八材料十五基础登记、按请求的必要组合、来源/权限、双时间与有效性、版本/撤销/冲突、四态与完整性、独立参考、请求与08隔离、精确字节摘要和单一入口方向。它不表示正常SIM已经生成、具体配置已批准、模型工具已接入或区块链已部署。

本稿补齐的值都是**现在提出的受控模拟配置**，不是对09确认范围的追认。后续10的实施/验收记录写入工单10，不再追加改写已经绑定摘要的09归档记录；协议改变须另有新版本和明确依据。

本轮沿用已读规格、研究草案、修订初稿和06—08验收；不重开全面检索或实现审查。适用的mattpocock-skills为TDD、codebase-design与code-review：以小Interface封装正常生成，只在同意的Seam观察行为；实现后的Standards/Spec按固定基线分别报告。当前阶段不启动TDD或双轴代码审查。

## 2. 工单10的交付范围与推荐配置

### 2.1 最小实现选择

只实现一个固定profile：`normal_six_stage_v1`，数据版本`sim-normal-1.0.0`。没有通用协议解释器、任意模板语言、任意权限表达式或多后端抽象。配置决定本稿明确列出的模拟时间、责任主体和枚举事实；字段形状、关联规则及R1含义由本稿固定。

输入为已验收目录`grain-A-1.1.15`，仅使用每行`parent_asin/crop`；核对目录记录与目录组件摘要、状态和数量。不再次扫描元数据原始大文件，不加载评论、06账号、07分组、08私有目标或模型结果。目录自然包含某些留出目标父ID不构成读取目标标签；生成器不知道哪个是目标。

为全部1,494父商品各建1批、6事件、8原件及15接收登记，预计为1,494 / 8,964 / 11,952 / 22,410条；后续R1独立参考为1,494条批次判断。这些是应验收数量，**不是本轮已生成数量，也不是独立用户样本数**。每个商品使用相同时间/枚举模板，保留原crop；没有随机抖动、异常比例或按用户/评分定制的参数。

### 2.2 时间关系：全部明确为模拟值

固定τ为 **2026-10-08 00:00:00 UTC = 1791417600000毫秒**。批次模拟建立于2026-10-01 00:00 UTC、收录于00:01。快照于 **2026-10-07 12:10 UTC = 1791375000000毫秒** 封存，包含该时点全部本基准接收登记；不含后来登记。

| 阶段 | 事件开始UTC | 事件结束UTC | 事件接收登记UTC |
| --- | --- | --- | --- |
| 采收 / harvest | 2026-10-01T08:00:00Z | 2026-10-01T09:00:00Z | 2026-10-01T09:01:00Z |
| 包装 / packaging | 2026-10-02T08:00:00Z | 2026-10-02T09:00:00Z | 2026-10-02T09:01:00Z |
| 储存 / storage | 2026-10-02T10:00:00Z | 2026-10-04T08:00:00Z | 2026-10-04T08:01:00Z |
| 检验 / inspection | 2026-10-04T09:00:00Z | 2026-10-05T09:00:00Z | 2026-10-05T09:01:00Z |
| 运输 / transport | 2026-10-05T10:00:00Z | 2026-10-06T10:00:00Z | 2026-10-06T10:01:00Z |
| 零售 / retail | 2026-10-07T12:00:00Z | 2026-10-07T12:00:00Z | 2026-10-07T12:01:00Z |

零售事件是已发生的时点观察，start=end；零售材料的有效区间另列，不把未来失效时间写成已经发生的事件终点。

| 材料 | 签发UTC | 接收登记UTC |
| --- | --- | --- |
| D1 harvest_record | 2026-10-01T09:05:00Z | 2026-10-01T09:06:00Z |
| D2 packaging_binding | 2026-10-02T09:05:00Z | 2026-10-02T09:06:00Z |
| D3 storage_log | 2026-10-04T08:05:00Z | 2026-10-04T08:06:00Z |
| D4 inspection_sample | 2026-10-04T09:20:00Z | 2026-10-05T09:02:00Z |
| D5 inspection_report | 2026-10-05T09:10:00Z | 2026-10-05T09:11:00Z |
| D6 transport_dispatch | 2026-10-05T10:05:00Z | 2026-10-06T10:02:00Z |
| D7 transport_receipt | 2026-10-06T10:05:00Z | 2026-10-06T10:06:00Z |
| D8 retail_status | 2026-10-07T12:05:00Z | 2026-10-07T12:06:00Z |

检验采样发生于10月4日09:15，采样材料09:20签发；检测区间为10月4日10:00至10月5日08:30。采样原件等到检验事件于10月5日09:01登记后，于09:02收录；检验报告09:10签发、09:11登记。运输发出材料同理在发出后签发、运输事件结束登记后再收录。这是显式的模拟延迟，不要求材料签发必须晚于整个阶段结束。

零售状态原件观察于10月7日12:00、12:05签发，适用区间推荐为：

`[1791374400000, 1791504000000) = [2026-10-07 12:00, 2026-10-09 00:00) UTC`。

该区间包含τ；τ等于valid_to时失效。valid_to表示该SIM当前状态声明的适用边界，不是未来再次观察的事实。其余7份材料均为historical_fact，无任意TTL，只支持各自已发生的采样/区间事实。

必须验证：批次建立≤首事件开始；阶段end≤下一阶段start；事件登记不早于event_end；材料签发不早于其断言完成的事实时点；材料登记不早于签发及所属事件登记；全部接收登记≤封存≤τ。采样/检测、发出/到货子事实落在所属区间中。零售观察≤签发≤登记，并且valid_from≤τ<valid_to。相等只在上述不等式明确允许处合法。

这些日期、间隔、100个SIM包装单位和枚举状态，只为得到可手查、可复现的正常基准；不声称代表现实谷物供应链时长、食品安全标准或在τ的真实品质。

### 2.3 责任主体与授权范围

下表是8个**模拟业务主体**，不是新增论文智能体或8个独立现实机构。所有材料由项目自行构造，来源记SIM，使用来源为project_constructed_simulation；不复制真实认证、真实签名或机构背书。

| 模拟主体 | 可创建批次 | 可负责事件 | 可签发材料 |
| --- | --- | --- | --- |
| SIM-PRODUCER | 是 | harvest | harvest_record |
| SIM-PACKER | 否 | packaging | packaging_binding |
| SIM-WAREHOUSE | 否 | storage | storage_log |
| SIM-SAMPLER | 否 | 无 | inspection_sample |
| SIM-LAB | 否 | inspection | inspection_report |
| SIM-CARRIER | 否 | transport | transport_dispatch |
| SIM-RECEIVER | 否 | 无 | transport_receipt |
| SIM-RETAIL | 否 | retail | retail_status |

范围均限于当前目录/版本的SIM批次。SIM-REGISTRY只能接收获权主体的批次/事件/材料及记录收录事实，不替其签发业务结论。SIM-VERIFIER是受信任离线核查主体，获准读取当前快照全部基准原件及登记；本轮不发放模型会话工具能力或系统管理员权限。

按09规则，业务主体只可修订/撤销其自身材料谱系；登记主体不能凭“登记者”身份更改别人的事实。本正常版本只生成version=1的register记录，无修订、撤销或实际签名操作。身份模式固定`simulated_allowlist_no_crypto`，不记录“签名通过”。后续状态变更实现归11，真实身份/签名及Fabric接入归后续账本实现。

### 2.4 可原样落盘的配置提案

确认后才将以下完整JSON写入`config/sim-normal-1.0.0.json`。业务所需值均已给出，没有待补天数、阈值、种子或主体。当前只在本确认稿中展示，配置文件尚未创建。

```json
{
  "schema_version": "sim-normal-config-1.0.0",
  "version": "sim-normal-1.0.0",
  "profile": "normal_six_stage_v1",
  "protocol_binding": {
    "version": "sim-evidence-protocol-1.0.0",
    "record_path": ".scratch/data-preparation/issues/09-evidence-protocol.md",
    "record_sha256": "ef7f34e0868c879963287c4085418ed2748939f394ea61ea1751635b4da7abc6",
    "draft_path": ".scratch/data-preparation/ticket09-stage1-sim-evidence-request-review-draft-20261015.md",
    "draft_sha256": "6ae2dd42b943b65eda899560be8cffa68fac8570ad362439b2a100de76720461"
  },
  "catalog_binding": {
    "version": "grain-A-1.1.15",
    "record_path": "records/catalog/grain-A-1.1.15.json",
    "record_sha256": "ff9d23d4c1147cfa75c3f979c77bbbfdb1f630b0ee3a78df4aa3c22fa238ccad",
    "component_sha256": "1fa80d0e969a73fc02ca3c6c815b8c597980d2aaa2e4a9d158d012d967799a84",
    "expected_parent_count": 1494
  },
  "byte_contract": "sim-jsonl-utf8-lf-1.0.0",
  "id_namespace": "Thesis-SIM-1",
  "clock": {
    "batch_created_at_ms": 1790812800000,
    "batch_registered_at_ms": 1790812860000,
    "snapshot_sealed_at_ms": 1791375000000,
    "verify_at_ms": 1791417600000,
    "retail_valid_from_ms": 1791374400000,
    "retail_valid_to_ms": 1791504000000,
    "sampled_at_ms": 1791105300000,
    "test_started_at_ms": 1791108000000,
    "test_completed_at_ms": 1791189000000
  },
  "events": {
    "harvest": {
      "start_ms": 1790841600000,
      "end_ms": 1790845200000,
      "registered_at_ms": 1790845260000
    },
    "packaging": {
      "start_ms": 1790928000000,
      "end_ms": 1790931600000,
      "registered_at_ms": 1790931660000
    },
    "storage": {
      "start_ms": 1790935200000,
      "end_ms": 1791100800000,
      "registered_at_ms": 1791100860000
    },
    "inspection": {
      "start_ms": 1791104400000,
      "end_ms": 1791190800000,
      "registered_at_ms": 1791190860000
    },
    "transport": {
      "start_ms": 1791194400000,
      "end_ms": 1791280800000,
      "registered_at_ms": 1791280860000
    },
    "retail": {
      "start_ms": 1791374400000,
      "end_ms": 1791374400000,
      "registered_at_ms": 1791374460000
    }
  },
  "materials": {
    "harvest_record": {
      "issued_at_ms": 1790845500000,
      "registered_at_ms": 1790845560000
    },
    "packaging_binding": {
      "issued_at_ms": 1790931900000,
      "registered_at_ms": 1790931960000
    },
    "storage_log": {
      "issued_at_ms": 1791101100000,
      "registered_at_ms": 1791101160000
    },
    "inspection_sample": {
      "issued_at_ms": 1791105600000,
      "registered_at_ms": 1791190920000
    },
    "inspection_report": {
      "issued_at_ms": 1791191400000,
      "registered_at_ms": 1791191460000
    },
    "transport_dispatch": {
      "issued_at_ms": 1791194700000,
      "registered_at_ms": 1791280920000
    },
    "transport_receipt": {
      "issued_at_ms": 1791281100000,
      "registered_at_ms": 1791281160000
    },
    "retail_status": {
      "issued_at_ms": 1791374700000,
      "registered_at_ms": 1791374760000
    }
  },
  "issuers": [
    {
      "issuer_id": "SIM-PRODUCER",
      "may_create_batch": true,
      "event_stages": [
        "harvest"
      ],
      "material_kinds": [
        "harvest_record"
      ]
    },
    {
      "issuer_id": "SIM-PACKER",
      "may_create_batch": false,
      "event_stages": [
        "packaging"
      ],
      "material_kinds": [
        "packaging_binding"
      ]
    },
    {
      "issuer_id": "SIM-WAREHOUSE",
      "may_create_batch": false,
      "event_stages": [
        "storage"
      ],
      "material_kinds": [
        "storage_log"
      ]
    },
    {
      "issuer_id": "SIM-SAMPLER",
      "may_create_batch": false,
      "event_stages": [],
      "material_kinds": [
        "inspection_sample"
      ]
    },
    {
      "issuer_id": "SIM-LAB",
      "may_create_batch": false,
      "event_stages": [
        "inspection"
      ],
      "material_kinds": [
        "inspection_report"
      ]
    },
    {
      "issuer_id": "SIM-CARRIER",
      "may_create_batch": false,
      "event_stages": [
        "transport"
      ],
      "material_kinds": [
        "transport_dispatch"
      ]
    },
    {
      "issuer_id": "SIM-RECEIVER",
      "may_create_batch": false,
      "event_stages": [],
      "material_kinds": [
        "transport_receipt"
      ]
    },
    {
      "issuer_id": "SIM-RETAIL",
      "may_create_batch": false,
      "event_stages": [
        "retail"
      ],
      "material_kinds": [
        "retail_status"
      ]
    }
  ],
  "registry": {
    "registrar_id": "SIM-REGISTRY",
    "backend": "local_sim_registry",
    "identity_mode": "simulated_allowlist_no_crypto",
    "read_principal_id": "SIM-VERIFIER"
  },
  "facts": {
    "origin_area_id": "SIM-AREA-01",
    "warehouse_location_id": "SIM-WAREHOUSE-01",
    "retail_location_id": "SIM-RETAIL-01",
    "quantity_units": 100,
    "quantity_unit": "SIM_PACK",
    "packaging_condition": "intact",
    "storage_mode": "SIM_DRY",
    "test_scope": [
      "SIM-Q1"
    ],
    "report_conclusion": "pass",
    "handover_status": "accepted",
    "retail_status": "on_sale"
  },
  "reference_request": {
    "profile_id": "R1_SIM_Q1",
    "source": "experiment_design",
    "predicate": "inspection_report_conclusion",
    "required_test_scope": [
      "SIM-Q1"
    ],
    "required_conclusion": "pass",
    "time_scope": "sampling_event",
    "required_kinds": [
      "inspection_sample",
      "inspection_report"
    ]
  }
}
```

顶层**恰为以上14个键**；嵌套键也按示例封闭，未知键、重复键或缺键均拒绝。版本为安全的路径单节（字母、数字、点、连字符），其他profile不自动兼容。各时间/数量必须为JSON整数，布尔值不能充当整数，取值0至2^53−1；字符串非空且不含NUL，ID/枚举必须匹配本稿类型。数组不接受重复元素；阶段、材料、主体及项目数组按给定顺序固定。R1项目只启用SIM-Q1，报告conclusion固定pass作为正常事实，required_conclusion是研究请求谓词，不是gold答案。

协议绑定验证归档记录和原09草案的实际文件摘要；目录绑定验证--catalog-record指向同一记录、stage=catalog、status=catalog_complete、scope_version一致，目录组件实际摘要及唯一父商品数等于绑定。原目录行须为included、crop为非空字符串；不读取嵌套metadata内容参与生成，不重跑目录筛选。已确认的文件摘要是接受依据，不拿旧producer摘要与当前已演进代码强行比较。

不增设运行时“用户审批系统”。本文确认后，将确认及本稿摘要记入工单10，再写上述配置；运行时校验已归档协议、受支持profile、完整字段及绑定，未知/缺失协议不能因自报approved=true获得通过。配置/规则有实质变更时须记录新确认及新版本，不能靠换一个未受审的JSON冒充原版本复现。

## 3. 字段、ID、版本与字节合同

### 3.1 类型与共同约定

所有对象均拒绝未知结构和重复键。source必须为SIM；原件不含expected_status、gold、anomaly_type、目标/用户/评论字段或自身摘要。各schema版本固定1.0.0。parent_asin/crop按输入字符串逐字保留，不trim、改大小写或Unicode规范化。真实评论始终只归父商品，未加入任何SIM批次关联标签。

本节封闭键和整数限制只作用于新增配置/输出。原目录沿用已验收schema，允许其已有metadata及数值类型存在；生成只取parent_asin/crop，不因metadata里有评分、价格等字段而复制、使用或改写它们。

字段的必要性由下表固定；只有零售材料多两个有效时间键，其他材料**不带**这两个键，不用null冒充缺失。未启用的温湿度、检测浓度、法定阈值或当前品质字段不在schema中。

| 记录 | 完整键集合及类型 |
| --- | --- |
| batch | schema_version、source、parent_asin、crop、catalog_version、sim_batch_id、sim_profile_id、protocol_version、issuer_id：字符串；version：整数1；created_at_ms：整数毫秒 |
| event | schema_version、source、event_id、parent_asin、sim_batch_id、stage、actor_id：字符串；version：整数1；event_start_ms/event_end_ms：整数毫秒；predecessor_event_ids：字符串数组，首阶段为空，其余恰前一阶段ID |
| material共同部分 | schema_version、source、evidence_id、parent_asin、sim_batch_id、event_id、kind、issuer_id、temporal_mode：字符串；version：整数1；issued_at_ms：整数毫秒；facts：按kind封闭的对象 |
| retail_status额外键 | valid_from_ms、valid_to_ms：整数毫秒，valid_from<valid_to；temporal_mode=current_assertion |
| 其他7种材料 | temporal_mode=historical_fact；不含valid_from/valid_to，不自动补TTL |

八种facts的完整键及值域如下。cfg中未出现的事件/采样/运输段ID，由下节确定性规则得到。

| kind/所属事件 | facts完整字段 | 正常值/约束 |
| --- | --- | --- |
| harvest_record / harvest | origin_area_id:string，crop:string，harvested_at_ms:int | SIM-AREA-01；crop同目录；时间同采收event_end |
| packaging_binding / packaging | harvest_event_id:string，packaged_at_ms:int，package_condition:string，quantity_units:int，unit:string | 引用同批次harvest事件；时间同包装end；intact；100；SIM_PACK |
| storage_log / storage | coverage_start_ms:int，coverage_end_ms:int，segments:array<object>；每段恰start_ms:int/end_ms:int/mode:string | 单段覆盖整个储存半开区间；mode=SIM_DRY。仅记录模拟模式，不据此作数值达标判断 |
| inspection_sample / inspection | sample_id:string，sampled_at_ms:int | 同批次采样ID；1791105300000；落在检验事件内 |
| inspection_report / inspection | sample_id:string，test_scope:array<string>，test_started_at_ms:int，test_completed_at_ms:int，conclusion:string | 同一sample；[SIM-Q1]；1791108000000至1791189000000；pass |
| transport_dispatch / transport | transport_segment_id:string，departed_at_ms:int，from_location_id:string，to_location_id:string，quantity_units:int，unit:string | 同批次运输段；时间同运输start；SIM-WAREHOUSE-01→SIM-RETAIL-01；100 SIM_PACK |
| transport_receipt / transport | transport_segment_id:string，arrived_at_ms:int，from_location_id:string，to_location_id:string，quantity_units:int，unit:string，handover_status:string | 同运输段/路线；时间同运输end；100 SIM_PACK；accepted |
| retail_status / retail | observed_at_ms:int，location_id:string，status:string，stock_units:int，unit:string | 时间同零售时点；SIM-RETAIL-01；on_sale；100 SIM_PACK |

数量是离散模拟包装单位，不能解释为千克、真实在售规格或采集时库存。运输发出/收到数量按同单位整数严格相等，不引入称量容差。storage_mode不是储存合规判定标签；SIM-Q1/pass也不扩展为全部食品安全结论。

### 3.2 ID确定性、唯一性和关联

定义`H(tag, parts...)`为SHA-256，输入为UTF-8编码的`"Thesis-SIM-1:"+tag`、一个NUL字节，以及各part的UTF-8字节，parts之间用单个NUL分隔，无尾NUL。禁止part包含NUL；哈希输出为完整64位小写十六进制。

| 标识 | 精确规则 |
| --- | --- |
| sim_batch_id | `b_ + H("batch", catalog_version, parent_asin)` |
| event_id | `e_ + H("event", sim_batch_id, stage)` |
| evidence_id | `d_ + H("evidence", sim_batch_id, kind, issuer_id)` |
| sample_id | `s_ + H("sample", sim_batch_id)` |
| transport_segment_id | `t_ + H("transport_segment", sim_batch_id)` |
| registration_id | `g_ + H("registration", target_kind, target_id, 十进制version)` |
| snapshot_id | `n_ + SHA256(UTF-8("Thesis-SIM-1:snapshot") + NUL + snapshot_core的规范字节)`，core不含snapshot_id自身 |

候选身份为(parent_asin,sim_batch_id)，不依赖用户、目标或场景名。batch依赖目录命名空间而不依赖材料内容、时间或生成版本，因此同目录批次在后续材料视图/版本变化中保持业务身份。不同目录版本属于不同基准命名空间；不把它们声称为不同真实批次样本。

事件/材料/登记均反查到恰一个当前批次；材料event_id必须同批次且kind与stage匹配。采样ID和运输段ID不能只比字符串而跳过父商品、批次、事件；包装harvest_event_id必须为同批次前驱。正常包不存在跨父商品、孤儿或同id/version多字节原件。

batch/event/material业务version全部为1，(类型,id,version)唯一；本阶段不生成v2、supersedes或revokes。未来材料修订保持evidence_id、增加业务version并显式前后关联，遵守09头版本/撤销不回退；数据版本sim-normal-1.0.0与业务version=1不同。已发布目录和旧原件不原地改字节。配置、生产器或依赖变化导致同版本复用冲突时拒绝覆盖，不能把运行时间更新当作修订。

### 3.3 JSONL与摘要

字节合同`sim-jsonl-utf8-lf-1.0.0`：

1. UTF-8无BOM；每记录一个紧凑JSON对象，键在所有嵌套对象中按Unicode码点序排序（本schema键均ASCII）；无键间空格，数组保持规定顺序。字符串标准JSON转义，非ASCII直接UTF-8，不作Unicode规范化；数值只允许整数，无浮点/NaN/Infinity。
2. JSONL行尾严格单个LF，不允许CRLF、空白行或多余尾空行；非空文件最后一条也带LF。单对象JSON组件（policy/snapshot）同样紧凑排序并以一个LF结束。
3. **对象content_sha256只摘要该行JSON的原始UTF-8字节，不含LF**；文件SHA-256包含全部实际字节及LF。登记对象不包含在其自身target摘要中；快照core也不含自身ID，禁止递归摘要。
4. batches按parent_asin的UTF-8字节升序；events按父商品顺序、固定六阶段顺序；materials按父商品顺序、固定八kind顺序；registrations按(registered_at_ms, target_kind顺序batch/event/material, target_id UTF-8字节, version)升序，sequence从1连续编号。
5. 不把真实生成时钟、绝对输出路径、Python日志或模型结果写入这6个稳定组件。源文件绑定与实际运行信息放在主记录；相同绑定和代码在新目录重跑，稳定组件逐字节相同。
6. 读取校验原始字节，不先改换行/重新序列化后比较摘要。输入catalog仍沿用其已有字节合同，不反写或重排；新输出排序不改变原目录。

标准库即可实现，无新依赖；此合同是受限整数JSON合同，不声称实现完整JCS或VC。

## 4. 一个完整的虚构商品示例

这是文档内的单商品例：parent_asin=DEMO-P001、crop=rice，使用上面时间/主体配置及目录命名空间计算ID；**它不表示真实目录含此商品，不写入data目录，也不计统计样本**。下列JSONL每行都是完整原件，未省略字段；对象摘要不含代码块展示的LF。

批次B的完整原件：

```jsonl
{"catalog_version":"grain-A-1.1.15","created_at_ms":1790812800000,"crop":"rice","issuer_id":"SIM-PRODUCER","parent_asin":"DEMO-P001","protocol_version":"sim-evidence-protocol-1.0.0","schema_version":"sim-batch-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","sim_profile_id":"normal_six_stage_v1","source":"SIM","version":1}
```

六事件按E1—E6排列，前驱ID可以逐行反查：

```jsonl
{"actor_id":"SIM-PRODUCER","event_end_ms":1790845200000,"event_id":"e_7e6328ef6b8b34c65933ace1082712f5afff960824c2932db45860c865861616","event_start_ms":1790841600000,"parent_asin":"DEMO-P001","predecessor_event_ids":[],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"harvest","version":1}
{"actor_id":"SIM-PACKER","event_end_ms":1790931600000,"event_id":"e_94095c325a21d0340982d1a051721bf438aac9e625f703c8535e50f4c7dc35df","event_start_ms":1790928000000,"parent_asin":"DEMO-P001","predecessor_event_ids":["e_7e6328ef6b8b34c65933ace1082712f5afff960824c2932db45860c865861616"],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"packaging","version":1}
{"actor_id":"SIM-WAREHOUSE","event_end_ms":1791100800000,"event_id":"e_5038b96c9526120c7c5ccac9e5755c452fc1b73e643ddebabe7b93219d4461c7","event_start_ms":1790935200000,"parent_asin":"DEMO-P001","predecessor_event_ids":["e_94095c325a21d0340982d1a051721bf438aac9e625f703c8535e50f4c7dc35df"],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"storage","version":1}
{"actor_id":"SIM-LAB","event_end_ms":1791190800000,"event_id":"e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6","event_start_ms":1791104400000,"parent_asin":"DEMO-P001","predecessor_event_ids":["e_5038b96c9526120c7c5ccac9e5755c452fc1b73e643ddebabe7b93219d4461c7"],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"inspection","version":1}
{"actor_id":"SIM-CARRIER","event_end_ms":1791280800000,"event_id":"e_050d59da3900381b919ca5d32be047a0bace1b5994e54450af2e1be32b3f61bc","event_start_ms":1791194400000,"parent_asin":"DEMO-P001","predecessor_event_ids":["e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6"],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"transport","version":1}
{"actor_id":"SIM-RETAIL","event_end_ms":1791374400000,"event_id":"e_369a2d9282e6af5932c43fe208bf92a638c6eecba0d876cf6daae9c7c87abbf9","event_start_ms":1791374400000,"parent_asin":"DEMO-P001","predecessor_event_ids":["e_050d59da3900381b919ca5d32be047a0bace1b5994e54450af2e1be32b3f61bc"],"schema_version":"sim-event-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","stage":"retail","version":1}
```

八材料按D1—D8排列；检验D4/D5的sample_id相同，运输D6/D7的segment、路线和数量相同，D8有显式有效区间：

```jsonl
{"event_id":"e_7e6328ef6b8b34c65933ace1082712f5afff960824c2932db45860c865861616","evidence_id":"d_3cac64a97dfbc31f2b8098c5e2361d226e7c0bcdd73ac8c7c17ad4a8d954739c","facts":{"crop":"rice","harvested_at_ms":1790845200000,"origin_area_id":"SIM-AREA-01"},"issued_at_ms":1790845500000,"issuer_id":"SIM-PRODUCER","kind":"harvest_record","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_94095c325a21d0340982d1a051721bf438aac9e625f703c8535e50f4c7dc35df","evidence_id":"d_4b86f727285f12a2337403fd390ee58cea692edfd2d87ddb8aed4274b9e35816","facts":{"harvest_event_id":"e_7e6328ef6b8b34c65933ace1082712f5afff960824c2932db45860c865861616","package_condition":"intact","packaged_at_ms":1790931600000,"quantity_units":100,"unit":"SIM_PACK"},"issued_at_ms":1790931900000,"issuer_id":"SIM-PACKER","kind":"packaging_binding","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_5038b96c9526120c7c5ccac9e5755c452fc1b73e643ddebabe7b93219d4461c7","evidence_id":"d_2f8242594650fef919c4f4d2ea5a1b6888b900838a85be62da265f38a42e897f","facts":{"coverage_end_ms":1791100800000,"coverage_start_ms":1790935200000,"segments":[{"end_ms":1791100800000,"mode":"SIM_DRY","start_ms":1790935200000}]},"issued_at_ms":1791101100000,"issuer_id":"SIM-WAREHOUSE","kind":"storage_log","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6","evidence_id":"d_424ee04cabe4aa7552321b22ee2cd7c02c0dc007390251e9963f386f1c0b726f","facts":{"sample_id":"s_9082e4616e39185b4700ac663b5c479408ded39790a8cf28a146a9b872cd3289","sampled_at_ms":1791105300000},"issued_at_ms":1791105600000,"issuer_id":"SIM-SAMPLER","kind":"inspection_sample","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6","evidence_id":"d_eb64a2181dff5b0ccafc395d84ab5d807fc8efe2756963ba89a4c4bf1600fc28","facts":{"conclusion":"pass","sample_id":"s_9082e4616e39185b4700ac663b5c479408ded39790a8cf28a146a9b872cd3289","test_completed_at_ms":1791189000000,"test_scope":["SIM-Q1"],"test_started_at_ms":1791108000000},"issued_at_ms":1791191400000,"issuer_id":"SIM-LAB","kind":"inspection_report","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_050d59da3900381b919ca5d32be047a0bace1b5994e54450af2e1be32b3f61bc","evidence_id":"d_62817700e2de79662b919b33b096c80e562b66cc87bc0d7dfb53d64f8952b40f","facts":{"departed_at_ms":1791194400000,"from_location_id":"SIM-WAREHOUSE-01","quantity_units":100,"to_location_id":"SIM-RETAIL-01","transport_segment_id":"t_256ec93a00a3481029e8ecfafbacfc9d7279a1a1699a4d1ae0269098c61522e0","unit":"SIM_PACK"},"issued_at_ms":1791194700000,"issuer_id":"SIM-CARRIER","kind":"transport_dispatch","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_050d59da3900381b919ca5d32be047a0bace1b5994e54450af2e1be32b3f61bc","evidence_id":"d_a7586fc5ad0fdcb3d914cac28fbbc8a8b7b29dea56d21c830525fac622ac1e7f","facts":{"arrived_at_ms":1791280800000,"from_location_id":"SIM-WAREHOUSE-01","handover_status":"accepted","quantity_units":100,"to_location_id":"SIM-RETAIL-01","transport_segment_id":"t_256ec93a00a3481029e8ecfafbacfc9d7279a1a1699a4d1ae0269098c61522e0","unit":"SIM_PACK"},"issued_at_ms":1791281100000,"issuer_id":"SIM-RECEIVER","kind":"transport_receipt","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"historical_fact","version":1}
{"event_id":"e_369a2d9282e6af5932c43fe208bf92a638c6eecba0d876cf6daae9c7c87abbf9","evidence_id":"d_76173f116cfcd0a56fbb7e231ef73b245a4cd72d78a1a8d607a439faea22dba3","facts":{"location_id":"SIM-RETAIL-01","observed_at_ms":1791374400000,"status":"on_sale","stock_units":100,"unit":"SIM_PACK"},"issued_at_ms":1791374700000,"issuer_id":"SIM-RETAIL","kind":"retail_status","parent_asin":"DEMO-P001","schema_version":"sim-material-1.0.0","sim_batch_id":"b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04","source":"SIM","temporal_mode":"current_assertion","valid_from_ms":1791374400000,"valid_to_ms":1791504000000,"version":1}
```

人工定位表：

| 别名 | 含义 | 完整ID |
| --- | --- | --- |
| E1 | 采收事件 | `e_7e6328ef6b8b34c65933ace1082712f5afff960824c2932db45860c865861616` |
| E2 | 包装事件 | `e_94095c325a21d0340982d1a051721bf438aac9e625f703c8535e50f4c7dc35df` |
| E3 | 储存事件 | `e_5038b96c9526120c7c5ccac9e5755c452fc1b73e643ddebabe7b93219d4461c7` |
| E4 | 检验事件 | `e_6928d0552279112564887fa2e290207dbaf4c244dd104bd1818564970f0229e6` |
| E5 | 运输事件 | `e_050d59da3900381b919ca5d32be047a0bace1b5994e54450af2e1be32b3f61bc` |
| E6 | 零售事件 | `e_369a2d9282e6af5932c43fe208bf92a638c6eecba0d876cf6daae9c7c87abbf9` |
| D1 | 采收记录 | `d_3cac64a97dfbc31f2b8098c5e2361d226e7c0bcdd73ac8c7c17ad4a8d954739c` |
| D2 | 包装绑定 | `d_4b86f727285f12a2337403fd390ee58cea692edfd2d87ddb8aed4274b9e35816` |
| D3 | 储存区间 | `d_2f8242594650fef919c4f4d2ea5a1b6888b900838a85be62da265f38a42e897f` |
| D4 | 采样绑定 | `d_424ee04cabe4aa7552321b22ee2cd7c02c0dc007390251e9963f386f1c0b726f` |
| D5 | 检验报告 | `d_eb64a2181dff5b0ccafc395d84ab5d807fc8efe2756963ba89a4c4bf1600fc28` |
| D6 | 运输发出 | `d_62817700e2de79662b919b33b096c80e562b66cc87bc0d7dfb53d64f8952b40f` |
| D7 | 到货交接 | `d_a7586fc5ad0fdcb3d914cac28fbbc8a8b7b29dea56d21c830525fac622ac1e7f` |
| D8 | 零售状态 | `d_76173f116cfcd0a56fbb7e231ef73b245a4cd72d78a1a8d607a439faea22dba3` |

B=`b_3b7d6d7e781b47b69ab0cc7f62561ac1a00afa3df573e7458a3831bff3c98c04`。对两份R1原件的摘要人工核对向量为：

| 原件 | 精确单行字节的SHA-256（不含LF） |
| --- | --- |
| D4 采样绑定 | `defc69f661bc92ee5a92f16b2bb9f956b74066409bad558ce1ff22896c6e97d8` |
| D5 检验报告 | `b2666c82d25aa867050b78ca64c457caf3edd5ddfcf021a361b3609733580b5d` |

这些ID、时间和两个摘要已用.NET独立计算，供后续公共夹具使用；未运行生产生成器。示例不是“由生产输出反推期望”。

## 5. 接收登记、策略与快照合同

### 5.1 接收登记：每批次15条

每条registration恰含以下字段：

| 字段 | 类型/值 |
| --- | --- |
| schema_version/source/registry_backend | string，sim-registration-1.0.0 / SIM / local_sim_registry |
| registration_id/target_kind/target_id | string；kind限batch/event/material，ID按第3.2节 |
| version/sequence | int；version=1；sequence为全快照1..15N |
| parent_asin/sim_batch_id | string，与原件和批次映射相同 |
| event_id | batch时为null；event时等于自身event_id；material时等于其适用event_id |
| issuer_id | batch取issuer_id，event取actor_id，material取issuer_id；必须获该类型授权 |
| content_sha256 | string，64位小写hex，为目标原件单行字节摘要 |
| registrar_id/receipt_status | string，SIM-REGISTRY / accepted |
| registered_at_ms | int，按第2.2节对应条目 |

receipt_status=accepted只表示模拟接收成功，不代表材料结论Supported、密码签名成功或区块链有效提交。event_id=null是batch登记的已声明不适用，不是未知关联。

同一原件恰一条register接收记录；登记索引的对象/版本/issuer/摘要均与原件核对。封存后不追加登记来改变旧快照；状态变更类型和异常登记由11另行实现，本阶段不建立通用状态日志框架。

### 5.2 策略policy.json

固定完整键为：schema_version、source、policy_id、catalog_version、sim_version、identity_mode、creation_source、issuers、registrar_id、read_principal_id、read_scope、status_change_authority。

前七项/主体/issuer数组分别取本稿固定schema `sim-policy-1.0.0`、SIM、`sim-normal-policy-1.0.0`、目录/数据版本、`simulated_allowlist_no_crypto`、`project_constructed_simulation`及第2.4节issuers。read_scope恰为`{target_kinds:["batch","event","material"],material_kinds:[八kind固定顺序],scope:"current_snapshot_only"}`；status_change_authority固定`issuer_own_lineage_only`。本地准备与核查主体被信任，策略不宣称NTFS或未来模型访问隔离已验收。

### 5.3 快照snapshot.json

snapshot_core恰含：schema_version=`sim-snapshot-1.0.0`、source=SIM、protocol_version、catalog_version、sim_version、registry_backend、cutoff_sequence、sealed_at_ms、verify_at_ms、policy_id、reference_request、components。类型分别为字符串、整数毫秒/序号、reference_request对象及components对象；reference_request完整复制第2.4节研究请求定义。

components恰列batches.jsonl/events.jsonl/materials.jsonl/registrations.jsonl/policy.json，每项恰`{sha256:string,bytes:int,records:int}`。hash是相应文件的实际全部字节；policy records=1。cutoff_sequence=15N，等于最后连续登记序号，全部登记时间≤sealed_at。core按第3.3节序列化但不加LF后计算snapshot_id，再将该ID加入最终snapshot对象，整个文件以LF结束。snapshot文件自身摘要只放在外部主记录，不写入自己的components。

独立核查通过实际登记/原件枚举、版本及权限计算R1范围完成性，不采信生成器自报的complete=true或normal=true。快照只代表本基准的固定授权收录范围，不声称现实供应链事实完整。

## 6. R1与独立参考：本工单做到什么

R1是研究设计请求：“该批次指定采样事件的SIM-Q1报告结论为pass”。每个批次只生成一份sample与一份report；参考按当前批次的唯一检验事件/采样绑定实例化，不读取真实用户历史或目标。不把R1分配给1,603个根任务，不改08固定请求或候选；根任务联合接入在后续工单。

最小支持组合为：可采用的inspection_sample + 可采用的inspection_report；两者父商品/批次/检验事件/sample_id一致，报告覆盖SIM-Q1且conclusion=pass。还需该声明相关批次/事件/登记、签发/读取权限、时间/业务头版本和相关快照范围完成。报告pass是原始SIM报告事实，不能直接当作整批次gold。

没有样本绑定、无权限、摘要不符或对象错配不能形成正/反组合；报告为fail且绑定完整才构成有效否定。独立谱系有效pass与fail并存才为Conflict；这些语义继承09。**10不实现通用生产四态核验器或异常生成器**，只以专用独立R1参考核算正常材料，正常全量应为1,494个Supported。状态是推导结果，不是生产器写死的答案。异常场景/分配在11检验，不能在10提前生产带异常标签的大数据。

独立参考由单独验收程序（拟`.scratch/data-preparation/diagnostics/verify_sim10.py`）读取公共原件/登记/策略/快照及结构化请求，使用标准库逐字节/关联核查，不导入sim_normal或其他生产核验函数，也不接收生成器异常类型、生产最终状态或模型结果。参考程序及其结果摘要单独记录。

每条私有参考完整键为：

- schema_version=`sim-r1-reference-1.0.0`、source=SIM、reference_rule_version=`r1-reference-1.0.0`；
- parent_asin、sim_batch_id、snapshot_id、request_profile_id=R1_SIM_Q1；
- adopted_evidence：数组，每项恰evidence_id/version/content_sha256/fact_pointers；R1正常为两项，定位sample的/facts/sample_id及报告的/facts/sample_id、/facts/test_scope、/facts/conclusion；
- rejected_evidence：数组，每项恰evidence_id/version/reason；正常为空；
- registration_ids：相关登记ID数组，及scope_complete:boolean、support_present:boolean、refutation_present:boolean、state:string；
- derivation：恰含batch_event_binding、sample_id_match、required_project_covered、material_time_valid、issuer_and_read_authorized（boolean），observed_report_conclusion、requested_conclusion（string），selected_versions（恰含sample/report两个整数），related_registration_count（int）。正常为五个true、pass/pass、1/1及4条相关登记；这些值逐项由原件与登记核算，不复制生成器断言。

数组按对应ID UTF-8字节序排序。参考和审核详细轨迹只放私有审计目录，不加入模型可读组件。人工至少逐项核对本稿完整虚构例及09四态作例；全量采用独立程序检查所有记录，不以抽查代替关联/摘要验证。没有外部专家参与时称独立计算与作者核对。

基准包的六阶段结构验收与R1资格推导分开：正常包必须有六事件八原件，但R1不额外要求包装状态、储存数值或零售库存。R6全履历、R2运输等已确认方向保留，10不实现这些请求的通用执行。储存模式只存事实，R4数值达标及“当前品质”未启用，没有相应阈值。

## 7. 输出组件、主记录与接受记录

### 7.1 固定输出位置

以--output-root为根（必须在Thesis内），生成以下新版本路径；输入的目录/协议/配置路径始终以Thesis项目根解析，不从output-root寻找私有上游。新空复现root仍使用相同输入及同版本相对布局。

| 位置 | 内容/数量 |
| --- | --- |
| data/sim/grain-A-1.1.15/sim-normal-1.0.0/batches.jsonl | 1,494批次原件 |
| 同目录events.jsonl | 8,964事件原件 |
| 同目录materials.jsonl | 11,952材料原件 |
| 同目录registrations.jsonl | 22,410接收登记 |
| 同目录policy.json、snapshot.json | 各1个对象 |
| records/sim/grain-A-1.1.15-sim-normal-1.0.0.json | 不可原地更新的生成主记录，绑定六稳定组件及来源 |
| data/sim-reference/grain-A-1.1.15/sim-normal-1.0.0/r1-reference-1.0.0/reference-r1.jsonl | 独立程序生成的1,494条私有参考，不是生产组件 |
| 同参考目录check.json | 独立核查摘要/计数/失败及来源绑定；参考稳定数据与实际运行日志分开 |
| records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json | 只有独立核查、复现、保护、公共测试与两轴审查通过后才归档的接受记录 |

没有第三个数据准备入口、Web管理界面、额外模型manifest或分场景数据目录。运行日志/TDD/审查证据沿用`.scratch/data-preparation/verification/`；不复制真实上游材料作新“来源”。

### 7.2 生成主记录与CLI成功合同

生成主记录的完整顶层为：

| 键 | 类型/内容 |
| --- | --- |
| stage/status | string，sim_normal / normal_sim_prepared |
| catalog_version/sim_version/profile/protocol_version | string，绑定本稿版本 |
| inputs | object，恰config、protocol_record、protocol_draft、catalog_record、catalog；每项path（项目相对路径）、sha256、bytes |
| producer_sha256 | object，恰prepare_data.py和sim_normal.py的实际SHA-256，不虚构未出现文件摘要 |
| code_state | object，git_head_sha、worktree_dirty；如实记录运行时状态，不拿固定比较基线冒充实际运行HEAD |
| components | object，六稳定文件名到path（输出root相对）、sha256、bytes、records的映射 |
| counts | object，parents=N、batches=N、events=6N、materials=8N、registrations=15N；policy/snapshot各1不算批次样本 |
| snapshot_id/sim_verify_at_ms | string/int，实际快照ID及固定τ |
| reuse_fingerprint_sha256 | string，对fingerprint_core按本稿字节序列化（不含LF）后SHA-256；是复用指纹，**不是数字签名** |
| runtime | object，python_version、conda_prefix、generated_at_utc；只在主记录，不进入稳定原件 |
| normal_component_status/independent_acceptance | prepared / pending_separate_record |
| formal_package_status/model_execution_status/ledger_deployment_status/sample_sufficiency | not_built / not_run / not_deployed / not_determined |

inputs中的catalog组件以已验收记录给出的catalog_path读取，核对其摘要。fingerprint_core恰含stage、catalog_version、sim_version、profile、protocol_version、inputs、producer_sha256，取主记录对应值；不含runtime、code_state、输出components或自身摘要。protocol_record/draft路径及字节摘要按归档绑定。主记录输出与stdout JSON为相同对象；stdout不另打印原账号、路径错误堆栈、数据原文或调试信息。

先在项目.tmp下构造并核查六文件，再发布新版本目录，最后独占写成功主记录。同版本若输入/配置/生产器指纹和全部六组件匹配，退出0返回既有主记录，不改其字节；组件缺损、旧记录不匹配或已占用版本路径均拒绝覆盖。构造/校验失败无成功主记录，暂存保留在项目.tmp；若发布中断已留下未完整版本，必须视为不完整，不能标prepared、复用或自动覆写。不新增跨目录事务/自动恢复框架。路径检查覆盖写入目标全部祖先，拒绝符号链接/junction逃逸和输入输出重叠；不改动08的既有实现。

### 7.3 接受记录合同

生成退出0只表示prepared，**不自动写accepted**。独立验收、公共测试、复现、保护及固定基线双轴审查完成后，在独立接受记录里归档下列完整顶层：

- schema_version=`sim-normal-acceptance-1.0.0`、status=`accepted_ticket10_normal_sim_component_only`、catalog_version、sim_version；
- approved_contract：工单10本稿路径/摘要及用户确认记录路径/摘要；协议及配置摘要；
- generation_record：主记录path/sha256；components：六个组件的path/sha256/bytes/records，与主记录一致；
- independent_reference：参考规则版本、程序path/sha256、私有reference-r1及check的path/sha256、审计总数与状态计数；正常为Supported=N、Refuted/Pending/Conflict均0；
- validation：public_cli_tests、independent_full_check、fresh_reproduction、upstream_protection四项，每项status及报告path/sha256；计数/环境均如实记录；
- reviews：固定base_sha=755f277…、实际review_head_sha、Standards和Spec各自报告path/sha256、阻塞数；不合并两轴发现来掩盖任一失败；
- limitations：formal_package_status=not_built、sample_sufficiency=not_determined、model_execution_status=not_run、ledger_deployment_status=not_deployed；
- accepted_at_utc：实际归档时间。

没有自含摘要或虚构回执。接受记录本身的摘要由后续依赖或交付记录保存。生成主记录仍保留pending_separate_record原字节，以“接受记录存在且完整绑定当前主记录/产物/证据”为组件验收生效依据，不回改主记录。失败时保留诊断与拒绝原因，不产生accepted状态。

同版本的任何已发布产物损坏或生产器修订不得靠重写接受表消解；保留失败/旧版，必要时升级sim-normal-1.0.1及相应接受记录。正常参考全部Supported只证明当前SIM请求/快照下的规则结果，不证明现实品质、推荐效果或样本充分。

## 8. 公共Interface、Seam与验收行为

### 8.1 唯一公共数据准备入口

新增`prepare_data.py --stage sim_normal`及`--sim-config PATH`；只使用三个阶段参数：

| 参数 | 必需 | 合同 |
| --- | --- | --- |
| --catalog-record | 是 | 当前Thesis内已绑定目录记录；验证其状态/版本及目录字节，不读原始元数据/评论 |
| --sim-config | 是 | 确认后写入的完整JSON配置；验证封闭字段、协议/目录绑定、时间和主体 |
| --output-root | 是 | Thesis项目内独立根；输入根仍为项目根；不覆盖既有版本 |

全局--stage同样必需。sim_normal误传其他阶段参数（如--review-record、--split-record、--task-config、--access-probe）拒绝，不把它们当额外数据来源；其他旧阶段的参数/输出语义不改。

此阶段所有CLI相对路径均以固定Thesis项目根解析；绝对路径解析后也必须仍在项目内。来源记录中的相对依赖路径同样以项目根解析，输出组件绑定则相对于其output-root。命令示例从项目根运行。

以下是**确认并实现之后**的调用形式，当前版本没有sim_normal，不在本轮执行：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TMP=Join-Path $PWD '.tmp'
$env:TEMP=$env:TMP
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage sim_normal --catalog-record records/catalog/grain-A-1.1.15.json --sim-config config/sim-normal-1.0.0.json --output-root .
```

| 情形 | 退出码/stdout |
| --- | --- |
| 新鲜成功或一致复用 | 0；第7.2节主记录对象，status=normal_sim_prepared |
| 缺阶段参数、错误/越界路径、非法JSON/类型/字段、时间或权限配置不合法 | 2；恰`{stage:"sim_normal",status:"sim_normal_incomplete",error:{code:稳定原因码}}` |
| 未识别或不匹配的协议/profile/归档摘要 | 2；同形状，status=needs_confirmation，code=unapproved_protocol |
| 目录状态/版本/摘要/数量或父商品字段不符 | 2；status=sim_normal_incomplete，code=invalid_catalog |
| 同版本来源/配置/生产器变化、组件缺损或目标已被占用 | 2；status=sim_normal_incomplete，code=output_conflict |
| 命令语法本身错误（未知参数等） | 2；沿用argparse错误，无成功记录；不承诺结构化JSON |

其他稳定原因码仅`invalid_config`、`invalid_path`、`invalid_arguments`、`io_error`；阶段分派后错误不回显原件/宿主私有绝对路径。未知stage仍是现有argparse行为；不借此改所有阶段错误处理。

### 8.2 确认的测试Seam提案

**S1：公共数据CLI。** 测试用subprocess通过真实prepare_data.py，观察退出码/stdout和其正式输出组件；可以独立读取/哈希这些产物，不导入生产模块、调用内部函数、mock内部协作者或依赖实现形状。它能验收生成/关联/发布/复用，不能证明未来模型工具、NTFS隔离或区块链行为。

**S2：独立离线核查的外部执行。** 拟验收脚本`verify_sim10.py --record PATH --audit-root PATH`只读取相同公共产物和绑定配置，写私有参考/check；退出0表示该次正常核查与参考一致，2表示不完整/不一致并保留失败check，不写正式accepted。其测试也只看外部产物/退出状态，期望来自本稿手算例/09规则，不测试内部函数。它是独立验收取证程序，不是第二个SIM数据准备入口，不承担模型/异常场景生成。

S2的record/output均须在项目内；audit-root为新空私有路径，不能覆盖原件。正式运行采用第7.1节参考目录；新鲜复现/失败夹具使用项目.tmp中的独立目录。它不接收--expected-status、异常计划或生产核验结果参数，审计读取权限与SIM-VERIFIER范围一致。

S2从`<生成root>/records/sim/<主记录文件>`的固定布局确定生成root，再解析主记录components的相对路径；inputs仍从Thesis项目根解析。record布局或组件路径越界即失败，不扫描旁边目录猜测原料。

### 8.3 验收行为清单

下列是应通过的外部行为，不是预先一次写完全部测试的指令；实施时每次只选一个行为做RED→GREEN。

| 编号 | 通过Seam/观察 | 必须看到的结果 |
| --- | --- | --- |
| A1 参数与批准依赖 | S1退出状态/文件 | 缺任一必要参数、未知配置结构/类型、未绑定协议不发布成功组件；原因码符合8.1 |
| A2 目录绑定与覆盖 | S1产物，合成小目录及真实1,494目录 | 全部唯一父商品各1批6事件8材料15登记；有无评论/是否形成用户任务不影响覆盖；错误摘要/孤儿/重复父ID拒绝 |
| A3 完整字段与SIM披露 | S1的六组件 | 键/类型/枚举与第3/5节逐项一致，所有原件source=SIM；无真实签名、目标/异常/gold字段 |
| A4 ID和对象关联 | S1批次/事件/材料/登记 | 六事件前驱、包装绑定、采样及运输段均同对象；按本稿独立ID向量/规则核对，不用生产函数生成期望 |
| A5 原件与文件摘要 | S1登记和主记录 | 两类摘要字节口径正确；至少以本稿D4/D5字面量摘要作黄金向量；篡改已发布字节后复用拒绝且不重写 |
| A6 时间合法性 | S1输出及非法配置调用 | 固定时间逐值一致且满足不等式；τ早于封存、区间倒置、样本/检测越界、登记早于签发等均退出2 |
| A7 零售与历史有效性 | S1原件/S2核查 | D8半开区间覆盖τ；其他7份不被加TTL。无温湿度/食品限值或当前品质自动补字段 |
| A8 来源与授权 | S1 policy/记录及错误配置 | 每kind/事件有恰一获权签发主体，收录主体分开；身份模式显式模拟。主体/种类授权错配不能生成成功包 |
| A9 R1材料组合 | S1原件、S2私有参考 | sample+report对象/事件/sample/project一致；参考从原文得Supported；不把报告pass或六阶段齐备直接当答案 |
| A10 参考独立性 | S2来源/推导及人工例 | 不导入生产函数/复制生产状态，记录原件和登记定位；手算例与参考一致。接口无异常标签/expected-status输入 |
| A11 输入隔离 | S1产物与依赖清单 | 只加载目录允许投影与配置/协议；源metadata的关闭字段哨兵不复制，项目中私有目标/评论/模型结果变更不改变生成组件，不调用08会话 |
| A12 新鲜复现 | S1两次新空root、S2参考 | 六稳定文件逐字节和SHA相同，snapshot_id相同；参考稳定行相同。实际运行日志/主记录时间不要求跨目录相同 |
| A13 一致复用与旧版本保护 | S1重跑及冲突/路径夹具 | 一致时返回旧主记录且不改字节；变配置/代码/依赖或损坏组件不覆盖；既有旧版本哨兵/08版本不变；junction/路径逃逸无额外写入 |
| A14 正式接受门禁 | S1主记录+外部验收记录 | prepared不等于accepted；只有完整独立核查、复现、保护、公共测试、两轴无阻塞才归档接受记录，正式联合/样本充分性仍非通过 |

小目录账户为零，不伪造真实用户；需要不同目录/摘要/数量时，由受信任测试夹具提供相应绑定，输出在.tmp，明确不是正式数据。字面量/手算期望在运行生成器前给出，不能把首次生产输出保存成期望后宣布通过。全量真实数据不再取样凑覆盖，所有关联/摘要/时间均独立核对。

本工单只验收正常生成与参考所需行为，不新增材料查询工具、生产通用四态内核或异常扰动接口来“方便测试”。09异常语义不丢失，完整生成/分配及其验收在11展开。

## 9. 修改范围与确认后执行顺序

### 9.1 允许的最小修改范围

| 文件/区域 | 目的 |
| --- | --- |
| prepare_data.py | 只加sim_normal阶段分派、sim-config参数和该阶段合法参数/错误返回；旧阶段语义不改 |
| 新sim_normal.py | 固定正常profile的加载、生成、关联/字节校验、稳定发布/复用；不引入通用规则引擎 |
| 新config/sim-normal-1.0.0.json | 用户确认后才落盘本稿完整配置 |
| 新tests/test_sim_normal.py | S1公共行为夹具；S2必要外部行为可同文件组织，不导入生产内部函数 |
| 新diagnostics/verify_sim10.py与verification证据 | 独立R1及全量/新目录复现/保护核查、RED/GREEN和两轴报告；不把它变成另一准备工具 |
| 新docs/data-sources/normal-sim.md、records/sim及data/sim相关目录 | 使用合同、正常原件、主记录、私有参考与接受清单 |
| 工单10、map及必要确认/验收说明 | 记录授权、实际结果和后续边界；不回改冻结09/06—08/原研究材料 |
| .gitattributes中的3个精确文档路径 | 本轮归档时固定09原草案/确认记录及10确认稿字节，避免Git自动LF/CRLF转换使已绑定摘要失效；其他路径规则不改 |

不修改preference_tasks/preference_access/text处理、06清洗、07分组或已有数据/配置；发现无关问题只记录。现有Thesis Conda路径和Python3.13.16标准库足够，依赖安装0。所有后续项目代码/测试/验收均显式conda run -p项目内Thesis，不用base或其他项目环境。

### 9.2 实施与固定基线审查

1. 用户一次确认本稿后，将确认与本稿SHA-256归档到工单10，再写正式配置。先记录原稿/上游/旧版本保护清单，固定比较起点仍为755f277…。
2. 按mattpocock-skills:TDD，在S1/S2批准的Seam逐个行为执行RED→最小GREEN，保存真实失败与通过输出；不横向先堆全部测试，不导入内部函数造期望。
3. 适用公共行为通过后运行现有197项加新增测试的一次完整回归，报告实际总数；不预先虚构新增数或“全部通过”。用固定提交候选供Standards/Spec并行审查，命令为`git diff 755f277e9a971a517e8b4a5bb94e747b46f3f640...HEAD`，同时保存实际commit列表和HEAD。
4. 两轴分别审查本工单变更：Standards依据AGENTS/项目约束与技能基线，Spec依据已批准本稿、09归档和工单10。只看本次diff，不全面重审06—08；分别归档原报告及阻塞处理，必要修订继续TDD且不移动比较起点。
5. 无阻塞后从明确代码状态运行真实1,494商品正常生成；独立程序全量核查、生成R1参考，执行新空root复现与旧版本/原材料保护。若此时发现实际缺陷，只按必要范围修复/补测/复审，保留旧产物，不能覆写失败版本凑验收。
6. 条件全部满足才写接受记录和实际验收结论；只关闭正常SIM组件，不进入11/12或模型/账本运行。所有摘要/数量/运行时/审查HEAD均来自实际执行。

当前尚无sim_normal实现、测试、正式配置、生产器摘要、实际新产物或接受记录，不能将本稿示例中的数值当作已验收结果。

### 9.3 明确留后续的事项

| 后续范围 | 本轮处理 |
| --- | --- |
| 工单11 | 异常类型的生成/分配、扰动对象/比例/强度/种子/重复、状态变更及无关对照；本轮不分配或定规模 |
| 工单12 | 正式主任务/比较、K/预算/融合、样本充分性、场景权重和统计相关性；1,603账户及分组仅继承事实 |
| 联合实现 | 新请求合同、根任务配对、材料list/read工具及实际模型会话分派；08仍保持原schema/空工具 |
| 账本实现 | 数字签名/真实身份、集中式日志/Fabric、区块/交易/有效提交回执；本地收录不叫已上链 |
| 未启用主张 | 数值检测/储存合规、采样新鲜度窗口、现实认证、当前品质；不补阈值，不以本配置暗示已达标 |

## 10. 一次集中确认点与本轮自检

C1—C11不再重复请求确认。请集中确认下列**新增的具体实施合同**，或按编号指出修改：

| 编号 | 本次新增确认内容 |
| --- | --- |
| I1 | 第2节完整JSON：固定τ/封存、六阶段及八材料时间、零售半开区间、8个主体授权与模拟枚举事实 |
| I2 | 第3—5节完整字段/类型、ID/业务version=1、精确字节及原件/文件摘要、15条登记和快照core规则 |
| I3 | 第6—7节R1专用独立参考、六稳定组件、prepared与独立accepted分开、私有参考和主/接受记录合同 |
| I4 | 第8节唯一prepare_data.py Interface、三必要参数、退出码/原因码、S1/S2外部测试Seam及A1—A14验收行为 |
| I5 | 第9节文件修改范围、无新依赖、Thesis环境、TDD逐行为、755f277固定比较与两轴分别报告 |
| I6 | 第9.3节后续边界；不将任何未启用数值/当前品质主张或11/12/工具/账本参数视为已批准 |

本轮已完成09确认归档及这一份合并确认稿；没有另写零散配置提案或要求下一轮再补基本时间/字段。配置所需的值已经明确，后续范围中的参数仍不属于正常生成前置。

本轮只做文档内虚构例及字节/日期核算，未执行项目Python、安装依赖、运行项目测试、生成批量SIM或调用模型。原09草案/来源笔记、06—08代码/配置/数据及论文/上游材料保持只读；本次既有文件只改09工单、spec确认更新、map状态及归档字节保护的.gitattributes。文档自检结果在交付时按实际核算说明。

交付前文档核对：1个完整配置对象/14个顶层键解析通过；1批次、6事件、8材料共15个示例的ID、对象、来源授权及时间关系核对通过；R1两个字面量摘要一致，协议/目录记录绑定摘要一致，2处本地链接可定位，代码块闭合。767项只读保护文件的前后汇总摘要一致；正式config、sim_normal.py、对应测试及data/sim目录均未创建。这些是文档核算，不是项目实现或验收测试已通过。

**停在此处，等待I1—I6一次集中确认；确认前不写正式sim-config、不新增实现/测试、不生成正常SIM包。**
