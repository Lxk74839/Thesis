# 推荐运行专项：本地协议与公开组合接受

日期：2026-10-17（Asia/Shanghai）。状态：**合同内本地实施、验证、独立审查及分项接受完成**。

固定BASE：`6ac5c2cddde6973b9743e3e17f5c264840f42854`。授权归档：`2afd1d4`。最终实现提交：`3d970b775875197142c18e6d84e9709f49a155b3`。先前候选`c0267785ed6b920e5717ad5d9b4bacc820098bc8`、`dbb127cbda336d635bf27d278c55c8138dafe1ca`及原审查/失败全部保留；本接受提交只归档文档和工单，不改变已审代码/测试。

## 原稿与范围绑定

| 原稿 | 原始字节SHA-256（最终核对一致） |
| --- | --- |
| spec.md | `8982a92d8541f8bc52b31824924527abd66b87910cde4e13124abc27b90b6fa8` |
| confirmation.md | `04d4bed92e1c4e63f6a2f61185ede7e14d499a3c4ad1954cff02a3de415fa9ec` |

依据[独立授权](authorization-20261017.md)实施CRR-01—CRR-09、P1/P2/P3和H01—H15。沿用F1—F3、09及已接受接口，不重开数据路线或上游接受。仅修改既有evidence_access.py的共享根预算衔接；两个新生产模块、新公共测试、三份诊断和专项文档均在§9白名单内。标准库、既有Thesis Conda Python3.13.16，无依赖/SDK/tokenizer安装或配置变更。

## 分项接受

| 条件 | 实际结果及证据 |
| --- | --- |
| A01 Interface/TDD授权 | 2afd1d4先归档；P3→P2→P1逐公共行为RED/GREEN；[映射](verification/tdd-and-interface-map.md)及后续[集中修复](verification/repairs-c026778.md)、[收口](verification/repairs-dbb127c.md)保留原始失败。已有行为首次即GREEN如实记录，未伪造RED |
| A02 R/S/M及六角色职责 | R完整列举/读取/评估、模型0；S单身份具同样分析/画像/工具/反馈能力；M管理dispatch、追溯工具请求、用户H字段定位/未知、取证评估后的农产品属性/单位/值/引用及适用Q、核验/最终提交均有实际Adapter消息。只有验证通过才登记角色完成，final检查完成向量 |
| A03 宿主状态与停止 | 完整C/b固定、稳定队列、当前候选/游标、显式assess实际G；必要首10停止，质量按固定测试前缀。未闭合/未评估不得跳过。非空发布、完整C合法空、局部空阻断、预算/时间未完成及协议/模型/来源失败区分；关闭游标不重开 |
| A04 同一根账 | 工具/角色/候选/模型/程序/重试同账同锁；普通阶段保护final，最终提交/封存有意图及结算；cache/reasoning不重复；未知保留占用、已知尝试照计、停止免费重试。实际超预留/迟到/失败留账，零占用pending也不算结清；既有E1兼容且旧动作fixture限制保留 |
| A05 整表门禁与发布 | 资格/数量/ID/批次/引用字段/版本/回执/封闭理由/完整排序/预算均核对；引用采样与报告还须真正匹配支持谓词。门禁无补取、无重排或改字；最多一次Issue绑定修订。畸形首稿/修订、坏尾/错序/自由断言及提交/审计失败/迟到均不得发布，旧记录不覆盖 |
| A06 Q组件 | full/no_quality/mean_quality同实际A/G/完整C/b/H/融合/重复/游标/终态/发布文件SHA；H09字面分数、mean=.675/分母4、G外raw q原例通过；full等于实际交付。失败三个组件共同anchor_failed并标F1后续规则，空C零分母；无新增I/O/模型/G/理由 |
| A07 消息Adapter | 封闭有序消息/工具call_id/参数/响应/usage/错误，额外身份/path/旧call复用/非法数值等拒绝；原始输入意图在调用前fsync，返回/usage存同根。未绑定真实模式在transport前拒绝；本轮只有scripted/synthetic/public_fixture_only，provider请求0 |
| A08 组合、兼容、保护、资源 | 110最终**105例全部通过（新48+既有57）**。111/112精确绑定3d970b7的13公开组合、170文件及12源码/合同/诊断摘要独立核对通过；113保护2013文件changed=[]。累计资源及所有失败结清，见下表 |
| A09 双轴审查 | 同固定BASE和同精确候选，两原独立代理分别定向复审。[并列汇总](verification/review-summary.md)：最终Standards阻塞0/非阻塞1、Spec阻塞0/非阻塞0；原三项阻塞已关闭，模板重复的非阻塞建议仅记录 |

接受层次分别为：共享根账/宿主协议、公开ModelAdapter与真实本地人工原件的组合、旧E1及受影响公共接口兼容。没有把这三项写成真实供应商、自然协作或效果接受。

## 最终证据与资源结算

审计根始终为`data/recommendation-runtime-audit/20261017/`，未换账、重计时或扩额。`.tmp/recommendation-runtime/`仅公开临时fixture。全部项目Python/子进程由同一Windows Job守护发起；代理仅静态审查，没有另起Python。

| 项 | 最终结算 |
| --- | --- |
| Python累计墙钟 | **479.977036000011秒 / 1800秒**，113次守护记录，包含50次非零退出（RED及已记录fixture/启动器失败）；80未实际跑测试不作为通过证据，费用照计 |
| 内存 | Job峰值1,391,501,312字节；加64MiB守护预留共**1,458,610,176字节（约1.36GiB）/4GiB** |
| 未结算资源 | 无resource-inflight.json；没有中断余量重置、换目录清零或自动扩额 |
| 最终公共例 | normal-R/S/M、quality-four、stock-feedback、necessary/quality-twelve、unassessed-quality、unknown-usage、full/prefix-empty、bad-order、bad-source，共13例 |
| 只读保护 | 2013文件、23,359,006,767原始字节；前/审查前/最终hash复核；论文、研究、全部既有接受及非白名单文件changed=[] |
| 实际外部执行 | 真实模型/供应商/API/付费0；没有加载真实开发/测试根作为推荐输入，没有T0/P1、效果统计、数据重生成、链部署或工单15冻结 |

最终`final-evidence-manifest.json` SHA-256：`ff06f18d201379de8eda6fa7fcb7fc12625c484367f5171458a8cfab7720bdb9`。该文件绑定全部113份原始运行输出的SHA、资源账、110最终测试、111精确候选组合源码/输出、112独立核对及113保护输出；`delivery-3d970b7.json`含170文件逐项字节/SHA与12个源码/合同/诊断摘要。所有公开result.binding及versions中的implementation_candidate均核对为3d970b7，已审实现与工作区源码无差异。

发布记录含原草案/A/G和提交前预算快照，权威结束结算在同根budget.jsonl；组件存audit.json并指向完整publication.json摘要。失败/迟到尝试及失败审计分别保留，无成功入口。独立checker只用标准库读取公开原件/消息/账/交付和字面期望，不调用生产运行/预算/核验函数生成答案。

## 保持待绑定

`provider/model/version/settings/tokenizer/official_capability/pricing`仍unbound；`execution_budget=null, execution_authorized=false`。正式L、根limits、最终预留和F3容量未冻结。公开合成输入单位为完整messages/tools的UTF-8字节，不能当官方token计数或计费；实际供应商请求0另列。

精确候选公开例的合成Adapter尝试数为R单候选0、S单候选10、M单候选10、质量4候选M25、质量12候选M65、库存反馈M12。全部按真实脚本续轮实计，**不证明7/10/12目标或64候选容量可行，不是自然反馈/模型协作收益**。后续真实供应商、分词/能力/价格证据、获授权T0与可执行预算冻结、真实运行/评价、链及15各自仍需适用绑定和授权。本轮无剩余合同内实施阻塞。
