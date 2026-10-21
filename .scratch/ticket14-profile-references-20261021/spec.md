# 画像事实引用合同v1与一次独立PUBLIC

BASEbab6bfb，继承API协议。A4 pointer有效但模型复写value不等是已确认事实，旧A4保持失败。本轮明确破坏性接口修订：用户画像observations只含pointer/preference_status，程序在冻结H及H_sha256匹配后解析原值，保存H哈希、pointer、事实哈希、原值及原样状态；原模型消息独立保存，不覆盖、不丢弃旧value或强制转history_fact。

同类商品原文属性复写改为attribute+已有citation(evidence_ref/receipt_id/target_id/version/pointer)，严格绑定实际取得原件后派生value/unit和事实哈希；商品核验assessment/quality是既有程序状态，不新建未经取得的证据引用。原顺序/完整覆盖/证据判定、六角色、推荐与发布规则不变，不读取参考或评价。

公共测试seam：生产composer/Schema/normalize→明确引用解析函数→完整RecommendationRun(S)。用虚构长历史覆盖合法/越界/无效/冻结H变化、旧错误响应拒绝、商品citation失效及原始响应与派生事实分开；全S生产PUBLIC含reasoning/tool续接/画像/发布。记录prompt/Schema/runner新版本，旧失败不重写。定向TDD、固定同候选独立双轴后1次独立PUBLIC用户画像生成，16KiB/512/HTTP120/执行180秒，4Router/gpt-6-luna，无retry/count/other，费用null、未知计量不填零。

离线900秒/累计6900/收尾120，写128MiB/内存4GiB，P1共享64MiB。原账/历史超限保留、用户等待不计，本轮不授权A5或完整S/M/异常/Q/正式100。恢复预算须列历史5次/原余7，现有完整离线9次，明确足够新预算为待确认，不自动启用。
