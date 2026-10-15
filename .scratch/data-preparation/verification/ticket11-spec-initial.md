# Ticket 11 Spec 初审

固定基线 `2e6594e5d207f4f1798639dad652a9d140f17ef8`；候选 `ada0f6bdfbdfada78699ccde5164789f85376df2`。仅审本工单增量；正式生成和接受尚未执行不列为缺陷。

- **P1，阻塞：一致复用信任可变的旧清单。** `sim_scenarios.py:369–408`只核对文件与旧主记录自报摘要，未与固定输入应生成的字节核对。审核稿357/436要求“相同输入/配置/代码及全部输出字节才一致复用”“变…输出拒绝覆盖”。公共探针把V00报告改fail并重封所有外层绑定后，S1仍退出0/prepared，应为2/output_conflict。
- **P1，阻塞：指定采样未落实。** `diagnostics/verify_sim11.py:526–583`只要求任意sample/report互相匹配。审核稿47/296要求“基准…指定采样”“不能任取同商品另一采样”。追加同事件另一采样及完整fail报告，原指定采样仍pass，实际却从Supported变Conflict。
- **P1，阻塞：跨声明范围的v2可非法替代。** `diagnostics/verify_sim11.py:475–524`仅由动作/登记对象键选头，未核对前后kind/sample/test_scope。审核稿95要求“对象/声明范围不变”才可替代。V09的v2合法改成SIM-OTHER或另一sample并重封后实际Pending，原指定声明应继续由v1支持；修复须保留96/H08的合法头失效不回退。
- **P2，阻塞：请求版本及字符串边界漏检。** `diagnostics/verify_sim11.py:108–115,219,316–319`漏校验请求schema版本、git_head_sha及拒读target_id类型。审核稿302要求“严格…未知字段”，369要求“不支持…结构…退出2”。请求2.0.0及git_head_sha=0实测均退出0写参考；拒读键同类缺口须集中补齐，合法bool保留。
- **P2，阻塞：check输出合同不完整。** `diagnostics/verify_sim11.py:642–647`缺外层完整性状态及拒绝原因汇总；审核稿373明确要求两项。应从实际检查和参考拒绝项聚合，不能填预期答案。

前三项及边界实证分别见 `ticket11-author-probes-initial.json`、`ticket11-author-version-probes-initial.json`、`ticket11-author-wire-probes-initial.json`。静态审查未运行项目代码，动态探针由父代理在Thesis环境顺序执行。

非阻塞记录：私有计划尚无304所述显式共享集合ID，但已有跨视图相同的selected_parents/selection_version，当前共享关系可核对。未发现新增模型运行、用户关联或正式统计范围扩展。

合计：5项阻塞（最高P1）；1项非阻塞。
