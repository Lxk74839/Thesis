# T0-A有限存储修复：逐行为TDD记录

日期：2026-10-19。人类授权见authorization-t0-a-storage-repair-20261019.md，原提案及两份诊断脚本原字节先归档于c8533d8。固定增量BASE为69918e613fd700fd33c53a0ded5557b604487fcc。公共Seam为PreparedObjectWriter/add/close、iter_prepared_objects、独立检查器CLI及本包必要拒绝门。

全部项目Python采用同一命令结构（环境TEMP/TMP与包缓存指向项目）：

```text
conda run -p D:\Work\Codex\Project\Thesis\.conda\envs\Thesis --no-capture-output python -B .scratch/ticket12-budget-20261018/diagnostics/run_check.py storage_repair_<编号>_<行为> -m unittest tests.test_t0_catalog.StorageTests.<公共行为>
```

原始输出逐条保留在data/recommendation-runtime-audit/20261018-batch/storage_repair_*.txt；原账保存精确秒数、源码指纹、退出码、峰值提交量及磁盘计量。下表编号为实际守护标签中的数字，不是重新运行次数。

| 行为 | RED→最小GREEN / 首次GREEN | 具体信号 |
| --- | --- | --- |
| 完整prepared字节/metadata/身份往返 | 199→200 | 缺公共writer/reader→26件全部字段与冻结原件一致 |
| 两套PUBLIC存储≤旧对象10% | 201首次GREEN | baseline及longH分别26件，已满足，不人为制造失败 |
| 严格去重且保留调用方attempt/source | 202→203 | 重复保存2段→1段，原两条引用与第一份metadata保持 |
| W/P及版本/身份绑定拒绝 | 204→205 | 不一致字节、错误ID/mapper、冲突工具metadata原被接受→拒绝 |
| 旧目录只读兼容 | 206→207 | 找不到新manifest→读取旧组件并核对原SHA/字节 |
| 损坏pack、索引、投影、身份拒绝 | 208→209 | 错摘要/规则/长度/重叠/重复ID被接受→有界解压及完整核对后拒绝 |
| 中断保留完整前缀、标不完整 | 210→211 | 异常仍写complete=true→false并保留已存对象 |
| 文件写失败不发布未写对象 | 212→213 | 第二次实际文件写入替身失败后索引仍有2件→仅保留第1件 |
| 同输入稳定字节 | 214首次GREEN | 两次存储操作pack/manifest逐字节一致；不展开根计划 |
| 超16MiB完整失败原件 | 215→216 | 无记录→保留完整压缩W及失败标记，正常reader拒绝不完整store |
| 独立对象CLI及接受边界 | 217→218 | CLI无check-objects→新/旧两格式26件核对，明确不接受完整目录 |
| 不落盘的真实摘要重算 | 219→220 | 缺recompute选项→从原对象重新压缩/计算组件摘要；文件读取陷阱证明没有复制旧store答案 |
| 独立检查损坏/partial拒绝 | 221首次GREEN | 新核验器已满足各变体，不破坏实现造RED |
| 原完整检查接入新存储、保留覆盖门 | 222→223 | 找不到逐件JSON→新格式可核对；改coverage为不完整仍拒绝。只复制原PUBLIC计划字节，不重新展开 |
| 三件验证先检查T0域 | 224→225 | 新模式未接入时尝试打开原分析stdout，被写保护拒绝；未启动旧worker/读取开发对象。新模式在离线域先返回t0_domain_required |
| prepare-only/count拒绝与新计划0 | 226首次GREEN | 替代sender未触发、原count导出拒绝新store、本包prepare在展开前拒绝 |
| 16项新增行为合并验证 | 227 | 16通过；未运行CatalogTests的生成型测试或其它已接受组合 |
| objects目录联接必须先拒绝 | 228→229 | Windows真实junction曾被reader跟随→逐层检查objects、manifest、pack及旧catalog路径；reader和独立CLI均拒绝，联接目标原件保持 |
| 边界修复后的相关合并验证 | 230 | 17项存储行为通过；仅因上述新修复重验该存储套件 |

本轮没有测试私有hash/parser/helper，没有重新生成PUBLIC事实或根轨迹。新的超界/损坏输入是从冻结prepared对象派生的测试副本，不形成新根计划。文件系统写失败只在系统I/O边界替代；实际writer、reader及独立CLI均执行真实代码。

直接读取旧objects路径的原测试断言已改为公共reader或公开失败存储格式；未重新运行这些需要新根计划的原测试，不宣称已验证新格式prepare整链或全目录生成。原生成CLI在本包活动时显式禁止新计划。编译器与recompute接入同一存储实现，其完整开发执行仍需将来独立授权/接受。

资源基础设施在首次RED前安装：原账前缀绑定、离线本包300秒、T0扩展1860且本包60秒、Windows Job树4GiB、数据/审计写入门及固定输出范围。此安装如实记为授权基础设施，不伪记功能RED。所有上述失败和子进程均计入原离线账，未从T0账扣除或挪用。

截至227，本包原离线账新增13.059852000093088秒，原累计230.7842583002348秒；累计受控数据写入3,183,221字节，守护给出的其它磁盘保守上界1,152,733字节。原T0四行历史未变，三件真实验证尚未执行；须固定candidate双轴无阻塞后才能开始。

首个固定candidate为b1a50e37714edeebee68a8837ee19273df0a56bd，Standards/Spec两份原独立静态报告均为0发现、0阻塞，报告原文保留。其后补充公共边界测试228得到真实RED，按上述229最小修复；未用原静态结论覆盖新源码。修复后固定新candidate并作独立复审，再归档程序接受。

截至230，本包原离线账新增16.490007900079945秒，原累计234.21441420022165秒；累计受控写入4,485,556字节，其它磁盘保守上界1,293,674字节。17项合并验证实际unittest耗时2.593秒，守护计入2.796432500006631秒。T0真实验证仍未启动。
