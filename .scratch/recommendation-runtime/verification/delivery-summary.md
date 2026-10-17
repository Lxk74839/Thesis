# 本地运行器交付核对

固定审查起点：`6ac5c2cddde6973b9743e3e17f5c264840f42854`。授权归档提交：`2afd1d4`。合同/确认表原稿保持只读；实现候选与最终接受提交另记独立审查及接受文件。

最终状态：[分项接受完成](../acceptance-20261017.md)，实现3d970b775875197142c18e6d84e9709f49a155b3。105例全通过，精确候选13公开组合/170文件独立核对及2013文件只读保护通过；[两轴复审](review-summary.md)各0阻塞。下列82/89/91/92资源数字是首候选历史，最终结算479.977036秒、进程树峰值加守护约1.36GiB；全部原失败/组合/账保持。画像已落实H字段定位与取证评估后属性/Q/引用职责，首稿与修订均先验证封闭根形态，引用组合另核实际支持谓词。

## 文件范围与依赖

| 类别 | 精确文件/目录 | 影响 |
| --- | --- | --- |
| 唯一既有生产修改 | evidence_access.py | RootBudget及E1可选共享注入；同账、时间、重试、预留、日志及投影；独立旧E1路径兼容 |
| 新生产 | recommendation_runner.py、model_adapter.py | R/S/M公共运行入口；封闭脚本模型协议。无外部SDK或默认供应商 |
| 新公共测试 | tests/test_root_budget.py、test_model_adapter.py、test_recommendation_runner.py、runtime_fixtures.py | 人工事实原字节、模型/故障Seam、公共Interface及整表/结算/提交反例 |
| 新守护/独立核对 | diagnostics/run_check.py、protect_scope.py、check_delivery.py（本专项目录下） | 同一累计Python/Windows Job账；hash只读保护；标准库独立公开交付检查 |
| 新专项文档 | verification/、acceptance-20261017.md；本专项map与工单更新 | 原始双轴审查、修复/定向复审、分项接受、证据及待绑定边界 |
| 忽略产物 | .tmp/recommendation-runtime/、data/recommendation-runtime-audit/20261017/ | 公开fixture、消息/原件/失败、根账、发布与独立逐文件清单；不进入Git |

Python仍为既有Thesis Conda 3.13.16，仅标准库。joint_access、joint_tasks、evidence_verification、quality_fusion、recommendation_actions、environment/config及所有旧测试均不改。论文、研究材料、上游数据/来源/接受与工单15均只读。

## 实际行为与限制

R列举并读取当前候选全部登记及依赖，再由原8生产核验显式准入；模型调用/token/费用为0。S一会话承担全部职责。M六角色经同一ModelAdapter实际请求/返回，推荐管理dispatch，生命周期追溯提出工具请求；转发注明源消息，E1回执含actor。失败完成向量不补造。原动作入口公开fixture限制未放宽。

固定完整C和b队列；当前候选未闭合不推进。必要臂首10合格停止，质量臂处理宿主批准的固定前缀（本轮只用人工测试值）。合法空须完整C。R/S/M均保留实际A、显式G、草案、Issue、一次修订、终态及发布失败证据。

根账在setup前启动，覆盖候选、角色、模型、工具、重试、程序及提交/封存；普通阶段保护final。未知不填0，已知尝试照计，未知占用保持且停根；只允许同请求权威回执补结算。零占用pending也不算结清，final只容许自身当前意图。实际超预留及迟到保留实数并停止。日志排他创建，关键模型输入在调用前fsync，返回/usage入同根日志。

草案理由限四种原子主张和字面模板，引用须实际A/正确对象、版本、回执及字段。库存另需正常Q同属性z支持；基础分绑定安全输入指纹和12位文本。模型/程序Issue各自保留，修订仅在可见Issue pointer内；程序不改字或补取。final检查整张列表及完整顺序、G、引用和预算。提交或审计封存失败/迟到不发布，保留失败文件；旧记录不覆盖。

质量M的full/no_quality/mean_quality共享冻结A/G/完整C/b/H/融合/重复/游标/终态，成功锚点引用实际发布文件SHA。full必须逐位等于实际交付；失败组件共同anchor_failed，附F1后续评价规则，不读取参考或填指标。控制列表不搬用模型理由。

## 审查方式

按mattpocock-skills:code-review，先固定候选Git提交，再由两个独立代理并行静态审查同一`git diff 6ac5c2c...<candidate>`及提交链。Standards依据根AGENTS.md、docs/agents约定、已授权范围与技能中的smell baseline；Spec依据本专项spec、confirmation及独立授权。没有CODING_STANDARDS.md/CONTRIBUTING.md，不虚构规则。

两轴原文分别保存，不合并/重排发现；真实阻塞集中修复、公共复现与定向复审。仅判断性非阻塞建议记录，不借审查扩大范围。独立审查和接受完成前，不把工单记resolved。

## 验证证据入口

- [公共TDD与H01—H15映射](tdd-and-interface-map.md)。原始失败与通过输出、守护账均在新忽略审计目录。
- 82：97例通过，含新40、既有E1/E2 43、动作9、Joint 2、Q 3。后续新增行为另有85→86（pending final）及87→88（冻结融合绑定）定向证据。
- 83/84：公开13组合/170个产物文件独立核对通过。加强门禁后的v2组合及最终源码摘要另存，不覆盖v1。
- protection-before保护2013个文件、23,359,006,767字节，后续after检查只做hash比较，不解析真实研究/评价内容。

候选固定前收口：91新接口42例全通过；与82保留的57个既有兼容例合计99个不同适用例。89/90的v2公开13组合和170文件核对通过；92对2013个受保护文件复核，changed=[]。此时累计Python296.9813184秒，最高Job提交内存991,113,216字节（另有64MiB守护预留），全部失败均在同一账内。

实际provider/model/API/费用均0。`provider/model/tokenizer/capability/pricing=unbound`，`execution_budget=null, execution_authorized=false`。本地合成账、脚本调度、反馈改字、12候选停止都不证明真实模型能力、自然协作收益、F3容量或正式L可行；T0/P1、真实开发/测试根推荐、统计、部署、工单15冻结均未执行。
