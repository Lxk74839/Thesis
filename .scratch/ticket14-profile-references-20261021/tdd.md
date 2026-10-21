# 画像引用接口TDD

版本：prompt rsm-role-composer-0.3.0；profile Schema rsm-profile-references-0.1.0；核心runner0.2.0、生产4Router runner0.2.0。破坏性接口修订不兼容旧value复写响应，A4仍失败。messages[*].response.message.content保留原模型业务对象，profile_facts单独保存程序值及来源role_message_id；每条用户事实记录H_sha256/pointer/fact_sha256/preference_status；商品事实记录原citation、原件JSON哈希及事实哈希，值和单位均从已取得原件派生。

history_red：新的两字段引用响应被旧生产Schema拒绝，RED→改Schema/解析/运行器后GREEN。product_red：无value/unit的属性引用被旧Schema拒绝，RED→只改同类citation绑定合同后GREEN。H变化、越界/非法JSON指针、旧错误value、失效receipt/version/pointer均拒绝；未知状态原样保留，不产生偏好推断。原相等/发布/证据规则保留。

final_profile_directed：6项PASS（4引用/小入口测试、完整S生产PUBLIC、直接影响的冻结条款拒绝回归）。完整S用虚构长历史，经生产prepare/normalize、reasoning元数据、opaque工具续接、用户/商品画像及原发布，9次合成模型响应。原始用户观测无value，派生事实等于冻结长原文；商品derived哈希存在。模型改写value只用于明确拒绝的旧合同用例；不是A4原审计回放。缺usage仍unknown/incomplete。

quality和assessment为现有主机计算状态（批处理已用assessment_receipt_id），保留原合同；没有为此引入虚构citation/receipt。仅原件事实value/unit属本次相同复写问题。无真实D1/S执行，未读实际Key或评价、未重跑上游全套。固定候选双轴后仅独立PUBLIC一次，A5未接线/未授权。
