# C01—C06离线适配：逐行为TDD与证据映射

BASE固定`023a6cc5b906541f01b56cfd805594719bfac557`。实施前`c5e2963`已归档[人类授权](../authorization-model-offline-20261018.md)及原字节集中确认文件。公共Seam仅prepare/invoke/count/run及计数CLI；HTTP/事实/文件/时钟是外部替身。旧批处理接受直接继承，未重跑其30项收口或13公开组合。

所有项目Python使用既有Thesis Conda及同一Windows Job守护，账根`data/recommendation-runtime-audit/20261018-batch/`，从原70.268001秒继续累计，未换账或清零。每次失败、保护和诊断都在原resource-ledger.jsonl。所有新增用例的公开文件从一开始就按检查label保存在`cases/<label>/`，不清理早期RED原件。

下表按实际执行先后记录；一个新行为实际失败后才做最小实现，未预写整批测试。label中的green只是尝试名称，失败不算通过。公开期望为合同字面值/独立原件，不以生产函数生成答案。

| 行为 | RED原始label | 最小实现及GREEN |
| --- | --- | --- |
| 完整W/P准备且不发送 | 042：没有prepare | 043：保留完整消息/工具/输出schema，分别冻结W/P |
| 封闭角色schema | 044：开放data仍prepared | 045：逐对象封闭及已支持schema校验 |
| 缺计数保留未知 | 046：没有计数模块 | 047：离线count_missing、不发送 |
| fixture计数不成官方 | 048：无fixture计数入口 | 049：绑定W/P/版本/project，显式basis=fixture |
| 内容漂移/跨project拒绝 | 050：错误请求仍counted | 051：冻结内容摘要与project核对 |
| native调用与100/40/30/20会计 | 052：无counter/根预留连接 | 053：同prepared/回执/根预留单次调用，100/30、183微美元 |
| 实际输入漂移 | 054：101输入被当成功 | 055：保原usage、usage_mismatch且不自动重试 |
| 格式失败保留已知usage | 056：已知费用被丢为unknown | 057：保183费用，宿主可显式修复，同预留不可复发 |
| 函数call_id/arguments | 058：合法调用误format_error | 059：原生函数调用映射与宿主闭合检查 |
| 角色输出守schema | 060：wrong字段仍ok | 061：封闭schema结果检查 |
| refusal/incomplete/429 | 062：统一误标format_error | 063：分类及已知/未知usage原样保留 |
| 规划封顶不是许可 | 064：只有count_missing | 065：明确permission_denied、发送0 |
| 目录去重不丢根 | 066：CLI无导出产物 | 067：完整声明引用与唯一W对应 |
| 显式fixture许可与原件账 | 068：无目录计数入口 | 069：先intent再一次替代POST、raw与费用留存 |
| CLI导入及逐根累计 | 070：无import | 071：2根同W仍各100，保留fixture来源 |
| 运行器缺计数停在发送前 | 072：新模式被旧preflight拒绝 | 073：count_missing终态，模型0、final槽不动 |
| 六角色native共账 | 074失败；075尝试仍native_prepare_failed | 076：六角色schema、整数enum显式类型、保留原uniqueItems，9调用/900输入/270输出/1890微美元（fixture） |
| count CLI默认拒绝 | 077：无count CLI | 078：规划permit拒绝且不创建尝试账 |
| 单一HTTP计数边界 | 079：无替代连接入口 | 080：固定origin/POST，关闭连接，无redirect/retry/凭据探测；连接是fixture |
| 重贴官方标签不能越权 | 081：改receipt和result/intent标签后被接受 | 082：核对实际替代传输来源、许可范围及真实外部授权关联 |
| deadline同预留 | 083：可扩到90秒未预留时间 | 084：阶段、根/final及该预留截止共同限制 |
| 迟到结果不成功 | 085：45001ms仍ok | 086：timeout，保已知usage和原件 |
| 畸形native原件 | 087：None输出处理抛异常 | 088：记录format_error及unknown，不丢账 |
| 两客户端不能抢同一槽 | 089：两次替代发送 | 090：同目录独占inflight，另一请求明确count_inflight；之后用事件稳定时钟安排 |
| 未知计数结果重开仍停 | 091：只有笼统permission_denied | 092：count_stage_halted，3微美元未知占用保留，重开不重发 |
| 空R fixture不获官方来源 | 093：空集合被真空真值误标official | 094：scope与来源共同判断，R输入0仍是fixture |
| 小目录不冒充全T0 | 095：一个R也可标全量 | 096：全量标签要求320账户×10视图×3方法的声明集合，未执行此枚举 |
| 未绑定返回model不能套价 | 097：未知model仍按183结算 | 098：保100输入，费用unknown，不重试 |
| 不能折叠重复attempt账 | 101：重复intent被dict吞掉 | 102：序列/唯一性核对，不降低已用配额 |
| 自重封不能添加服务端状态 | 103：添加conversation并重封后counted | 104：W/P封闭字段和固定设置；后续加强测试同步wire_bytes，排除旁支拒绝原因 |
| 不隐藏未申请托管工具 | 105：web_search_call被忽略 | 106：unsupported_provider_tool、附加费用unknown、停止 |
| 自重封不能漏历史调用 | 107：删call留result仍counted | 108：逐call/result闭合，不由摘要代替输入合法性 |

另两项必要观察没有追加生产实现：099为新质量测试的编写错误（漏json导入，误将S也当有M的组件），100修正测试后S/M均通过；不称产品RED。109的部分计数覆盖检查首次GREEN：一个缺项让整根累计为null、不能官方完整。这两项不伪造失败。

110收口：**39/39通过（34新增、5必要旧接口回归），4.492秒；守护4.749秒**。必要旧回归仅旧provider未绑定、历史身份/工具ID、额外宿主字段，以及运行器接地画像/共同重试。没有重跑旧全库、已接受批处理收口、公开组合或上游生成。

全部新增测试使用公开小事实与literal fixture计数，不读正式效果，不把字节/fixture整数当真实token容量。native客户端实际外发0；真实计数需独立批准的执行记录/费用证据/完整目录及显式凭据路径。没有生成HTTP发送函数，live run继续拒绝。

工具原schema的uniqueItems没有删除或用免费宿主取证替换；其在既定模型strict schema下的实际支持未获调用验证，官方[支持属性页](https://developers.openai.com/api/docs/guides/structured-outputs)没有列明该关键字，仍是外部计数/后续验证的未知项。离线prepare成功不是供应商接受或容量通过。
