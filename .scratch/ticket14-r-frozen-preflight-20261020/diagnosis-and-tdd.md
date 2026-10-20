# 非执行真实预检诊断

原失败证据：../ticket14-r-baseline-20261020/result.json指向原audit；完整性pin记录于package.json。诊断仅读取原审计及新的真实安全装配，不调用RecommendationRun.run/取证/排序/发布，不创建真实attempt或消费新R许可。

反馈命令：& .scratch/ticket14-r-frozen-preflight-20261020/check.ps1 -Label <新标签> -m unittest tests.test_p1_frozen_preflight.FrozenPreflight.test_real_1493_candidate_assembly_passes_complete_preflight_without_execution

001、002原实现两次稳定RED（unittest分别0.094/0.090秒），异常failed_protocol/runtime_preflight_failed，与原症状一致。已将循环缩至真实装配/工厂/_preflight；1493候选及冻结身份不能缩减，否则改变C hash引入另一失败，不再是原错误。无需完整R来诊断。

三项可证伪假设，已在修改前向用户展示：

1. 旧来源根不含合法冻结snapshot；只补精确冻结来源准入后，完整函数应通过。
2. 若存在任务/视图或safe input指纹错配，只修来源仍失败；独立条件表应显示对应false。
3. 若存在队列/证据首项/零模型预算接线错配，只修来源仍失败；对应条件应false。

preflight-conditions-before.json覆盖全部适用条件：预算绑定、schema、执行种类/开发身份、R/necessary、K/clauses、C唯一及长度、scores合法值、C及base_scores hash、消息root/H/clauses、装配投影hash、source_ref相等、旧路径根、joint C/b/batches、首证据候选、R四项额度/预留；quality、S/M、PUBLIC/on-demand分支明确不适用。只有旧路径根false，其余适用项true。

003仅修来源准入后，完整真实函数GREEN（0.099秒）；支持假设1，当前输入下不支持2/3。preflight-conditions.json为修复后的完整条件表；旧根判定仅作informational，实际采用frozen_source_error=null的精确冻结校验。没有删除原身份、消息、完整性、队列或预算检查。

修复限定已验收PILOT/parent/D1/R task/V00；从原冻结manifest及五组件校验取scene和root pin，核对C/H/base hash、view/snapshot身份、双侧精确ref、路径重解析/无reparse、实际bytes/SHA和快照身份/核验时点。任何其他sim目录或临时路径不获得能力。新诊断日志在独立临时输出目录，快照未复制、未改字节或标PUBLIC。

004回归11项通过（1.358秒）：本包6项真实非执行准入（含多变体）、直接相关原R接线5项。原先手写PUBLIC对象套用D1身份的测试改为必须拒绝；真实PUBLIC R自身仍可发布，避免把夹具借作冻结开发来源。负例均首次已满足，不制造RED；内容改变在文件读取边界注入，冻结文件前后hash不变。

所有预检的预算模型/工具/候选用量均0，guard网络/凭据/评价访问计数0。没有真实推荐、评价或API。无临时生产日志或调试分支；诊断表和回归测试作为持久证据保留。
