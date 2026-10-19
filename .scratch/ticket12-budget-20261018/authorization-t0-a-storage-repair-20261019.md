# T0-A有限存储修复包：人类确认与实施授权

日期：2026-10-19（Asia/Shanghai）。来源：本聊天用户明确确认`t0-a-performance-storage-diagnosis-20261019.md`中的R01—R05，并要求开始实施、审查和三件有界验证。

固定增量BASE：`69918e613fd700fd33c53a0ded5557b604487fcc`。提案原字节SHA256：`d0c1cabfd92ae19912d722e06a4218224c692536cf54e9807a4e6df49ac880b9`。原提案、历史合同和接受记录不回写。本记录与提案共同构成有限修复包的授权，不签发开发目录prepare授权。

R01—R05全部确认：单份完整W逐对象zlib level 1压缩拼包；固定删除四个顶层字段重建P；保留请求、metadata、W/P字节及摘要、prepared_id和全部原引用语义。新增公共PreparedObjectWriter/add/close、iter_prepared_objects及独立检查器check-objects；只允许提案§4白名单。新格式不能取得计数或生成发送资格。

严格按mattpocock-skills:tdd逐个公共行为RED→最小GREEN。复用既有PUBLIC对象，新增根计划0；不重新运行生成、profile或I/O诊断。实现后固定candidate，以本BASE完成独立Standards/Spec增量审查，保留各原报告；阻塞修复与复审只运行必要定向验证。

原离线账累计217.7244063001417秒，总额1800秒不变；本包累计命令墙钟≤300秒。原T0账累计1797.3523884000024秒，明确追加60秒，有效总额1860秒；三件验证包自身累计≤60秒。失败、重试、子进程及收尾均累计，不能每次重领。4GiB进程树含64MiB守护；跨两域全部新增磁盘≤256MiB，数据写入≤248MiB，8MiB留审计/收尾；删除产物不退还写入额度。

程序测试、固定候选双轴审查通过后，直接按提案§6规则：原requests至首个final最多17行/1MiB，选首个analysis、final前最后一个acquire、该final共三件；原件≤24MiB，连必要元数据总读取≤64MiB。调用生产writer落盘、reader还原及独立核验，无需再次请求同一许可。只读原目录，不读取其他开发对象或评价目标，不枚举原objects目录。

保留原91.6GB目录和T0_A_incomplete；不全量重跑、不续编译、不执行C/B/P1或供应商API。达到上限停止并留未完成记录，不自动扩额。通过时仅接受存储组件，不接受完整A、容量或费用，不关闭工单12。

归档先于实施：本确认、原件指纹、两份诊断脚本原字节副本、原账字节长度/摘要及PUBLIC state和PUBLIC对象指纹独立保存。资源守护的封闭扩展与计量门属于执行前基础设施；不把其首次安装伪记为修复行为的RED。后续全部项目Python显式使用Thesis Conda和原守护。
