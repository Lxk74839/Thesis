# A3真实D1/V00/S：已执行一次，未通过

受审候选2513b421ab643689f09882d0317570c78c6eaba4，BASE6e0bb40。继承e5ea9ed生产协议及既有A/R/worker验收；本轮无独立PUBLIC联网探针。新增精确A3授权和既有入口/共享时间账接线，未改方法、输入、工具、Schema或发布协议。

## 执行前

按tdd.md，精确A3未接线先RED→局部接线GREEN；共享执行账漏A3先RED→枚举修复GREEN。完整PUBLIC S经真实prepare/normalize/工具/发布9轮成功，包含合成reasoning非空summary/content、opaque密文及工具续接；无usage保持未知，不是旧响应回放。原测试误把独立角色首轮也要求带前角色密文，修正测试预期后未修改生产隔离行为。最终6项定向测试PASS（3新增、3直接影响回归）。

真实D1完整1493候选prepare_p1→装配→build_runtime→非执行_preflight通过，Key/网络/模型/评价读取均0；最终1调用/1500输出/145秒与冻结预留、HTTP120及外层回收链保持有效。独立Standards/Spec对同候选均PASS（review.md）；随后生成A3-ready并立即执行。未重复未受影响的全套。

## 实际结果

- authorization_id：`S-COMPLETE-ONCE-20261021-A3`。
- run_id：`P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A3`。
- task_key：`a4f49f4b6b418d132b326f9b028c682e8e4d429f8cd96e9eb50592d081dae5a4`。
- 完整1493候选；实际POST602583字节；仅1次Responses，HTTP200，gpt-6-luna，request_id=null，response_id见原回执。count/other/retry=0，独立执行Job15.4700591秒，4GiB限制有效。
- 原生可接受计数input255485/output212，cached0、reasoning112属于212子量，不额外累计；兼容native_usage字段null，完整原始usage未知，费用null，计量unknown/incomplete。
- 原生output[0]为reasoning，content/summary均空数组，encrypted_content为长度3064字符串，status缺失；生产解析成功。output[1]为message，同样解析成功。未保存密文或内部推理正文。
- 之后在运行器分析业务校验停止：`failed_protocol / changed_request`。已确认`data`恰含necessary_clauses、observations，observations为数组；returned necessary_clauses和冻结binding各为2项数组，但值不相等，触发recommendation_runner.py:358-362。安全布尔与类型/长度见failure-structure.json。没有依据把它归因于reasoning解析；更深生成原因未知，本轮未修正、未放宽该校验。
- reasoning真实出现且解析通过；没有发第二次请求，protocol_followup_rounds=[]，所以真实reasoning上下文续接仍未覆盖。

## 实际A/G与闭合状态

原有完整候选集合仅是C，不能冒充实际取证范围。audit.evidence.acquired中candidates={}、context={}；仅绑定/候选绑定元数据，未取得候选证据、未核验，verified_count=0，G=[]。publication_path=null、recommendation_count=null，**不是valid_empty或已交付0条**。

1次模型预留/实际调用已结算，预算usage model_calls1、request_output_tokens8192、logical_tools/physical_tools/candidates/retries均0；engineering_limits_settled=true，usage_exact=false。审计/预算已落盘，工程发布链未闭合，不判S通过。只封存失败，不启动A4，不追加请求。

真实审计：`data/recommendation-runtime-audit/ticket14-development/p1/P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A3/audit.json`；预算同目录`budget.jsonl`；实际A仍保存在原审计中，无参考补证。控制回执、claim、配置及Job账位于`.scratch/ticket14-s-120-20261021/A3/`；共享请求账在P1根`S-120-CONTROL-20261021/requests.jsonl`。只归档小型脱敏控制材料；不复制包含真实输入的审计/预算为额外副本。

## 共享余额与资源

A1/A2/A3共3/12次生成，累计请求输出参数24576/98304，算术余额9次、73728；执行46.387549/1800秒，算术余额1753.612451秒。A3独立许可已消费，余额不自动变为A4授权。旧A1/A2 claim、审计及回执均保留。

本包离线600秒/预留120、累计5400及写入128MiB结算见resources.json；原账仅追加，历史超限不撤销。A3执行15.4700591秒单独记录并从本包离线时钟排除，用户等待不计入新段。T0及原账前缀校验见preservation.json。

M、异常、Q1/Q2、正式100未运行；S未通过，不推进剩余六M执行。任务14继续未完成。
