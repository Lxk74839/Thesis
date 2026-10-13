# Spec 第十轮复审

基线 `fb5eff2d09bca20381529a5da5dac9c479a28acf`；目标 `f8727b62cb92be81f965aa0a1dfcf96674d28788`。完整静态复审，未运行代码。以下均待公共 CLI 验证。

1. **P1：明确含盐陈述被当未披露。** `identity_catalog.py:72–106,186,236–237`：`title="Raw rice kernels"`、`features=["Not only rice but salt."]`，缺 Ingredients 前缀则 not_disclosed；混合检查也未识别 Not only，最终 included。草案 `scope-rule-revision-draft-20261012.md:13,20,30` 要求记录实际添加／连续组成，不能把已有成分陈述当缺失。应区分实际组成、部分声明与用途／营销，保留反证。

2. **P1：否定内容重新提供正向身份。** 同文件 `191–208,236–237`：仅 `title="No whole grain rice"`，首次肯定收集为空；第二轮否定检查只跳过可选 raw，whole 阻断粮种匹配，随后却加入 rice＋whole grain，weak_identity 变 included。草案 L13 要求正向身份／形态依据；L29：“否定声明……不能拼成商品身份或配料。”正向证据必须来自肯定作用域。

上轮标题独立陈述及引用重复已闭合。A边界、未知非验证、评论父商品／零低评空文本、迁移／旧版及独立 oracle 未见其他新增缺口；06未批准条件分析无扩围或参数冻结。未执行全量结果不算缺失。

Spec：2 项 P1，最严重均为无合格证据或有添加反证仍入选。
