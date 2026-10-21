# 已授权PUBLIC及A4实际执行

受审源码与2e93b52一致；继承既有6项测试及同候选Standards/Spec PASS，无代码开发、测试或重复审查。启动前两个许可无claim/attempt，共享3调用/24576输出参数/46.387549秒与P1字节数均未变。使用新210秒段、预留60秒，旧600秒包保持结算。

- PUBLIC：1次，HTTP200/gpt-6-luna，生产composer/Schema/normalize返回精确[c1,c2]，PASS。正文2116字节、cap512；原生351/66 Token，reasoning31为输出子量；执行4.607885秒独立记账。
- A4：独立run `P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A4`，完整1493候选；2次HTTP200/gpt-6-luna，真实reasoning两轮解析成功。条款校验通过后在用户画像阶段failed_protocol/invalid_profile停止。只读核对旧审计：字段合法、pointer在H且可解析，但value与该历史位置原值不相等（resume-failure-structure.json）；未改旧审计、未修复或补发。
- A4原生input511324/output282，reasoning146属于输出子量；费用null、整体计量unknown/incomplete。执行43.742826秒独立记账；count/other/retry=0。PUBLIC不占S共享账。
- 实际候选证据取得0、核验0、G=[]；publication=null、recommendation_count=null，不是valid_empty。2次模型预留已结算，engineering_limits_settled=true；发布链未闭合，S未通过。

控制回执：`.scratch/ticket14-s-120-20261021/A4/execution-result.json`；审计和预算：`data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A4/audit.json`、`budget.jsonl`。PUBLIC控制证据在本目录PUBLIC/，实际小结果在P1根PUBLIC-CLAUSE-CONTRACT-20261021/result.json。小型回执/结构证据归档，不复制真实输入/审计原文。旧not-started记录保留为历史，不作本次回执。

共享S现5/12生成、40960/98304输出参数、90.1303745/1800秒；算术余额7/57344/1709.8696255秒。A4与PUBLIC许可均已消费，无A5授权。M/异常/Q/正式100未运行，任务14未完成。准备/归档、继承写入及实际执行分域结算见resume-resources-20261021.json；原账只追加，历史超限保留。
