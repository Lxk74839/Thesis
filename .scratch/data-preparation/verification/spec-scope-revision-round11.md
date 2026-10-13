# Spec 第十一轮复审

基线 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；目标 `0638dd6a61480b3b1bd08909b89a7b88464bb869`。完整静态复审，未运行代码。

**P2：加糖早退绕过完整声明冲突。** `identity_catalog.py` 的 outside_objects 早退分支：`title="Raw rice kernels with sugar"`、`details={"Ingredients":"Rice"}`。先得到完整单粮声明，却因 sugar 被当 A 外对象直接 excluded，绕过后续新增冲突处理。草案 `scope-rule-revision-draft-20261012.md:13,20` 要求未解决关键成分反证／实质矛盾保留冲突。应识别明确“谷物加糖”与纯 Rice 声明的矛盾，保持 pending/conflict 和双方来源；Rice Sauce＋单粮原料不是同一矛盾，仍须按 A 外形态排除。主代理已反馈公共 RED 复现，修复属于下一固定提交，非本目标。

上轮两项、Raw／Not raw 与完整声明对加盐／多粮的控制已闭合。A范围、否定／用途、未知非验证、父商品全评论及零低评空文本、迁移／旧版／独立 oracle 未见其他新增缺口。06未批准条件分析无扩围或参数冻结；待执行全源结果不算漏项。

Spec：1 项 P2，最严重为明确成分矛盾未按冲突隔离。
