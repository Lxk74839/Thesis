# Spec 第八轮复审

基线 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；目标 `661fb5f129dfece2357ec10a04028a36c223e025`。仅静态固定 diff，未运行代码。

**P1：非稻米熟制对象仍会入选。** `identity_catalog.py:145,227–228`；`config/grain-A-1.1.4.json` 的 excluded_forms 仅有 cooked rice，其余加工门槛也不含通用 cooked。夹具 `title="Cooked barley kernels"`、其他字段空：barley＋kernels 提供身份／形态，missing_composition 被新版放行，最终 included/not_disclosed。Cooked oat groats 同样受影响。草案 `scope-rule-revision-draft-20261012.md:13` 明确“熟制即食……仍按 A 排除”；L19 要求 A 内形态一致。建议核查全部粮种的肯定熟制售卖形态，保留 uncooked、when cooked 与烹调建议控制；须公共 CLI 验证。

第七轮否定作用域已修复，同句 contains salt／but is malted，以及 Not rice／Not only 控制有效。旧版六摘要保留、独立 oracle 与单入口未见新增缺口。06仍只是未批准条件诊断，无扩围或参数冻结。未完成的全量运行不算代码缺失。

Spec：1 项 P1，最严重为明确 A 外熟制商品错误入选。
