# A 阶段逐行为验证

BASE=dcd7f1971a41af7dd1b29421e250596af06faffd。全部项目 Python 由本包 invoke-check.ps1 → Thesis Conda → 原 run_check 的 liveA 守护执行；失败、启动均计账。原始 stdout 为 data/recommendation-runtime-audit/20261018-batch/liveA_<编号>_<标签>.txt。

| 公共行为 | 实际路径 |
| --- | --- |
| 只读装配 history/H、b、指纹 | 002 ImportError RED → 003 GREEN |
| 权限主体不可替换 | 004 未拒绝 RED → 005 GREEN |
| PUBLIC 来源在读取前拒绝越界 | 006 拒绝太晚 RED → 007 GREEN |
| 装配到 PUBLIC 运行器、终态复用 | 008 新参数缺失 RED；009 preflight 仍失败；010 GREEN。源条款对象与 binding 条款ID须转换，完整条款保留 |
| 实际A单份封存与引用 | 011 缺 acquired_ref RED → 012 GREEN |
| 原生产形状产物／独立参考到单任务评分 | 013 缺模块 RED → 014 GREEN；一项执行与49未执行槽，汇总 incomplete |
| 审计原字节与 task 引用绑定 | 015 损坏审计未拒绝 RED → 016 GREEN |
| 真实开发仅装配、不能借 fixture 获得运行能力 | 019 仍标 public 模式 RED → 020 GREEN；未调用任何真实运行器 |
| 开发成员及父冻结身份必须核对 | 021 伪成员证明未拒绝 RED → 022 GREEN |
| 未决 intent 不得当缺记录／零分 | 024 缺 terminal 处理 RED → 025 GREEN |
| 注入运行器预算须等于记录 | 036 未拒绝 RED → 037 GREEN |
| 缺预算的 PUBLIC 配置须列明 missing | 038 错报 assembled RED → 039 GREEN |

以下8项首次即通过既有／已完成行为，如实保留，没有制造RED：017 M替身到评分并保持fixture来源；023 Q三组件仅同一次M的A/G；026 缺实际A不补证；027 缺计划执行是管线错误而其他槽not_started；028 参考错批次拒绝；029 失败／未知usage不重试不填零；030 本包读／写／网络守护；031 新场景使用精确快照和原请求模板。

018为获准的只读来源定位和独立开发清单冻结，非推荐／评价／统计。原始数据、参考和正式计划未改。开发任务键在测试中与草案8个字面量逐项比较，成员证明及正式100交集0核对；测试只对真实任务做装配和拒绝检查。

032实际运行18项新增公共行为全部通过。033实际运行原 DispatchBoundary 的16项直接影响回归通过。034实际运行10项直接影响断言通过：原 RootBudget 两项、batch第十合格停止／Q同锚点两项、评价器状态／绑定／空／Q／usage五项及原PUBLIC CLI拒绝一项。direct_regressions.py只适配原测试的PUBLIC临时目录，方法体与断言未变；没有全库／上游验收／旧T0运行。新增两项预算行为后，以最终新增测试文件的实际输出为准。

PUBLIC原件来自手写事实与独立字面量状态、目标和手算期望；未从生产输出生成gold。M与Q的实际取证、模型返回原件、A、审计、publication和task引用留在本包PUBLIC目录，public-example.json和public-Q-example.json提供定位。Q只验证既有纯质量一致性，不从参考填q/m/z或重取材料。

启动结算偏差：最初33次 launcher 的 Math.Max 整数重载把小数秒取整。035逐次补计1秒，共33秒保守上界，不退款；旧2秒记录加补计应描述为3秒上界，不能称精确实测。脚本已改为double重载，后续按外层Stopwatch减已计guard秒数结算。原记录全部保留。

040最终新增文件20项通过（12组实际RED→GREEN、8项首次通过）。核对22份保护文件及离线账原前缀未变。原生Git whitespace首次因字节绑定JSON/JSONL中的CRLF报告失败；只增加本目录的局部cr-at-eol属性，保留原始记录字节，随后重查。该失败原生命令仍由本包60秒原生保守上界覆盖。
