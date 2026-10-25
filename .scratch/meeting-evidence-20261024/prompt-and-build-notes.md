# 六角色提示词与项目搭建流程核对

日期：2026年10月24日。核对对象为本地源码及已保存的真实请求，未新增供应商API调用，未修改生产代码、论文、原数据或历史结果。当前代码基于任务16协议macrec-agri-v2，历史已完成实验使用personalized-compact-0.1.0，两者必须分别介绍。

## 已实现的算法和实际进度

旧版Compact先从历史提取一份可复用的偏好画像：R按规则选择可观测属性；S一次模型画像；M按六角色依次检查画像。各场景使用宿主确定性的完整候选重排。它没有实现MACRec式逐次动态工具调度，不能将其结果写成MACRec复现结果。[源码 analyze_profile](D:/Work/Codex/Project/Thesis/personalized_recommendation.py:48)，[源码 run_task](D:/Work/Codex/Project/Thesis/personalized_recommendation.py:88)。

旧版冻结100名来源账户、18个场景，共5000条方法任务终态：4752成功、248模型失败，缺失及未启动均为0。16个V场景按用户等权平均的真实偏好结果为：R的HR@10=0.217500、NDCG@10=0.121012；S为0.195625、0.108129；M为0.205625、0.102365。预定四项比较的区间均含0，不能宣布M总体优于R或S。来源：[实际结果](D:/Work/Codex/Project/Thesis/.scratch/compact-execution-9d0c8eb7/results.md:1)。

任务16的新B0是MACRec农产品有界适配：管理者动态选择User、Items、Search，观察工具返回，检查反思后可进行第二轮求解。上游锁定提交为cbd9ea036cf6cac05a2ee59592526982a626fc82；农业接口、宿主约束和推理预算已经做了适配，因此不能声称零修改复现。[上游来源锁](D:/Work/Codex/Project/Thesis/.scratch/macrec-algorithm-20261023/sources/SOURCE_LOCK.json:1)，[新求解器](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:169)。

新I1在相同候选与材料规则下，使用候选级语义匹配、短历史置信度、证据质量和定位反馈。当前实际代码的分数为b+lambda×sum(w×c×o×q×(m-b))；无支持时该项增量为0。c由不同历史父商品的正负支持计数与tau计算。以上是算法实现，不代表效果已经证实。[置信度](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:40)，[评分](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:119)。

任务16在320开发账户上建立离线共同召回，固定16人模型面板；共同Recall@200=68.75%，面板Recall为75%。v2的8个直接Finish探针通过；特征阶段已执行8个用户任务均未成功，随后停止，B0/I1主对照0/32。累计89次物理请求包括旧协议14次和v2的75次，发送未知的1条必须按审计未决解释。当前没有B0/I1性能比较值。[v2实际结果](D:/Work/Codex/Project/Thesis/.scratch/task16-execution-v2-20261023/protocol-v2-20261024/results.md:1)。

## 六角色怎样协作

六个角色名称来自同一ROLES映射。推荐管理虽然拆成thought和action两次业务调用，仍是一个角色，不应因此称为七智能体。[角色表](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:8)。

1. 需求解析：接收当前请求，输出necessary、preferences和unknown。只复制当次必要条件与明确偏好，历史画像不在此步骤生成。[提示词与结构](D:/Work/Codex/Project/Thesis/macrec_protocol.py:95)。
2. 推荐管理：thought说明当前分析判断，action在User、Items、Search、Finish间选择。B0的Finish包含完整候选排名；I1组织User、真实Search观察、Items矩阵，最终分数由宿主计算。[管理提示词](D:/Work/Codex/Project/Thesis/macrec_protocol.py:105)。
3. 用户画像：读取历史文字及可观察商品，提出不超过六个带引用的属性偏好。支持crop、form、title_term、retail_stock；原文、正负立场和冲突检查由宿主继续执行。未知可输出空画像。[画像提示词](D:/Work/Codex/Project/Thesis/macrec_protocol.py:115)，[校验和置信度](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:40)。
4. 农产品画像：B0返回有来源的候选比较叙述；I1对每个候选及偏好输出匹配值m和来源字段f。匹配只能来自标题、作物类别及实际已取得的库存观察，不能把无法观测的属性当成已满足。[商品提示词](D:/Work/Codex/Project/Thesis/macrec_protocol.py:124)。
5. 生命周期追溯：以Lookup/Search请求宿主读取指定范围的材料，观察实际返回后再总结。主程序负责范围、资格、材料一致性及q，模型不能编造材料或决定工具真值。[追溯提示词](D:/Work/Codex/Project/Thesis/macrec_protocol.py:137)，[工具范围验证](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:203)。
6. 推荐依据核验：关注Top10和8—15名边界，I1的问题需定位到候选、属性、来源及具体问题。有支持才触发修订，不强制为变化而改排名。[核验提示词](D:/Work/Codex/Project/Thesis/macrec_protocol.py:143)，[反思调用](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:295)。

主流程为需求解析，管理者thought/action，选中的子智能体读工具和返回观察，再由管理者决策；形成当前解后执行反思，必要时第二轮修订。每轮最多四个管理步骤、三次子智能体派发、每个子智能体最多三次命令（包括Finish），总上限37次生成。I1与B0的角色要求不同，但候选与材料范围一致。[求解器循环](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:215)。

公共提示约束要求只使用给定来源，评论与目录是非可信数据而非指令，SIM表示模拟证据，未知保持未知，不提供目标标签；JSON仅返回当前角色要求的结构。[COMMON](D:/Work/Codex/Project/Thesis/macrec_protocol.py:68)。

### 哪些提示词真的发送过

逐条读取当前运行目录75条v2请求意图及request文件，按kind/role/方法/是否探针统计：需求解析10次，管理thought20次，管理action18次（非探针I1），用户画像12次（非探针I1），追溯9次，另有User、Items、B0-Action直接Finish探针各2次。未发现v2反思请求。正式多操作Items尚未实际到达；不能把探针Items当作完整链路通过。

prompts目录保存公共原文、六角色模板和实际发送示例、旧版Compact六角色原文、来源清单。凡来自生成模板而非真实请求的内容都显式注明；真实示例仅保留system提示词和Schema，不带完整个人评论或密钥。

### 为什么探针通过后仍失败

macrec_protocol.py将action枚举和data.anyOf分别组合，原生Schema容许“Info动作+preferences载荷”。宿主decode再按被选操作检查data，故产生真实业务失败。检索列表Schema检查索引范围，却未要求唯一，重复索引可通过原生Schema，再在宿主acquire失败。这是协议实现缺口，不能直接归因于推荐效果。[生成Schema](D:/Work/Codex/Project/Thesis/macrec_protocol.py:157)，[宿主分支校验](D:/Work/Codex/Project/Thesis/macrec_protocol.py:161)，[唯一性范围检查](D:/Work/Codex/Project/Thesis/macrec_recommendation.py:203)。

此外，直接Finish探针将可选动作限制为Finish，所以没有覆盖History/Info/Lookup/Search等正式多操作分支。[探针特判](D:/Work/Codex/Project/Thesis/macrec_protocol.py:154)。这些缺口已归档，当前材料仅介绍现状，不擅自修改生产实现。

## 搭建流程与代码对应

第一步是独立环境。项目环境为D:\Work\Codex\Project\Thesis\.conda\envs\Thesis，Python为3.13.16。environment.yml提供版本，environment-win-64.lock.txt锁定Windows依赖。优先复用现有环境，所有运行显式conda run -p；不要在现存项目上直接重复创建或覆盖。[环境规格](D:/Work/Codex/Project/Thesis/environment.yml:1)。

第二步是来源获取与谷物筛选。sources/amazon-2023-grocery-metadata.json和amazon-2023-grocery-reviews.json声明源文件；prepare_data.py统一入口按stage调度metadata、reviews、catalog、review_extract、review_clean。目录筛选由catalog.py，评论提取由review_diagnostics.py，清洗由review_cleaning.py负责。[CLI入口](D:/Work/Codex/Project/Thesis/prepare_data.py:16)。

第三步是用户分组与模型输入隔离。user_split调用user_splitting.py；preference_tasks调用preference_tasks.py。历史需严格早于留出时刻，留出目标及其原文在private评价侧，模型目录和历史文本经有限文本策略处理。[任务构造](D:/Work/Codex/Project/Thesis/preference_tasks.py:153)，[文本策略](D:/Work/Codex/Project/Thesis/preference_text.py:65)。

第四步是同商品SIM材料。sim_normal阶段调用sim_normal.prepare_normal，按真实parent_asin生成该商品的模拟批次及harvest、packaging、storage、inspection、transport、retail六阶段事件、证据及本地登记。evidence_scenarios调用sim_scenarios.py构造可控变化，quality_fusion调用quality_fusion.py处理质量场景。历史评论仍是父商品层的真实反馈，没有声称真实购买SIM批次。[正常场景生成](D:/Work/Codex/Project/Thesis/sim_normal.py:206)，[场景变化构造](D:/Work/Codex/Project/Thesis/sim_scenarios.py:180)。

第五步是联合任务与候选。joint_tasks.py将root/history、完整候选C、基础分b、商品到SIM批次的映射共同组织。基础分是字符3-gram TF-IDF历史内容匹配，按当前候选内的分数范围归一化；不得把它写成学习得到的神经推荐模型。[基础分](D:/Work/Codex/Project/Thesis/joint_tasks.py:120)，[联合包](D:/Work/Codex/Project/Thesis/joint_tasks.py:186)。

第六步是冻结100人实验计划。experiment_runner.build_plan按test100-sha256-order-0.1.0与固定种子从接受的测试池选择100名来源账户；固定18个场景、1800条用户场景绑定和5000条方法任务。相同用户多场景不增加独立样本量。[冻结计划](D:/Work/Codex/Project/Thesis/experiment_runner.py:88)，[实际计划](D:/Work/Codex/Project/Thesis/data/recommendation-runtime-audit/ticket12-100x18/plan/plan.json:1)。

第七步是模型画像、取证、排序和独立评价。旧Compact的模型画像保存在profiles，实际已取得的材料观察保存在scenes，然后按完整C重排；compact_evaluation.py在评价侧读取留出目标，用户级汇总。新MACRec路线改为动态协作、候选语义矩阵与定位反馈，通过macrec_protocol、macrec_recommendation、macrec_experiment三模块接入，评价由macrec_evaluation独立处理。[Compact运行器](D:/Work/Codex/Project/Thesis/compact_experiment.py:259)，[新业务单元](D:/Work/Codex/Project/Thesis/macrec_experiment.py:1093)。

当前登记backend为local_sim_registry，原结果明确Fabric未部署；因此流程图不能将这一阶段绘成已完成的Fabric链上实验。

## 本地复现的安全入口

在新拷贝的材料目录中，可按environment.yml新建专属Thesis环境；在当前已有项目直接复用现有prefix。可安全执行：

```powershell
Set-Location D:\Work\Codex\Project\Thesis
$env:TEMP = "$PWD\.tmp"
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = "$PWD\.conda\pkgs"
& D:\Work\Anaconda\Scripts\conda.exe run --no-capture-output -p "$PWD\.conda\envs\Thesis" python -B prepare_data.py --help
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PWD\.scratch\task16-execution-v2-20261023\run-task16.ps1" -Action Status
```

以上命令分别显示已实现CLI和只读运行状态，不下载或发送模型请求。旧任务16的派发截止为2026年10月24日18:28:03（日本时间），总截止为20:28:03，本次整理时已过期。不得将旧Start/Resume写成当前可直接启动新实验的命令，也不得自动重置预算。

若在材料包中重放旧Compact排序，可直接导入personalized_recommendation.run_task（纯标准库，无模型发送），使用冻结C、基础分、历史、目录、原画像及原场景缓存，重新得到Top10；对照原完成结果验证一致。失败画像应继续保留failed_model，不能给默认空画像假装成功。

调用形状为run_task({C,base_scores,K:10,prefer_stock:场景是否quality}, catalog=完整安全目录列表, history=root.history, profile=保存画像.profile, scene=保存场景.candidates, mode='full', alpha=.5)。重放只是消费已有真实响应，并非再次发送API，不应写成重新完成一次独立大模型实验。

严格的从零重建还需官方原始压缩文件、已确认config、对应records及冻结来源绑定，不能靠少量展示CSV重新生成完全相同的原始文件摘要。代码快照用于说明实现和提供离线演示；如果只复制部分源码，应明确这是展示与重放包，不是整个生产项目的独立镜像。