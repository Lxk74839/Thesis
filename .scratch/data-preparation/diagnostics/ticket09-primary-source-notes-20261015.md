# 工单09第一阶段：原始来源核查工作笔记

日期：2026-10-15（Asia/Shanghai）。状态：研究笔记，供合并审核草案使用；不冻结规格，不修改工单08，不生成SIM数据。

核查范围为影响协议选择的6项原始来源。全部通过原出版机构、标准组织或作者预印本的全文阅读相关章节；以下只记录与本轮问题直接相关的内容，未作全面综述。项目论文正文、上游数据、真实评论及评价留出数据均未读取；未运行项目代码。

## S1：GS1 EPCIS 2.0——对象层次、事件时间与登记时间

- **题名/版本/机构**：*EPCIS Standard*，Release 2.0，Ratified Jun 2022，GS1 AISBL。
- **原文**：[官方固定版本入口及全文](https://ref.gs1.org/standards/epcis/2.0.0/)。已读取：§7.3.3（What）、§7.3.8（Instance/Lot master data）、§7.4.1（EPCISEvent）、§7.4.1.2（ErrorDeclaration）、§7.4.3（AggregationEvent）、§8.1.1及§8.2.2（认证、授权与删减）。公开可读，无本次访问限制。
- **支持**：商品类主数据与批次/实例信息不同；业务事件发生时间`eventTime`与仓库收录时间`recordTime`不同；更正保留旧事件并增加记录；查询结果可受授权删减。[来源](https://ref.gs1.org/standards/epcis/2.0.0/)
- **不支持**：标准未规定本项目五级链、固定六阶段或每商品批次数。`AggregationEvent.parentID`指物理聚合父对象，不能直接解释成商品目录父键`parent_asin`。
- **设计建议**：借鉴层次与时间语义，保留本地外键；不声称EPCIS合规。真实评论仍归父商品，SIM事件另有场景时间；目录父子关系不伪装成实体聚合。

## S2：W3C PROV-DM——材料来源、责任、修订与失效

- **题名/版本/编辑机构**：*PROV-DM: The PROV Data Model*，W3C Recommendation，30 April 2013；编辑Luc Moreau（University of Southampton）、Paolo Missier（Newcastle University）。
- **原文**：[固定版](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)。已读取：§5.1.1–5.1.4（实体、活动、生成、使用）、§5.1.8（失效）、§5.2.2（修订）、§5.3（责任及委托）、§7（有效溯源）。公开可读，无本次访问限制。
- **支持**：可以表达材料由何活动产生、由谁负责、从何修订、何时失效。PROV描述可用于评估可信性，并非来源事实真实性的证明。[来源](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)
- **不支持**：不自动确认签发资格、数据使用授权、材料真伪或食品阈值；也不规定本项目版本优先级。
- **设计建议**：材料、生成/核验活动、签发/登记主体分开标识；修订建立显式前后版本关系，撤销保留历史。不得将PROV的`Agent`误说成本论文六角色的来源依据。

## S3：NISTIR 8202——摘要、签名与区块链保证的边界

- **题名/年份/作者**：*Blockchain Technology Overview*，NISTIR 8202，October 2018；Dylan Yaga、Peter Mell（NIST），Nik Roby（G2, Inc.），Karen Scarfone（Scarfone Cybersecurity）。
- **原文**：[NIST元数据](https://csrc.nist.gov/pubs/ir/8202/final)、[官方全文](https://nvlpubs.nist.gov/nistpubs/ir/2018/NIST.IR.8202.pdf)，DOI：10.6028/NIST.IR.8202。已读取：§3.1（摘要）、§3.2–3.3（交易和签名）、§7.1（不可变性边界）、§7.3（Beyond the Digital；正文第36页）。公开可读，无本次访问限制。
- **支持**：摘要比较用于发现字节变化，签名核验依赖密钥；链外人或传感器输入可能错误，登记本身不能证明现实交付或测量发生。[来源](https://nvlpubs.nist.gov/nistpubs/ir/2018/NIST.IR.8202.pdf)
- **不支持**：摘要相符不等于材料陈述为真；本地模拟登记也不等于已部署分布式区块链。
- **设计建议**：分别报告“材料完整性/登记核验”和“请求声明的证据判断”。后续链适配保留登记主体、对象、摘要与状态变更；链下原文仍须能够依法取得和人工核对。

## S4：W3C VC DM 2.0——签发者、有效期、撤销及授权边界

- **题名/版本/机构**：*Verifiable Credentials Data Model v2.0*，W3C Recommendation，15 May 2025；编辑Manu Sporny（Digital Bazaar）、Ted Thibodeau Jr（OpenLink Software）、Ivan Herman（W3C）、Gabe Cohen（Block）、Michael B. Jones（Invited Expert）。
- **原文**：[固定版](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)。已读取：§2（verification定义）、§4.7–4.10（签发者、主体、有效期、状态）、§5.1、§5.3、§5.9、§5.12及附录A.6–A.10。公开可读，无本次访问限制。
- **支持**：凭证核验不蕴含声明真实；有效期和撤销状态可显式表达；外部资源摘要不符应报错；混合材料前须确认对象一致。信任、授权讨论部分是非规范说明。[来源](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)
- **不支持**：不提供完整RBAC/ABAC方案，也不统一规定食品证据有效期或签发者可信等级。
- **设计建议**：借鉴语义，不宣称VC合规。§5.3对其`relatedResource`机制建议SHA-384为最低强度；本轮保持08的SHA-256及其字节口径，不据此反向修改已验收接口。

## S5：FEVER——证据支持、否定、不足与独立标注

- **题名/年份/作者机构**：*FEVER: a Large-scale Dataset for Fact Extraction and VERification*，NAACL-HLT 2018，pp.809–819；James Thorne、Andreas Vlachos（University of Sheffield），Christos Christodoulopoulos、Arpit Mittal（Amazon Research Cambridge）。
- **原文**：[ACL出版页](https://aclanthology.org/N18-1074/)、[论文全文](https://aclanthology.org/N18-1074.pdf)，DOI：10.18653/v1/N18-1074。已读取：摘要、§1及Figure 1、§3.1–3.4（生成、标注与人工验证）。公开可读，无本次访问限制。
- **支持**：三标签为Supported、Refuted、NotEnoughInfo；正反判断应附必要证据组合；标注分离于声明生成，标注者不知道声明所改写的原句。[来源](https://aclanthology.org/N18-1074.pdf)
- **不支持**：没有Conflict第四态；未定义供应链材料授权、撤销或有效期；不直接证明本项目参考答案独立性。
- **设计建议**：借鉴“证据能否推出命题”的思路；Pending与Conflict由本项目另定义。参考答案需从原材料、登记事实及请求重推，并记录证据定位；不得复制异常标签或生产核验状态。

## S6：Ji et al.——预测时点可用信息与时间泄漏

- **题名/版本/作者机构**：*A Critical Study on Data Leakage in Recommender System Offline Evaluation*；arXiv:2010.11060v4，30 October 2022（首发2020）；Yitong Ji、Aixin Sun、Jie Zhang（Nanyang Technological University），Chenliang Li（Wuhan University）。
- **原文**：[固定版本元数据](https://arxiv.org/abs/2010.11060v4)、[作者全文](https://arxiv.org/pdf/2010.11060v4)。已读取：§1、§4.3、§5及Figure 9（Timeline Scheme；PDF第19–21页）。公开可读，无本次访问限制。
- **书目信息边界**：arXiv页面列出期刊记录为*ACM TOIS* 41(3), 2023, Article 75，DOI 10.1145/3569930；v4 PDF页脚仍有2022及占位排版。本次依据固定预印本，不将该页脚当正式期刊卷期。
- **支持**：推荐时不得使用该时点尚不可得的交互或商品；仅按用户各自留末次交互不足以保证全局时间隔离。[来源](https://arxiv.org/pdf/2010.11060v4)
- **不支持**：不能证明从历史评论推断的约束就是用户真实明确意图，也未规定本项目SIM请求的构造方法。
- **设计建议**：沿用08已确认的输入隔离；禁止目标交互、目标评论/评分及模型结果进入请求或异常构造。历史推断与研究者构造分开标记；SIM核验时间不冒充真实历史时点。

## 跨来源结论：本项目必须自行选择并披露的规则

以下是本项目方案建议，不能表述成上述标准或论文的强制要求。

1. **一父商品一正常SIM基准批次属于简约工程选择。** 本次核查的6项来源都没有要求“每个父商品必须恰有一个正常SIM批次”，也没有证明其最优性；这是有范围的核查结论，不能扩大成“所有文献均无此要求”。推荐理由是覆盖父商品、减少无关自由度并方便逐项人工核对。是否正式采用仍待用户确认。
2. **数量影响只作代数说明。** 若有`N`个父商品，一个基准批次对应`N`批；每父商品`k`批对应`kN`批。六阶段各置一个事件时分别为`6N`、`6kN`事件。新增同父商品批次不会自动变为新的独立真实商品或真实用户偏好样本；正式样本设计留工单12。
3. **必要替代方案由问题驱动。** 只有要检验同商品跨批次差异时才需多基准批次；同一基准的证据扰动可用独立场景版本表达，是否另增批次要依“物理批次改变还是材料视图改变”区分。异常类型、分配及规模留工单11。
4. **五级链与六阶段是项目协议。** `parent_asin → SIM batch → lifecycle event → evidence material → registration`需显式外键与SIM来源；材料允许被多个声明引用时，引用范围须逐条可见。保持父商品层真实评论与批次层合成供应链的语义边界。[S1](https://ref.gs1.org/standards/epcis/2.0.0/)
5. **证据组合按请求声明确定。** 六阶段是履历结构，不自动成为每个请求的全部硬门槛。支持所需材料组合、关联对象、适用时间和相关授权快照范围完整枚举应由项目协议写明；不是找到一份正向材料即可忽略其他适用材料。[S5](https://aclanthology.org/N18-1074.pdf)
6. **失败核验不是有效否定。** 缺失、无权限、摘要不符、对象错配使材料不足以被接受，不直接推出请求声明为假。Conflict只用于同对象、同声明、同适用时间下仍然有效的支持与否定并存且未按明确修订/撤销关系消解；此处是本项目拟议规则。[S3](https://nvlpubs.nist.gov/nistpubs/ir/2018/NIST.IR.8202.pdf)、[S5](https://aclanthology.org/N18-1074.pdf)
7. **材料寿命不等于观察结论寿命。** 文件可一直留存供审计；它能否支持某请求，仍取决于声明范围、观测区间、签发主体、版本/撤销及请求时点。过期也不自动变成有效反证。[S2](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)、[S4](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/)
8. **未找到通用数值依据。** 六阶段证据有效天数、温湿度/检测阈值、材料数量与强度等级，不能从本次来源直接得到统一默认值。应逐项列为研究规则建议或待决；存在请求明确给出的合成阈值时，需标“研究设计构造”，不得写成食品安全法定限值。

## 本子任务自检

- 已核查6项原始来源并给出固定链接、阅读位置、支持范围和访问情况；无二手解读作为技术结论依据。
- 已明确“标准语义借鉴”“项目最小设计”及“无来源数值依据”的区别。
- 未冻结协议、安装依赖、运行项目代码、修改08、读取留出/评价数据或生成批量SIM。
- 未核查父任务另行负责的路线论文；本笔记只作为合并审核草案的来源支撑，不代替用户确认。
