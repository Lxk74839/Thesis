# 任务14：Q输出合同修订与一次复验

Status: resolved

验收：见acceptance.md。Q1/Q2各一次真实released、各16次调用；八项独立评价pilot_acceptance=PASS。集中收口账220/224，余4不授权新run。正式实验未开始，HR/NDCG为0不代表效果成立。
BASE: 3d25e85。规格来源：2026-10-22用户完整确认，继承全部旧结果和账本。

范围仅Q1/M、Q2/M各一个新run、每项18次，累计188→224（旧余6包含在36内，新增上限30）。固定4Router/gpt-6-luna；count/其他API/自动重试0，并发1、HTTP120秒、run1800秒、最终1次/1500/145秒预留。存储1GiB共享/128MiB单run/2GiB新增、内存4GiB不变；历史时间和超限保持统计，不恢复分钟级门槛。

公共验证接口沿用生产prepare/invoke、工具往返、完整Q运行入口、score_task/summarize。测试使用手写PUBLIC合成输入，不冒充旧响应回放。六项有效结果不重跑，独立标签不进入运行输入。

## 已确认接口

- 产品画像acquired-product-object-0.3.0：observations为本组冻结ID的封闭对象，所有键required，值不重复candidate_id。程序仅以原键和原值构造冻结顺序列表，分别封存原对象与派生列表；任何缺项、额外项、重复JSON键、错回执/质量/事实引用均拒绝，不去重补缺。
- 排序问题ranking-issue-proof-0.1.0：新增category和ranking_evidence。排序类型必须绑定当前草稿、/items，提供实际观察顺序、所声称期望顺序、actual_G_full下G与冻结融合绑定哈希、首个差异位置；宿主用原实际G排序核对。上下文提供已有程序计算的实际G分数表，不引入参考标签、不改变公式或预期成功判定。
- 无效主张保留完整原问题单和拒绝码，不能授权草稿修订。全run最多一次显式verification_correction，在同一草稿上给出完整新判定；第二次不合法立即失败。错误JSON、角色Schema、HTTP等协议错误仍停止，不做隐式重发。其他证据问题保留原候选/条款/指针/回执绑定校验。合法问题才进入原修订流程，最终排序门禁不变。
- composer0.15.0、4Router runner0.3.0记录新run版本；旧产物及原版本逐字保留。

## 验收

真实错误模式先RED，再GREEN；包含完整32候选Q的生产适配器离线链、reasoning/工具续接、三组件同锚点、一次纠错与最终预留，以及194旧授权与224新授权的历史不清零、固定run不可复用。未改动部分继承既有验收，核心评价器不改。

同一精确候选Standards/Spec双轴PASS后立即执行两个配置中的新run，再独立评价；不加PUBLIC探测或其他真实run。8项全部闭合并通过原发布、审计、预算与质量三组件锚点才完成试点。失败如实保留，42个未授权槽位维持not_started；HR/NDCG为0照实报告，不用于反调输入。
