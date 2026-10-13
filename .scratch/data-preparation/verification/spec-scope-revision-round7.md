# Spec 第七轮复审

基线 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；目标 `d733e8ce437904159e5893d97ab42e0c805b7101`。仅静态固定 diff，未运行代码。

**P2：否定作用域修复仍不完整。** `identity_catalog.py:41–43,156–158`：夹具 `title="Raw rice kernels"`、`features=["This rice is not parboiled."]`，否定不在句首，仍命中 parboiled，结果 pending/field_processing_ambiguity。草案 `scope-rule-revision-draft-20261012.md:29` 要求否定声明单独保存语义角色；L19 允许一致身份／形态证据入选。应按被否定对象划分作用域，不能按位置或整句有无粮种词判断；保留真实预处理与身份否定反证。需公共 CLI 验证。

第六轮原 No oil／Not parboiled 已闭合，Not only 添加与 Not rice 控制仍有效。06 只作明确未批准的条件聚合，无扩围或参数冻结；旧版保留及独立 oracle 未见新增缺口。待生成的运行结果不算实现缺失。

Spec：1 项 P2，最严重为否定预处理造成误待裁决。
