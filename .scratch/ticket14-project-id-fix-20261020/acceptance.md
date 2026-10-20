# project_id定向修复增量验收

结论：project_id代码阻塞已解除，本独立修复包通过。代码候选cbff7f9cca24b4b8a13e581d59d0ce305da1d6c4，BASE 1550051ef6d2e24f17e281c887f2526e74186ef5。范围仅P1准入，生产代码只增加三行，不重验或替代A及既有P1离线贯通验收。

## 验收证据

- R/S/M共用准入要求project_id为非空白字符串。缺失/null/空串/纯空白/整数/bool/list/dict共24个组合，prepare_p1和execute_p1均返回terminal=not_started、started=false、missing=[project_id]、provider_requests_sent=0。
- 各方法先用其余条件全满足的PUBLIC配置证明ready/missing=[]，再单独改变project_id；装配哨兵、凭据/私有文件审计、counter和send均0。完整有效配置仍ready、started=false，token/usage为null，费率原样保留。没有把其他缺项拦截当作修复通过。
- 真实RED→GREEN：旧代码24个subTest错误放行；三行修复后新增2项全部通过。有效配置控制首次通过，未制造RED。另跑直接相关准入回归3项通过，详见tdd.md。此前11项和29项整套结果继承，不重跑；没有运行真实流水线。
- 同一BASE...candidate独立Standards/Spec均0项问题，详见review.md。审查后代码未修改。无非阻塞P3扩展修复。

## 本修复包资源

最终记账37.4304267/180秒；原离线累计1468.8550727001366/1800秒。保守写入上界8,534,827/67,108,864字节，剩58,574,037字节。原生源码/文档/Git/收尾30秒和8MiB已预计，非实测；审查工具时间另记。每次测试前后各有一条资源检查，共3组；均能容纳测试及30秒/8MiB收尾，无到限后补查。

测试子进程沿用4GiB Windows Job（其中64MiB留给守护），实测Job峰值22,585,344字节；原生全局内存峰值未实测。资源结果采用既有账和保守写入上界口径，不声称完整文件系统写入或原生内存测量。详见package.json、resource-checks.jsonl、resource-closeout.json。

继承离线账原有字节前缀SHA256复核一致，仅追加p1idfix_；T0账SHA256不变。上一包保守写入46,105,370字节超过33,554,432字节，其not_accepted及12,550,938字节超额继续保留；本包没有追溯扩额、冲销或改写旧记录。新包通过仅解除本次代码阻塞，不将旧包资源验收改成通过。

本轮实际凭据读取、生成/count/其他API、真实P1推荐/评价/统计均0；冻结数据、正式计划、论文和评价器未修改，无新依赖。

## P1真实执行仍未授权

继续引用现有集中草案：[P1执行条件与一次授权草案](../ticket14-p1-wiring-20261020/P1-conditions-and-authorization-draft.md)，不重写方案。

仍需决策并绑定：可信完整输入counter及其回执/端点、渠道分组/费率和共享预算、上下文/正文/输出边界、完整RootBudget/final_reserve、可信storage_guard与独立P1执行授权。若希望计数/费率未知时运行，须一次单独确认仅P1计数豁免、未知费用接受及对应预算策略实现；不能套用PUBLIC许可，正式100用户合同不变。CLI不会仅因JSON填写完毕自动具备真实执行条件。本包不启动P1，不追加新联网许可。
