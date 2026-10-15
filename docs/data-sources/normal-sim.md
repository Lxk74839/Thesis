# 正常SIM供应链组件

工单10通过唯一入口 `prepare_data.py --stage sim_normal` 生成同商品SIM正常基准，以已验收 `grain-A-1.1.15` 目录为输入，仅投影 `parent_asin/crop`。确认依据为 `.scratch/data-preparation/ticket10-preimplementation-confirmation-20261015.md` 第10节 I1—I6 及本次授权归档。真实评论仍只属于父商品。

固定 profile 为 `normal_six_stage_v1`，数据版本为 `sim-normal-1.0.0`。每父商品一批次、六阶段事件、八材料和十五接收登记。所有新增原件标记 `source=SIM`，策略披露 `project_constructed_simulation` 和 `simulated_allowlist_no_crypto`。本地接收不表示密码签名通过或已经上链。

在项目根运行，显式使用已有 Thesis 环境，无新增依赖：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TMP=Join-Path $PWD '.tmp'
$env:TEMP=$env:TMP
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage sim_normal --catalog-record records/catalog/grain-A-1.1.15.json --sim-config config/sim-normal-1.0.0.json --output-root .
```

配置、协议和目录路径均相对于固定项目根解析；输出根也必须在项目内。拒绝其他阶段参数、未绑定协议、非法结构/类型、目录绑定不符和不合法时间/授权。阶段错误退出2并输出稳定原因码，不包含输入原文或宿主路径堆栈。

六稳定文件位于 `data/sim/grain-A-1.1.15/sim-normal-1.0.0/`：batches/events/materials/registrations JSONL 及 policy/snapshot JSON。UTF-8无BOM、递归排序紧凑JSON、整数、单LF结尾；对象摘要不含LF，文件摘要包含全部字节。ID使用已确认的NUL分隔SHA-256合同。τ固定1791417600000，封存1791375000000；历史事实无任意TTL，零售状态使用明确的半开有效区间。

主记录位于 `records/sim/grain-A-1.1.15-sim-normal-1.0.0.json`，stdout返回相同对象。生成成功只标记 `normal_sim_prepared` 与 `pending_separate_record`。一致复用返回旧记录，不更改其字节；来源/配置/生产器或组件变化拒绝覆盖。暂存及构造失败留在项目 `.tmp`；中断发布不自动恢复或覆盖。

独立核查使用标准库，直接读取原件、登记、策略、快照及请求，不导入生成器：

```powershell
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python .scratch/data-preparation/diagnostics/verify_sim10.py --record records/sim/grain-A-1.1.15-sim-normal-1.0.0.json --audit-root data/sim-reference/grain-A-1.1.15/sim-normal-1.0.0/r1-reference-1.0.0
```

审计根必须新鲜、位于项目内且与原件隔离。程序写私有 `reference-r1.jsonl/check.json`，核查失败退出2并保留失败check；不会写正式接受记录。参考只判断“指定采样事件的SIM-Q1报告结论为pass”，不会把六阶段齐备直接当资格，也不加入08模型可见组件。

正式接受需另外完成公共测试、全量独立检查、新空根稳定字节复现、上游保护及755f277固定起点的Standards/Spec审查。接受记录单独绑定证据；不回改生成主记录。实际数量及结论另见工单10最终接受记录。

本轮不建设异常场景、正式联合任务、模型工具或账本部署；不作食品安全、当前现实品质、真实独立机构佐证或样本充分性结论。正常SIM组件通过与正式联合实验完成分别报告。

历史失败：2d3953b曾因S2整数漏检停止接受，原证据保留于ticket10-blocked-sim-normal-1.0.0.md。

当前接受（2026-10-15）：本次授权修复后，sim-normal-1.0.0实际1494父商品/1494批/8964事件/11952材料/22410登记，独立R1 Supported=1494，其余0。226项完整回归、固定755f277两轴无阻塞、六稳定组件及参考新空根字节复现和上游保护通过；独立接受记录为records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json。生成主记录仍保留pending_separate_record原字节，正式联合实验尚未完成。
