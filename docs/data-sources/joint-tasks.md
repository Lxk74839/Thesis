# 联合数据准备子范围

批准合同与授权位于`.scratch/data-preparation/ticket13-stage1-joint-package-and-independent-evaluation-contract-20261016.md`及`ticket13-implementation-authorization-20261016.md`。固定审查基线cfec0e5；只接受联合数据准备，不接受真实工具、异常生产核验、推荐运行器、模型/统计效果实验或账本。

唯一准备入口：

```powershell
conda run --no-capture-output -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis python prepare_data.py --stage joint_tasks --joint-config config/joint-task-package-0.1.0.json --output-root . --access-probe data/joint-inputs/joint-task-package-0.1.0/access-probe.jsonl
```

该阶段仅接joint-config/output-root及可选access-probe；其他阶段参数拒绝。Thesis Python3.13.16、标准库，无新依赖。配置封闭字段、批准原稿摘要、全输入/接受链及固定预算候选均检查；execution_budget=null且execution_authorized=false，不能凭候选限额获得执行许可。

联合包为本地逻辑包：受信任总清单引用完整父商品/原始元数据、全部匹配源评论与清洗/去重去向、正常/16视图/Q1/Q2事实、原根与独立参考。路径、字节、行数、SHA-256全部绑定，原文件不改写。它不是可脱离上游目录独立搬运的归档。

根ID继承08，不改变账户/分组/原S。评论仅归父商品；candidate-map把完整C中的父商品映射到唯一SIM批次，视图沿用同一业务身份。每根生成一次char3-tfidf-history-1.0.0分数：只用白名单目录/H，目录拟合IDF，严格历史rating/5加权，余弦round12后在完整C归一化；全同分/单候选=.5。排序队列与父ID顺序分别保存。

每根绑定原8及两个Q视图；原8计划R/S/M，Q只计划完整M锚点。管理绑定保留真实快照/条款/权限/时间与共同指纹；未运行模型、工具或组件效果重排。Q no-q/mean后续只能在完整M同A/G/终态上重排。

新模型投影不改08 schema。model目录只有catalog、roots、candidates及仅列这三者的manifest；目标、原账号、密钥、组别、UQ掩码、参考、来源路径/总清单摘要均不进入。初始请求仅当前根白名单和批准需求、C/b绑定及不透明会话句柄，tools=[]。candidate_page每页32，可按parent/base取完整C；背景三计数随候选分页。源码数据会话无宿主I/O、索引、网络和模型执行能力，不声称OS ACL或未来供应商运行接受。

probe每行恰含session_task_id/operation/arguments。会话由可信测试方固定，根ID默认绑定第一视图，也可用可信生成的不透明会话句柄指定该已绑定会话。model_request只收空参数；candidate_page收order=parent/base与cursor，初页null，后续使用实际返回cursor。其他资源/工具、改身份/快照、跨会话游标挑战统一access_denied。返回和请求只保存在私有审计，文本不授予权限。

独立S2不导入生产模块：

```powershell
conda run --no-capture-output -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis python .scratch/data-preparation/diagnostics/verify_joint13.py --record records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json --audit-root data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0
```

S2独立核对全来源图、新基础分/完整C/投影/真实探测、根/快照/批次关联和引用。从已接受独立11/Q参考做逐键关联，不重推旧47,808状态，不运行P0或旧SIM生成。Q只有精确正常v1范围才允许将已接受eligible=true及既有R1/R5来源映射为Supported；原件/登记/事件引用必须在同对象同快照解析，异常或版本范围不支持即失败，不能拿rank_quality或模型输出生成gold。

旧P0 U8/n8/覆盖仅引用并核对源指纹及根键。新增Q每根两次关联，UQ是两个Q都参考适用的测试账户交集；开发单列。缺参考键/错批次/错快照为管线失败，不是NA。人数门、覆盖正确性、实际区间与整体充分性分别记录；975达标不能写sample_sufficiency=passed。

准备成功退出0/status=joint_tasks_prepared；S2成功退出0/status=passed_joint_association_only。失败退出2，无成功接受记录。先完整暂存再发布，已有半发布或不一致输出拒绝；一致复用重新构造稳定组件并比较实际字节摘要，返回旧主记录且不改mtime。复现直接比较稳定数据/参考字节，易变主记录运行时间分开。

所有项目Python经`run_joint13_check.py`运行，统一累计1,800秒、Windows子进程树4032MiB并保留64MiB守卫余量，整体4GiB；失败/RED计入，同一环境顺序执行。资源账位于忽略的data/joint-audit/joint-task-package-0.1.0，独立静态代码审查不运行Python。

`deliver_joint13.py`只承担来源摘要保护、私有probe生成、经S1/S2的复现/复用及接受证据写入，不增加公共准备入口。全部实际门禁通过后才另写accepted_joint_preparation_component_only，prepared不回写；14/15、运行预算、真实工具和模型仍保持各自未完成状态。
