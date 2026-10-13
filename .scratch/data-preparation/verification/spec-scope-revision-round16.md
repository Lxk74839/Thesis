# Spec 第十六轮复审

基线 fb5eff2d09bca20381529a5da5dac9c479a28acf；目标 a35bb0ba1eff36c98eac6a992a398519397a78a4。完整固定差异静态审查，未运行代码或测试。

规格依据：已采纳的 scope-rule-revision-draft-20261012.md 正文、scope-revision-execution.md、spec.md 与工单04/05。

(a) 草案55/57/58、spec72/80、04:10/12、05:9/12：公共入口、独立版本、全源迁移与父商品全部评论的实现无其他新增缺漏；新增核对脚本无生产导入，并记录自身摘要及检查范围。尚未执行最新全源验收，不将预检当验收。
(b) 草案9/39/43/59、05:18：A粮种不变，未知不补真实事实，评论仍属父商品，06仍只条件诊断，无新增扩围或冻结。
(c) P2，草案20/30：identity_catalog.py:83-86 的内联 ingredients: 识别仍受 not active 限制。公共行 title="Raw rice kernels", features=["Ingredients: Rice. Product ingredients: Wheat."] 把第二份明确完整标签在103-104行续接进第一列表，118-128行误记 declared_outside_scope，最终排除；应保留两份声明并 pending/conflict。第二句改为 Product ingredients: Rice. 则误 unresolved，应一致单粮。普通 Salt 续文仍须保留。

上轮 made of/from 100% 重复声明及连续配料控制闭合，旧回放保留；其余A边界、作用域、零低空与输入隔离无新增发现。本轮1项P2，待公共复现与修复。
