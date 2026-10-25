# Thesis 项目迁移交接

日期：2026-10-19（Asia/Shanghai）。D盘文件、环境及Codex项目入口切换已验证。旧C盘副本已由用户删除，并复核目录不存在，迁移与清理完成。

## 后续工作入口

- 唯一工作根：D:\Work\Codex\Project\Thesis。
- Thesis环境：D:\Work\Codex\Project\Thesis\.conda\envs\Thesis；使用 conda run -p 显式指定。
- 项目TEMP/TMP为 .tmp，Conda包缓存为 .conda/pkgs，pip缓存为 .cache/pip；环境变量已按新根绑定。
- 源码、数据、原始文献、论文、未提交脚本、reports及Git历史已复制。已验证的大型T0-A目录在 data/ticket12-t0/catalog-0.1.0，迁移时复用该副本。

## 继承状态

- Git HEAD：69918e613fd700fd33c53a0ded5557b604487fcc。原未提交的两份诊断脚本和reports保留；本次仅在D副本更新AGENTS.md并新增迁移记录/本说明，未提交新算法改动。
- T0-A仍为T0_A_incomplete：2403/9600份计划，N=U=22113；目录迁移不构成实验或完整覆盖验收。
- 原离线实现账：data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl，累计217.7244063001417秒，原1800秒总额剩1582.2755936998583秒。
- 原T0共享账：data/recommendation-runtime-audit/ticket12-t0/resource-ledger.jsonl，累计1797.3523884000024秒，剩2.6476115999976173秒。
- 两账迁移前后SHA256一致。本次文件迁移/环境验证独立记录，没有重置或追加任何实验额度，没有执行C/B/P1或供应商API。
- 规模诊断任务在原聊天中被用户停止。已有diagnose_t0_costs.py和analyze_t0_payloads.py及小样证据保留；继续时先盘点现有证据，等待恢复方案确认，再开展需要新授权的实验。

## 路径与历史记录

- 当前程序按D根解释项目相对路径。运行前核对工作目录和sys.prefix均为D盘新地址。
- 旧验收、SHA、来源记录及日志中的C盘运行路径保留为当时事实；不要批量替换历史记录或重写既有验收。
- 原catalog-0.1.0.archive.json是此前单目录复制时留下的历史定位记录。当前本项目下的data/ticket12-t0/catalog-0.1.0可直接访问；无需使用旧C盘路径。
- 原聊天“12.模型绑定与调用预算收口”记录的cwd仍为旧C盘地址。用户在Codex添加D盘项目后，从D项目新建接续聊天；旧聊天保留为历史记录。

## 验证证据

- records/storage-migrations/t0-a-20261019/verification.json：22125份大型目录文件，91556152080字节，SHA256逐文件一致。
- records/storage-migrations/whole-project-20261019/verification.json：其余10758份文件，27319755825字节，SHA256逐文件一致。
- 同目录environment-verified.json：18个Conda包的名称、版本及build与原环境一致，使用项目包缓存离线克隆。
- 同目录runtime-validation.json：新cwd、解释器、prefix、TEMP/TMP、缓存路径及22份源码语法检查。
- 同目录project-validation.json：原Git HEAD、迁移后状态、两账摘要及剩余额度。

## 界面切换与旧副本清理（已完成）

1. 原Thesis项目入口已切换为D:\Work\Codex\Project\Thesis。
2. 新聊天已完成迁移自检，工作目录、环境前缀及既有资源账核对通过。
3. 此前自动审批拒绝过C盘递归删除。用户随后手动删除旧C盘Thesis目录；本次复核该目录已不存在，D盘项目、解释器及T0目录仍存在。
4. 清理后C盘可用空间为182.86GiB，较清理前增加110.87GiB。后续操作统一使用D盘工作根。

