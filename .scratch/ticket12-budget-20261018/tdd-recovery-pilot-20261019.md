# T0-A 限缩恢复机制 TDD 记录

基线05889b6，继承f97203a存储组件和17项接受。新范围以authorization-recovery-pilot-20261019.md为准，原6小时/128GiB/G2—G6未获批准。

所有运行均使用Thesis Conda及原run_check守护，标签recovery_pilot_*；失败不退账。完整原始输出在原离线账根同名txt，源码指纹及实际秒数在原resource-ledger.jsonl。没有运行原17项StorageTests、生成、profile或I/O诊断。

| 公共行为 | RED标签 | 最小GREEN/定向复验 | 实际观察 |
| --- | --- | --- | --- |
| 非pilot阶段拒绝 | 233_auth_red | 234_auth_green | 未展开计划即拒绝 |
| 独立来源snapshot | 235_snapshot_red | 236_snapshot_green；262_snapshot_targeted | 冻结PUBLIC来源、选择、身份键一次读取；不输出键/user_id |
| 完整prepare及W/P/身份保持 | 237_prepare_red | 241_prepare_green | 三个PUBLIC计划，26个完整prepared对象逐字段等于冻结原件 |
| 检查点故障与resume | 242_resume_red | 243_resume_green | 系统os.replace在第二次checkpoint失败；已提交前缀保留，仅重编未提交键 |
| 同输入摘要重算 | 244_recompute_red | 245_recompute_green | 首轮roots/requests/dependencies/objects及键正文读取陷阱未触发；摘要一致 |
| 独立pilot门与完整A隔离 | 246_checker_red | 247_checker_green | pilot可验收，完整check拒绝pilot覆盖 |
| 一致修改文件摘要的伪造依赖拒绝 | 248_dependency_red | 249_dependency_green | 依赖raw_utf8伪造并更新组件SHA仍被源字节核对拒绝 |
| 分根实际时间/IO/W/P/内存 | 250_costs_red | 251_costs_green | 26请求，W386237/P384183，Windows IO及采样私有内存非零 |
| 旧授权/越界receipt展开前拒绝 | 252_boundary_red | 253_boundary_green | 旧授权不再进入生成器；receipt路径先验证后读取 |
| 开发来源替换拒绝 | 254_dev_source_red | 255_dev_source_green | 生产CLI和独立snapshot均拒绝，身份键陷阱未触发 |
| 新程序接受路径绑定 | 256_program_red | 257_program_green | 任意接受记录路径在正文展开前拒绝 |
| 旧catalog绑定先于键读取 | 258_snapshot_binding_red | 259_snapshot_binding_green | 未绑定原目录元数据时，不读键 |
| 限缩CLI和物理读取门 | 260_limited_scope_red | 261_limited_scope_green | recover-from被明确拒绝；旧对象/依赖/probe和非G0真实键读取被守护拒绝 |
| 完成后resume幂等与整链定向复验 | 263_idempotent_red | 264_idempotent_green | resume保持稳定文件字节及mtime；再从输入编译三键，独立完整H/来源/probe检查及摘要均通过 |

标签前缀均为recovery_pilot_；准确标签以原账为准。238/239为Windows长路径失败，240为继承C盘PUBLIC快照定位符失败，均如实计时保留，没有制造或删去RED。修复仅缩短新测试输出路径，并在物理读取时定点映射历史项目根到D盘；保留原view.snapshot引用，避免改变模板和prepared_id。241的26对象完整等同性提供证据。没有生成新事实或修改冻结PUBLIC对象。235初次沿用旧保护快照接口产生的额外读取和时间也保留。

截至264：PUBLIC累计45/48次编译尝试，离线新包36.61068690015236秒；真实开发尝试0。诊断state原12占用不变。新行为逐项测试，没有全套重复执行；后续只对实际阻塞项定向复验。

G0真实320根HMAC、确定四根、旧2403计划元数据流式盘点的正向路径必须由程序双轴通过后的真实G0验证；PUBLIC一根不用于虚构四根选择。原始大对象、依赖、probe未在实施阶段读取；最终真实G0/G1结果另行归档，不以PUBLIC通过代替。

计量口径：原guard墙钟含启动、失败及收尾；Windows Job记录树内存峰值及IO；计划窗口每10ms采样私有内存，并另列进程生命周期峰值上界与控制器残余。原生文件编辑/控制材料、Conda临时文件采用单独保守磁盘上界，生产输出每次尝试写入累计，删除不退款；不能把采样峰值或保守上界误称精确物理磁盘/逐根峰值。

98c09de首次双轴：Standards 1个阻塞、Spec 2个阻塞，原报告分别保留。输出mkdir之前缺少新包路径门（两轴共同发现）、Q1/Q2编译依赖未全部纳入候选门。

- 265_output_path_red→266_output_path_green：系统os.mkdir陷阱证明生产prepare和独立snapshot在越界输出下尚未有任何目录副作用即拒绝。守护同时覆盖mkdir/rename/replace/unlink/rmdir；既有只读目录保持无变化。
- 267_compiler_binding_red→268_compiler_binding_green：独立snapshot必须包含evidence_verification、quality_fusion及其sim_normal/sim_scenarios导入闭包；对读取边界返回变化后的编译依赖字节，生产与独立check-pilot均在编译前拒绝。实际只读源文件未改。
- 程序/receipt/candidate门绑定四个白名单文件加11个只读编译/导入依赖，共15件；guard运行中每250ms检查源码变化，检测即终止Job。读写量分别记录Job与守护本身。

268之后PUBLIC仍45/48、真实0；离线包累计37.888368300162256秒。原生编辑/控制材料和未单独观测的启动小临时文件另保守计入64MiB，属于6GiB总上限中的数据消耗，不追加额度；Git和受控输出继续逐项另计。
