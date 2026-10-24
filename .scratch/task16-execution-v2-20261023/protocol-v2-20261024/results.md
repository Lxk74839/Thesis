# Task16 协议v2修复与V00运行结果

本轮完成已定位问题的v2实现、离线回归和固定候选双轴审查，并实际启动了授权的独立运行。8次medium/full业务探针全部成功；正式特征阶段出现新的协议反例及1条发送状态不明请求后执行安全Stop，worker已退出。B0/I1主对照尚未启动，V00主对照未完成。未增加参数遍历、探针或自动重试，未启动Q1/Q2或消融。

运行于日本时间2026-10-24 13:15:06启动，约13:20:38停止派发。本次停止的原因是业务协议及未知发送，原18:28:03派发截止和20:28:03总截止仍有效，没有延期、重置累计账或缩减16人面板。

| 验证项 | 本轮实际交付及边界 |
| --- | --- |
| 协议与数据隔离 | macrec-agri-v2按interpret/action/User/Items及操作定义原生业务字段；严格JSON拒绝包装、重复键、非有限数；interpret仅见当前请求，历史偏好由User处理 |
| 偏好校验 | 修复“As an oats lover”等明确词形；保留原文、属性支持、否定、冲突及父商品去重；无支持项过滤并留原因，允许空画像，Probe/Main共用语义 |
| 真实14条离线回归 | SHA只读引用；原有6通过/8失败判定保留。162efcef1b和558ef1a786仅在离线夹具剥包装验证原因，没有升级旧失败或冒充新模型成功 |
| 影响测试 | 46项PASS，15.148秒；红/绿轨迹和impact-regression.txt留档，复用其余算法验收 |
| 固定候选审查 | base 8004ae8aba1b40b662001c5078521074c6509674 → candidate 6fdce71f14f733857c76b9f71d9d28634051ea32；独立Standards/Spec均PASS。随后真实正式分支暴露下述缺口，审查通过不等于生产运行成功 |
| 版本与保留 | v2计划SHA 06233b5f52e6ee5db7dc580a117b3b9c301aa7246c441a68f9cc589d257e13da；新namespace/依赖/health/绑定；旧完整计划、旧V00、响应、错误和绑定全部保留 |

两个既有探针用户各完成interpret、action、User、Items一次，共8次真实新增物理请求；配置统一medium/full，没有四档遍历。探针验证指定Finish输出，但没有覆盖正式工具循环的全部状态约束。这一覆盖不足在特征阶段被实际反例证实，整体协议验收保持未完成。

特征16人状态为：成功0、协议拒绝6、调度耗尽1、发送未知1、停止时已开始但未形成终态2、尚未开始6。控制器显示features 8/16有结果记录，不能解释成8人特征成功。六组评分组件选参尚未完成，B0/I1主对照均未派发。

独立S5在停止后执行只读部分评价，文件为data/recommendation-runtime-audit/macrec-agri-dev-task16/evaluation/macrec-agri-v2/v00-after-stop-20261024.json，SHA b900497f5ac84c9ff80b716399c0b765a29563374324dcbc40b87c2df8cc15f7。它不是计划中的evaluate-v00阶段完成记录。

| 方法（固定16人） | 完成 | 已观察到的主对照失败 | 未启动 | HR@10 | NDCG@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| CB | 16 | 0 | 0 | 0.312500 | 0.178915 |
| B0 | 0 | 0 | 16 | NA | NA |
| I1 | 0 | 0 | 16 | NA | NA |

[paired-v00.csv](paired-v00.csv)与[paired-v00.json](paired-v00.json)逐一保留全部16个原root_task_id。有效B0/I1配对数为0；16条HR/NDCG差异均为NA，没有把未启动写成得分0。特征阶段错误不能算作已经观察到的B0/I1主对照成绩。

320人开发集共同召回Recall@200仍为68.75%（220/320）；100人的目标不在共同D中，未人为补入。因此共同召回后的HR上限受覆盖限制。固定16人面板覆盖为75%（12/16），不能替代320人的68.75%，也不能用来声称正式100用户评价完成或算法优越。历史100用户成绩曾被查看过，开发结果不具备全新盲测的独立性；本轮没有另加测试用户、重新抽样或修改历史结果。

下面保留具体原始响应及失败条件；详见[new-failure-evidence.json](new-failure-evidence.json)，含对应请求/响应路径、SHA、原文片段和原生Schema/宿主校验对照。没有改写、去重或修补模型响应：

| 原始响应 | 失败条件 |
| --- | --- |
| [d37290e5bf](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/d37290e5bfdb9e93aa9170669753017e7c9264f750127c400b44ee1220f2167e.response.json) | Search候选202项但唯一200，末尾重复20,20；macrec_evidence_scope |
| [d7e758b4fe](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/d7e758b4fef8bf03cce63275715936f1b7c01927bff54529ad485dc63b910a3f.response.json) | Lookup候选201/唯一200，重复0；macrec_evidence_scope |
| [f3c016ae37](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/f3c016ae3796f53871d8a2fddd7abaff323f24042357a88ad486cb9545e34b56.response.json) | Lookup候选200/唯一199，重复0；macrec_evidence_scope |
| [1b4586ec6b](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/1b4586ec6ba6ce6187c22509b78717bf774e48efc7965ff8071907c8110a680d.response.json) | Lookup候选201/唯一200，重复0；macrec_evidence_scope |
| [e0ce791b8c](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/e0ce791b8cda3551f68b0f0ed80398960499111b71ec0774e37c3180e1df6b8b.response.json) | Lookup候选300/唯一200，100至199重复；macrec_evidence_scope |
| [d1f23636d9](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/d1f23636d95ab336fa133354ba30aa58fa30db83223ff644bf0bff813ca0e7f2.response.json) | action=Info却返回data.preferences；macrec_business_response_shape:schema:$.data:fields |
| [8f5aff5db1](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/8f5aff5db15ff2e20ac33c30b522cb646a2089c075a22c3f7dbbecbda4c62ee4.response.json) | 管理者派发额度耗尽时仍请求User；macrec_dispatch_exhausted_or_invalid |
| [dce085fef9](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/macrec-agri-dev-task16/calls/dce085fef9c7837c28e3df9a461d5d6c465f4029a8af63ee324fc4485deb45e3.response.json) | local_timeout约21.077秒，send_state=unknown，HTTP状态及usage未知；不重发 |

前5条满足当前原生数组Schema，却违反宿主唯一性约束；第6条被不关联action/data的原生Schema接受，但不满足所选操作结构。后续必须补正式工具分支的结构关联和集合语义，不能靠扩大额度或事后修补响应通过。具体边界和后续验收条件已记录在[03-runtime-protocol-gaps.md](issues/03-runtime-protocol-gaps.md)；本轮不自行换新版本再派发。

发送状态审计特别说明：控制层原始累计计数为attempts=89、successful=88、failed=1、unresolved=0。successful仅表示传输收到响应，不等于业务成功。上述dce085fef9的原terminal保留failed，但原始HTTP诊断明确unknown，审计应按**1条未决、禁止重发**解释。新增protocol-bindings/macrec-agri-v2/uncertain-send-audit.json保存该差异，未删除旧记录以解除停止线。当前ready_for_execution只反映静态绑定检查，不能解释为这些业务缺口已经修复或可直接恢复。

资源实际为累计89次（旧14＋v2新增75），新增75为8探针＋67特征请求，失败尝试同样计入1504。已知累计输入1,426,222 Token（含缓存188,160）、输出28,634；v2新增已知输入985,888、输出18,867，另1请求usage未知。按输入¥0.045/M、输出¥0.225/M，已知非缓存输入与输出小计¥0.06215544；缓存价格、额外倍率、固定费用和未知请求费用分别未知，实际账单未知。

v2模型活动墙时312.069秒，请求时延累计601.981秒（并发累加，不当作墙时）；停止后独立S5区间已记入评价账，本地开发、等待、评价及重叠时间均保留原累计账。最终按[closing-ledger.json](closing-ledger.json)的as_of时间分别报告累计开发、模型、等待、评价、总耗时及新增字节，等待没有从24小时中扣除。原预算SHA 24d87b89be7d74bcc28d324d6ead5461a1ce563a69adad65706270206cbaa30b保持，新增空间仍按10GiB累计限制。

[source-protection.json](source-protection.json)核验全部通过：原材料/历史相关文件26、草案12、原文/作者固定源码16、旧运行不可变记录143、旧14条请求/响应28、当前封存代码及审查12。论文、历史100用户结果、原始材料、评分公式、候选和面板保持。Q1/Q2、消融、B0/I1主对照、六组评分选参及正式100用户验证未完成；Fabric未部署。没有依据宣称I1优于B0。

独立状态查询入口仍可直接运行，**本状态只查询，不启动或恢复**：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Work\Codex\Project\Thesis\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Status
```
