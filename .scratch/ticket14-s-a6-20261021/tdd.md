# A6定向TDD

命令：.scratch/ticket14-s-a6-20261021/check.ps1 admission_directed -m unittest tests.test_p1_s_a6 tests.test_p1_s_a5.A5.test_old_claim_markers_still_refuse_reuse_and_execution_time_keeps_all_attempts tests.test_p1_s_a5.A5.test_A5_retains_five_old_claims_and_enforces_both_new_limits

quota_red：保留8个历史8192发送意图后，旧控制链拒绝A6新请求；最小A6专属共享20/157148、本地12/91612后GREEN。历史字节前缀保留，11普通8192+最终1500恰到新上限，超额拒绝，旧A5仍旧上限。

checkpoint_red第一次因合成目录不符合既有RootBudget约束而失败，不算功能RED；改到既有PUBLIC runtime目录后，真实生产流程确因没有dispatch-checkpoint.json而RED。新增A6观察点后GREEN：正常合成S9调用并发布，JSON错误/调度claim_ids逆序分别3调用停止；同进程只一个dispatch，重复run返回缓存不新增调用。完整reasoning及工具续接/画像引用均沿生产路径；无usage保持未知，正文不含内部推理/密文。

admission_directed六项PASS：4新增（额度、同进程检查点三分支、真实1493非执行准入/发送控制链、A1—A6执行时间累加）+2原marker/旧A5额度。非法13调用/91613输出/1643820ms和缺run守护在装配前拒绝；1493实际装配_preflight通过，非零递增时钟的生产prepare/reserve/invoke抵达PUBLIC transport哨兵，实际Key/网络/评价读取0。原marker/claim/回执/attempt拒绝路径直接复用测试，不制造RED。

所有返回均PUBLIC fixture，不冒充真实A6。未重复上游全套、旧R/worker或独立联网探针。测试前后资源见resource-checks.jsonl和原追加账，使用Thesis Conda及原Windows Job守护，无依赖安装。
