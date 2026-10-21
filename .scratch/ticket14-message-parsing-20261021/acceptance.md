# 响应解析离线诊断验收

BASE858409a；代码候选1ba32b4551fb0a0dd5871b16d5c0b48179ff13a0，两轴PASS见review.md。API生成/count/other全部0，未启动A6/M/正式100用户实验，未读取实际Key，未改数据、画像、推荐或发布逻辑。

已证实：旧normalize把所有message的output_text合并后解析单一角色JSON，合成commentary+合法final_answer因此被拒绝。官方SDK聚合文本本身合法；问题是本地没有按phase区分中间消息与严格业务输出。来源见protocol.md，实际读取官方部署/文本/函数调用/会话状态指南，未从A5字段长度推断phase。

修复：同message内按顺序合并分块；仅解析唯一非commentary业务message。未知phase/type、多个业务项、工具与业务JSON混合、incomplete message/function_call、坏JSON/重复key、角色Schema及工具参数错误继续拒绝。不截取、不补JSON、不取最后项；原完整native输出与顺序仍通过protocol_ref续接，reasoning及画像引用逻辑继承。

失败证据：工程及严格ModelAdapter失败回执/审计的raw_response.business_output记录原output_index、phase/status、原始文本分块及UTF8 SHA256，canonical序列化最多96KiB。只含必要业务白名单项，绝不复制请求、HTTP头、reasoning正文/密文。命中实际认证回显或凭据样式（含跨分块拼接）、超限时整份正文省略，明确replayable=false与原因，不伪装完整回放。合成落盘→读回→生产normalize验证相同JSON错误；合法usage及无重试规则保持。诊断正文不应直接打印到终端；按原本地回执和写入守护保留即可。

反馈命令及RED→GREEN证据见tdd.md；最终14项新增通过，直接影响回归并集15项通过（6生产协议、6既有诊断、1完整S PUBLIC离线、2原sender/严格usage），总计29项不同测试。完整合成S为9次fixture调用，绝非真实S。首次已有行为如实GREEN；本次新RED包括phase拼接、重复key、缺失capture、incomplete调用及审查发现的分块认证回显。未重跑上游全套。

A5仍只能确认：第三轮dispatch，HTTP200/gpt-6-luna，两个message项，json_decode第1行112列；原正文、实际phase值、当时各文本分块及是否混入进度文字均未知，不能恢复旧错误文本或改判A5。本包关闭已复现的通用解析缺口，不能宣称A5真实根因已闭环。

恢复完整S尚缺新授权及真实业务证据。共享账保持8/17调用、65536/132572输出参数、136.180259399931/1800秒；余额9次/67036/1663.819740600069秒，不能复活A5。已有完整离线S需9次，余额仅够相同路径且无额外调用余量；本轮不消费。

最小采集方案（待确认，未启用）：若渠道可导出已存在的第三轮response_id对应业务message，取得仅含index/phase/status/output_text的脱敏导出后先离线回放，渠道是否支持未知。若无法导出，则另授权受控新尝试仅推进至dispatch响应，按当前正常路径预计最多3次生成、输出参数最多24576、每HTTP120秒、并发1/无重试/count/other0，完整1493及输入隔离不变；取得新业务证据即停止并离线回放，不顺带运行完整S。该新响应仍不能称为旧A5回放。实际新路径/额度须最终确认，不自动追加。

本包900秒/120收尾，累计8700；继承历史7768.934749400534及所有真实超限。恢复检查曾把两次消息之间用户等待计入，已保留误记行并追加更正：以最终候选提交时间及首次恢复检查文件时间划界，两侧各保守保留30秒为工作，只排除中间等待10797秒；不冲销任何历史工作。复用计时器的排除文件名为execution-exclusions.jsonl，其中scope明确user_wait，不是实际执行。最终资源与旧证据完整性见settlement.json，原账仅追加。
