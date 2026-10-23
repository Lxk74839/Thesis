# 业务实施进度（接续用）

## 最新状态 2026-10-23 21:29:50Z

下方是历史工作记录，其中“尚待实施”已完成，不代表当前待办。三模块、320×18场景CB/CB-D/R、真实13阶段259槽、全部S1—S5及32业务参数/六评分组合已接通；没有真实API和执行授权。

首次候选14de991的Standards PASS、Spec三项发现见review-round1.md。RED/GREEN36—41已修复并由两代理对最终业务候选027000146dd4102cd05626fd74b01ccad23af093复审，两轴PASS。36条完整业务回归PASS（42.658s），控制无新增修改，复用25条影响回归PASS（24.920s）。真实run-plan/review-seal已封存，计划027d7f...共259单元/6944调用上限；Status ready=true、worker=false、调用0。EndDevelopment已完成，完整账见final-ledger.json和验收。原deadline/dispatch/10GiB与全部等待累计不变。

- 本轮base=0545af7ebbec4e72ac604a67ed6d5cd9811b4880，branch继承codex/task16-execution-v2-20261023。用户本轮已确认原方法/范围/S1—S5，仍禁止真实API。
- 原deadline=2026-10-24T11:28:03Z、dispatch=09:28:03Z、10GiB，不重置。已BeginDevelopment；开始时等待约6.5h已计入。当前真实调用0，无authorization/run-binding/真实plan/seal。
- 只新增macrec_experiment.py、macrec_recommendation.py、macrec_evaluation.py、tests/test_macrec.py和本implementation目录。旧草案12/原26保护文件不改。控制仅new_bytes清单加tests/test_macrec.py，实际业务资源计量缺口，未改控制流程。
- TDD 01—16：S1私有标签投影/三路内容手算/哈希文件输入；B0实际Search观察+反思二次解；I1语义+c短历史+生产q+定位修订；四消融（A-feedback字节相同前缀）；S5 rank2/failure/unresolved/全分母/配对bootstrap；真实EvidenceSession质量夹具(.6/.9)；selection CLI保留3权重/M50/100/200；真实320参考CLI导出安全cohort无test。red/green日志保留。
- 17 RED=实际prepare CLI未实现；实现后正在运行单项test_real_preparation...。exec session 20518，命令Thesis Conda unittest discover tests/test_macrec.py -k real_preparation，日志green-17.txt。子进程捕获stdout，准备完成前无进度输出；材料缓存目录当前已有首个约58MB文件。成功后须读结果，失败按日志修复，不再横向开启下一个TDD行为。
- prepare_files按accepted_sources读model roots/candidates/catalog，独立macrec_evaluation references子进程只解析dev身份/目标，导出safe dev-cohort；真实EvidenceTools冻结18场景1494商品list/read/assessment，保留claims/provenance/receipts和q C/T/A；select子进程比较三CB权重并选M；每根独立保存C/D/b及分量，global catalog一次保存；model-index内容版本来自content函数source摘要，后续加worker不改变内容版本。
- 18场景材料预估约1GiB，高于旧0.30GiB估计，结束后量测并修订预计峰值，10GiB上限保持。
- exposure-note.md记录一次错误Get-Content -First 1私有evaluation输出test目标；该根不在原100（rg exit1），不加入任何开发/实验，后续披露。此后私有数据只在独立评价进程过滤dev，字段形状只输出key。

## 尚待实施

1. S1真实prepare完整GREEN；S5 select补320全18场景CB完整C/共同D/原R离线成绩（只用生产observations作排序门禁，独立states只作真值），当前select已有三权重/V00组件/召回选择。保留全部尝试。
2. 真实模型接线：BusinessClient使用Session.invoke，existing provider.make_sender懒加载/零自动重试；四类业务probe32次low/medium与half/full；模型wire不能包含scene/paths/labels，128KiB请求/256KiB响应，role outputquota2048/4096/8192半档或完整。需压缩context（尤其全D匹配/证据/旧solution/trajectory），保留全候选输入和源原文，不能盲增控制限额。run_task模型接缝可注入BusinessClient用于离线原生Session测试。
3. execute_unit真实分支：offline校验缓存；parameters32；features16*18无反馈前缀（用A-feedback协议，不能冒充整系统）；组件lambda×tau六组由原特征重评分后独立进程选择，完整I1按选参重新跑；V00 B0/I1配对；Q1/Q2；三核心消融/无反馈；S/M辅助各16槽1/6次旧协议画像后真实场景回放；evaluation阶段独立子进程读取reference和observed，不读模型凭据。
4. 参数/组件选择要各自safe配置与私有指标分文件，模型运行只读safe参数；无有效业务配置或实测ETA超原剩余时间则停并报告，不缩样本/调候选/自动降档。失败burst继承原预算规则。所有模型请求经现控制器，未知绝不重发。
5. 真实plan13阶段槽数[1,32,16,32,1,32,32,16,16,32,16,32,1]和PHASES调用量6944；source roles panel/candidates/recall/evidence/model/algorithm_spec/upstream_lock/evaluation_contract；真实16名单和源绑定；所有slots均真实职责，不空占位。先proposal，不提前伪造review-seal；通过最终双轴后方写生产run-plan/seal，付费授权仍false/无grant。
6. 补必要S2置信去重/矛盾/标题不构成偏好/未知回退/非法排列/循环上限、S3快照变化、S5第11位/NA/旧指标同值、信息守卫、worker离线集成及必要影响回归；不重复控制全量验收，复用原24测试记录。
7. 固定新candidate（base必须本轮0545完整SHA），按已读1.3.1 code-review两个独立agent Standards/Spec并行；可以复用task16_standards_review/task16_spec_review，用户要求审查/skill明确授权这两个子代理。其余不主动派代理。最后交付代码/映射/测试审查/真计划配置就绪/V00预算/独立命令，原截止不改，不发API、不改论文、不部署Fabric。

20:31Z 续接状态：
- RED/GREEN18模型边界真实Session缓存；19真实execute_unit推荐；20离线18场景CB/CB-D/R；21B0实际分析+Search必需；22泛赞誉拒绝；23业务参数单形状；24无反馈特征/六组件网格/独立选参；25独立report CLI；26compact M六画像+三场景回放均已针对性通过。
- 首轮业务回归24条：缓存只按内容SHA索引会误将另一路径/临时目录当同源，已改为(path,SHA)。B0证据夹具补实际User调度，15条Collaboration回归通过。全量还需最终重跑。
- 新freeze_plan生成真实13阶段/259槽，但model_for选择、offline/evaluate操作、剩余时长门禁及错误突发仍待接通；不要将当前frozen_unsealed标生产就绪。
- 测试27 freeze_cli运行中，exec session24153：实际prepare选择扩展320x18 CB/fullC,CB/commonD,R；子评价PID3244（20:26:29Z起，单核CPU忙，约1GiB内存）。冻结用新content_code包含评价文件SHA，所以旧仅选择文件不会覆盖。test timeout1800。
- 伴随OS评价计时exec session77756：WaitForExit PID3244后写OUTPUT/activity/offline-evaluation-20261024.json；收集该session确认退出，不是模型进程。
- 所有真实API仍0，无authorization/run-binding/request-index。原总截止11:28:03Z、派发截止09:28:03Z、10GiB不变。原基线HEAD0545af7ebbec4e72ac604a67ed6d5cd9811b4880，尚未业务commit。

接下来必要工作：
1. finish27；补model_for(32核对全配置8形状通过、medium/full优先)及原窗口ETA否决，不缩样本；接offline/evaluate真实操作和单次输入校验钩子（若必须改控制，记录实际阻塞）。
2. 否定偏好未知不得当满足、短历史父商品去重/矛盾、配置有限性、定位引用验证、真实200候选/6维128KiB wire大小、材料更改拒绝复用、模型错误突发/未决传递的必要TDD。
3. 运行控制已有24条验收复用，仅新钩子/必要影响回归；新完整业务回归。核对protected26/原stage1草案12字节及上游锁。
4. 固定完整业务candidate commit仅白名单3模块/新test/必要control改动/implementation子目录，AGENTS及旧untracked不暂存。并行Standards/Spec代理基于0545...同候选审查，修复再固定重审。skill完整baseline已读，可重读审查。
5. 最终frozen-plan/code byte/ref用真实双PASS报告封存run-plan/review-seal，不创建authorization，不Start。最终PowerShell Start -ConfirmLive只交付命令不调用；Status/Stop/Resume原脚本。
6. 交付实际离线数值、开发/模型/等待/评价时间/重叠/总墙钟、实测存储/预测余量、V00调用预算、真实配置/计划ready边界；EndDevelopment收口；额外暴露一个test标签见exposure-note，原100已看成绩也披露。

已知待审问题：run_task state.preferences可用但negative title_term缺失目前仍可m1，需要未知门禁。Feedback目前只检查有reference未验证真实ref/aspect。visible缺历史商品title/crop，Lifecycle compact丢proof/batch可用信息。BusinessClient矩阵扩展需完整allD校验由rank_i1执行，wire长上下文须压缩重复观察和Top15 components引用。known task16_failed业务推荐目前抛到control会丢自身report，特征选择需要识别终结失败；未知必须不重发。prepare_files缓存早退应复查生产材料源，控制Resume跳过旧单位需开头单次输入核验。费用原压力情景角色组合不是额度上限，已在execution-arrangement说明，不调整6944/1504调用预算。独立评价当前引用路径读取应校验冻结SHA而不是只传path。
