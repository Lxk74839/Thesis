# A6同候选增量审查

BASE8a6926656b1e8608c5a896784ea515c2f6e18dae；candidateffd1a6e2847f2c45332eda0e60637b860a04b677。

## Standards

/root/first_diag_standards：PASS。改动限精确A6授权、共享/本次额度及首dispatch检查点。检查点在原调度合同后观察，通过后同进程继续，失败停止；复用既有有界脱敏捕获，未改调度、证据、排序、发布规则。历史账保留，128MiB/64MiB真实守护保持，测试覆盖拒绝及不重复发送。无阻塞或需要扩修的设计气味。

## Spec

/root/first_diag_spec：PASS。A6独立grant/run/claim，旧账追加保留；本地12/91612及共享20/157148发送前双限；余额1663.8197406、根-20/Job-10/wait5及最终1/1500/145沿用。首dispatch解析和原合同后仅建一次≤100KiB检查点，不可回放则停止；原进程继续、不重发前三步。成功9轮/JSON或合同失败3轮合成覆盖，不将A5原因或真实A6判成功。

两轴仅静态审查同一BASE...candidate，无测试/API/实际Key/真实数据读取。Standards剩余发现0，Spec剩余发现0。未修改的解析1ba32b4、画像/原生续接及上游直接继承。
