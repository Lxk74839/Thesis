# 工单12预算：只读证据、调用分解与官方资料

日期：2026-10-18。基线：`ac4874c7218ea1a795ddf992a9c23d133766a293`。

## 1 复核方法与边界

只读读取`C:\Users\Kane\Documents\CodexProject\Thesis\data\recommendation-runtime-audit\20261017\micro\v4\<case>\runs\1\budget.jsonl`。使用PowerShell/.NET逐行解析JSON，统计含`observation.request.schema_version=rsm-model-request-0.1.0`的结算记录；按role/output_kind及最后一条runtime.stage分组。工具请求数来自response.message.tool_requests；逻辑/物理来自每次observation.usage的增量之和。

不重复统计reserve与settle，不相加usage累计快照。日志最后一条usage可能只是seal的零增量，不能把它当全根零消耗。没有运行任何生产模块、诊断Python、测试或公开组合。仅读取公开人工fixture，不读取正式测试推荐表现。全部日志绑定实现候选3d970b7，当前HEAD ac4874c为接受文档归档。

## 2 日志复核实数

下表I/O字段的量纲均为**合成UTF-8字节**，虽然旧字段名为input_tokens/output_tokens。供应商请求和美元费用全部0；时钟受控，不是网络延迟。

| case | 方法/臂 | 实际处理n | 模型调用 | 追溯调用 | 模型工具请求 | 逻辑 / 物理 | 合成输入字节累计 / 单轮最大 | 合成输出字节累计 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| normal-R | R/必要 | 1 | 0 | 0 | 0 | 27 / 2 | 0 / 0 | 0 |
| normal-S | S/必要 | 1 | 10 | 3 | 2 | 27 / 2 | 309,639 / 90,623 | 8,385 |
| normal-M | M/必要 | 1 | 10 | 3 | 2 | 27 / 2 | 124,312 / 34,971 | 8,391 |
| quality-four | M/质量 | 4 | 25 | 12 | 8 | 133 / 8 | 2,135,857 / 255,844 | 42,087 |
| stock-feedback | M/质量/反馈 | 1 | 12 | 3 | 2 | 39 / 2 | 326,438 / 92,940 | 18,290 |
| necessary-twelve | **R**/必要，C=12 | 10 | 0 | 0 | 0 | 225 / 20 | 0 / 0 | 0 |
| quality-twelve | M/质量 | 12 | 65 | 36 | 24 | 389 / 24 | 29,426,628 / 1,309,117 | 111,457 |

追溯每候选三次是`list请求→read请求→done续轮`，两次请求各伴随后续推理轮。单候选M顺序为：需求、用户画像、dispatch、list、read、done、农产品画像、draft、verification、final_submit；S序列相同但角色均为单智能体。

质量4候选角色计数：需求1、用户1、管理dispatch4、追溯12、农产品画像4、初稿1、核验1、最终提交1=25。质量12相应为1+1+12+36+12+1+1+1=65。反馈例初稿/核验之后追加revision1和verification1；非失败重试。

| case | 原budget.jsonl SHA-256 |
| --- | --- |
| normal-R | `15df3db91f8501016a0d4831c57fdf730c6d2fe4b0be08310c74c004f8e9a758` |
| normal-S | `83747941418440445fd32dc4881df2537fdeb65d8e55de78a5fe490103bb0eea` |
| normal-M | `73d44a9e941a06ba9fb98fe9fba1d106cdb5eecc6604da6977ad99a61e9bd094` |
| quality-four | `6e4b0826afb23ed711b302b955e4c249fb5f525a43423e399c9c2ea4ac97bba0` |
| stock-feedback | `26f89b7db5aba5c76f214de68507468da91e84de5ebd9eea73c0cd75e9df9d44` |
| necessary-twelve | `9202339adf9407cc1550406706e1e2553716ae569609d0e235605b7180b7ddd1` |
| quality-twelve | `ce44a67f48a9145af1251469dc71540cbb98e6339ef7fdfd886e17ea25c85b1e` |

公开fixture给S/M宽松测试上限：通常模型1,000次、候选100、输入10,000,000合成单位，quality-twelve输入为1,000,000,000；final为1次/1,000,000输入/100,000输出/1,000毫秒。它们用于验证协议，**不是F3 12/96k/12k/64/600及final 8k/1.5k/60通过的证据**。不把公开通过数重算为正式预算通过率。

## 3 工具与程序分解

quality-four：list共4次，63逻辑（60登记+3初始依赖）/4物理；read共4次，60逻辑/4物理；assess4、advance3、submit_draft1、verify_draft1、final1；commit/seal各0逻辑、0物理，实际文件I/O仍存在并计时间。

quality-twelve：list12次，183逻辑（180登记+3初始依赖）/12物理；read12次180逻辑/12物理；assess12、advance11、三项提交/核验/final共3逻辑，合计389。stock-feedback另外patch1、verify1，合计39。normal-R/S/M的fixture每候选10登记/原件，不混用质量的15作为其“实测”。

由同质量路径推导完整读取n个候选：`3+30n+n+(n−1)+3=32n+5`，n=4/12分别133/389；n=64为2,053，尚未加候选分页、反馈、失败、新批包装和额外异常依赖。此前规划约1,992没有覆盖现行每候选推进等完整路径，不能继续当上界。这个推导不新增64对象实验。

真实来源取证专项已有probe每源67逻辑/2物理，含32候选行、15登记、3初始依赖、15原件、1缓存返回、1评估；setup 402,468,658字节/110次文件读另报。这是单对象来源probe，不是64候选或模型载荷实测。直接复用[其接受记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/evidence-forensics/acceptance-20261017.md)，不重复probe。

## 4 静态定位

| 文件/入口 | 直接可核实事实 | 本轮判断 |
| --- | --- | --- |
| [recommendation_runner.py](C:/Users/Kane/Documents/CodexProject/Thesis/recommendation_runner.py:196) `_context` | 已取原文、完整C相关映射、全部成功角色输出重复进入上下文；角色history持续追加 | 载荷需有界、去重复，不能由调用压缩推断token下降比例 |
| [运行器调用](C:/Users/Kane/Documents/CodexProject/Thesis/recommendation_runner.py:285) `_invoke` | input_upper取完整JSON UTF-8长度；max_output_tokens=100,000；cost=0；model_id=null；provenance/scripted固定 | 当前仅合成协议，真实绑定需显式新版本 |
| [工具续轮](C:/Users/Kane/Documents/CodexProject/Thesis/recommendation_runner.py:328) `_role/_model_acquire` | 模型每次工具返回后再次invoke；dispatch与画像逐候选 | 5+5n不是六角色数量推测，有源码和原账支持 |
| [运行循环](C:/Users/Kane/Documents/CodexProject/Thesis/recommendation_runner.py:586) `run` | 固定游标、必要首10、质量前缀、每候选assess/advance，最终发布/组件 | 批工具必须保持同一停止及评估语义 |
| [适配边界](C:/Users/Kane/Documents/CodexProject/Thesis/model_adapter.py:87) `invoke` | 只接受精确scripted_public绑定、null model；额外真实模式在transport前拒绝 | 单增HTTP sender不足，不能绕此门 |
| [取证](C:/Users/Kane/Documents/CodexProject/Thesis/evidence_access.py:518) `_dispatch` | list最多32登记/页、read最多32不透明ref且限当前候选；advance和assess各1逻辑 | 当前不能合法发送一个跨候选read批；新批是顺序解释器，并非放宽ref权限 |
| [公开fixture](C:/Users/Kane/Documents/CodexProject/Thesis/tests/runtime_fixtures.py:155) `make` | 宽测试限额、synthetic计量、受控时钟 | 原组合只证明协议，不证明F3容量 |

## 5 当前官方资料与核验结论

下列均在2026-10-18实际打开官方正文；不使用搜索摘要或第三方模型榜单替代。静态文档查询不等于调用供应商API。

| 来源 | 只采用的事实/结论 |
| --- | --- |
| [GPT-5.4 Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) | 日期快照gpt-5.4-mini-2026-03-17；400k/128k；函数/结构化支持；none设置；输入/缓存/输出0.75/0.075/4.5 USD每百万 |
| [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) | ID仅gpt-6-luna，未列日期快照；1,050,000/128k；函数/结构化支持；明确none避免默认medium；基本输入/缓存/输出0.1/0.01/0.5 |
| [价格](https://developers.openai.com/api/docs/pricing) | Standard与Batch等服务等级区分；Tokens按模型计费；部分区域有附加价。本案单轮≤96k并限定Standard，其他服务/区域不默认为同价 |
| [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | 旧代与5.6以后缓存写入政策不同；新代写入价1.25倍并是输入类别价，不在普通输入价上再叠加；explicit模式无断点时不读写缓存 |
| [Counting tokens](https://developers.openai.com/api/docs/guides/token-counting) | 完整结构计数与纯文本tiktoken不同；官方input_tokens端点包含消息边界；全部生成量可能包含隐藏格式；max_output_tokens限制包括不可见生成 |
| [Reasoning](https://developers.openai.com/api/docs/guides/reasoning) | 推理token包含在output总量并按输出计费，不在总量上再加一次 |
| [Function calling](https://developers.openai.com/api/docs/guides/function-calling) | strict schema的required/additionalProperties要求；工具call与结果要有关联ID；工具返回后的模型续轮是真实新调用 |
| [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | 结构化输出与工具调用不同，拒绝/截断须处理；格式保证不替代业务正确性 |
| [Error codes](https://developers.openai.com/api/docs/guides/error-codes)、[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) | 错误/超时与重试信号；Retry-After及应用与SDK重试不能叠成隐蔽尝试；未获得按所有错误类型统一免费的证据 |
| [逐运行费用控制示例](https://developers.openai.com/cookbook/articles/per_run_spending_controller_responses_api) | 用量缺失/不一致及超预留应阻断；新代需cache_write_tokens才可算相关精确费用，usage不是凭空可得 |
| [弃用表](https://developers.openai.com/api/docs/deprecations) | 2026-10-14公告GPT-4.1 Mini于2027-01-14移除；2026-10-01公告GPT-5.4 Nano于2027-04-01移除 |
| [Batch](https://developers.openai.com/api/docs/guides/batch) | 异步批处理提供不同服务窗口与价格，已完成请求照计；它不消除逐轮模型调用，也不能自动满足本案根时限及依赖续轮，所以本案不套Batch折扣 |

OpenAI Docs技能要求仅用官方域查证，本轮未运行模型迁移resolver、未借当前聊天模型名称推导API能力或价格。完整reference页面两次因正文超工具大小限制未取得，相关事实采用已取得的官方指南，未把失败的页面当证据。`.md`镜像被web工具拒绝content-type，也未引用其未读内容。

## 6 事实、推导与未知清单

| 类别 | 内容 |
| --- | --- |
| 实测/原记录复用 | 25/65/10/12调用、字节/逻辑/物理/阶段数、公开方法类型、旧source probe、正式数据规模、现环境缺少分词目录 |
| 静态/算术推导 | 5+5n、64候选325/329、2,053逻辑、批32的9/13/17、批16的21/25、33,358/23,094根、新价格乘法和时间包络 |
| 未验证候选 | 新批行为、4,096/256、192k/24k、17次、64前缀、900秒、final完整预留及USD6,000模型池 |
| 硬缺口 | 分词精确版本/Windows轮子/encoding摘要，供应商完整请求本地计数或已证明上界，真实provider绑定/usage/错误会计实现、T0接受 |
| 自然运行未知 | 供应商访问/延迟、自然工具续轮/分页/角色完成率、token分布、反馈收益、实际失败收费、全部正式平均费用；没有读取正式测试表现填补 |

## 7 只读保护的核对范围

诊断开始HEAD=ac4874c，`git status --short`仅已有`?? reports/`，tracked diff为空。reports为既有用户产物，逐文件保存内存摘要用于交付前比较，不加入本轮产物。另核AGENTS/environment/三个受影响生产文件、论文/研究、F1—F3确认及正文、运行器/取证接受和14验收共12份重点文件摘要；不是重做上游全量保护或语义验收。

| 重点只读文件 | 原始SHA-256 |
| --- | --- |
| recommendation_runner.py | `cbe4aeb5b75dcf3a2831262d2c526295cb58c2dfb986a4975a12f45de82a9d0f` |
| model_adapter.py | `54a4409278f87b4b5c852b96f7b68cb9bdd14f34994aac8562ceb49a1d05b716` |
| evidence_access.py | `afa610615bb9aaf3b9562a89bba6f35d7fe64a84e34df8828331e0ff6d2ac6d2` |
| manuscript/论文初稿_表达与实验结构修订版_20261010.docx | `b9f44938f7298a23e84a69bfed33f2398bb705a8433bd44f49866f8fbc2064b0` |
| research/数据修复方案与验收草案_20261010.md | `40f3960a9cce38221367ef6f05074c61e22251e93ebb664bbad3077fefdb8a8d` |
| F1—F3确认 | `e81c699a4376dc43c417a0c697d481d5c5282ca0fbb5c068072d84d6d60a90fc` |
| 运行器接受 | `1b3e44881f83e5800a2ae61a74a03937599915af9b3453720c8c7e0557b3767e` |
| 取证接受 | `6ff196d11a6c8bb60b58f9f557c68264819e3dd323fa939dcb6f5fff5fd70bdd` |

交付检查仅验证本轮Markdown链接、算术、文件范围和只读摘要；不冒充实现、T0或独立双轴代码审查。全部历史公开日志保持原字节，不生成新的接受记录。

## 8 本轮交付检查结果

- 五份新增文件均为Markdown；全部本地文件链接可解析，代码围栏闭合。
- HEAD仍为ac4874c；已跟踪文件差异为空；未暂存或提交。已有reports目录保持，未移除或纳入本轮改动。
- 12份重点只读文件及12份既有reports文件合计24份SHA-256前后相同；旧日志仅作只读分解，没有追加或重写。
- 正式根数、主/备选调用、token报价及舍入余量由独立算术核对；没有拿任何真实推荐表现推导预算。
- 生产代码、配置、依赖、论文及接受记录写入0；项目Python/测试/公开组合/T0/P1/模型/计数API执行0；部署和15冻结0。

这组结果只说明本轮诊断文档交付满足约束，不是新实现或执行预算已通过验收。
