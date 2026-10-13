# Spec 第十五轮复审

基线 fb5eff2d09bca20381529a5da5dac9c479a28acf；目标 cf35c62e17722de378e314bf7c940bbc2b56d0ff。仅固定目标静态审查，未运行代码或测试。

依据：已采纳的 scope-rule-revision-draft-20261012.md 正文、scope-revision-execution.md、spec.md 与工单04/05。

(a) 草案55/57/58、spec72/80、04:10/12、05:9/12：公共入口、独立版本、迁移依据及全评论保留实现无其他新增缺漏；最新全量扫描与独立验收仍待执行，预检回放不等于全源验收。
(b) 草案9/13/39/43/59：粮种不扩围；Cold Cereal等保留未解形态关系，不推断实际熟制；未知非验证，06仍只条件诊断，无新增越界。
(c) P2，草案20/30：identity_catalog.py:87-90 仅在 not active 时识别新的完整声明。公共行 title="Raw rice kernels", features=["Ingredients: Rice. This product is made of 100% wheat."] 中，第二份明确完整声明在103-104行被续接进第一份配料列表，118-128行误判 declared_outside_scope，最终排除；应保留两份声明并 pending/conflict。第二句改为100% rice，则误 unresolved，而一致完整声明应 declared_single_grain。普通 Ingredients: Rice. Salt 仍须作为连续配料保留，不能任意截断。

上轮salt-free及同义否定修复闭合；新原例修订有来源依据。其余作用域、A边界、评论父级零低空及输入隔离无新增问题。本轮1项P2，待公共复现与修复。
