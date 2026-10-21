# A5固定候选增量审查

BASE：88b71d3fe95afd340702302e71ac27ca38b1815c
candidate：ff7bcb18bddda78e183c5decabe2328cb7d47ae6

## Standards

独立代理 /root/first_diag_standards：PASS。精确A5授权、共享/单次额度及真实双层写入限制符合AGENTS.md的最小修改要求。旧证据与账保留，画像、推荐、发布未修改，无依赖或框架扩展。无阻塞项。

## Spec

独立代理 /root/first_diag_spec：PASS。历史5次/40960及执行账保留；A5自身12/91612、共享17/132572发送前累计约束；旧run仍用旧上限。执行1800秒扣历史余额，HTTP120及最终1/1500/145秒保留。准入强制共享128MiB、run64MiB真实守护；旧marker拒绝；完整1493非执行预检和生产发送链哨兵测试覆盖。无阻塞项。

两轴均只读审查同一BASE...candidate，未运行测试/API或访问实际凭据、真实数据。复用此前画像/协议及未修改部分验收；新定向测试见tdd.md。不以离线通过判定真实S成功。
