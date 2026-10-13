# Spec 复审：规则修订第五轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；固定目标：`cdb2b955eaa24386dd8603512c90584df852afe9`。确认非空 three-dot diff，使用固定提交静态审查，未执行 Python／Conda；未将运行中的新产物或尚未完成的验收作为代码缺失。第四轮三项具体反例均已修正并有公共 CLI 正反例。1.1.0 被明确拒绝并保留配置、产物及六个摘要，新版本没有覆盖旧版。

1. **P1：非标题本品预处理事实未完整检查。** `identity_catalog.py:130–169,177–180,194–195`。夹具 `title="Pantry Essentials"`、`features=["Parboiled rice grain."]`：legacy 为 weak_identity，新循环取得 rice＋grain，但歧义仅检查 sold 标题，最终 included。`title="Raw barley grain"`＋`features=["Malted barley grain."]` 也绕过新标题 malt 规则。草案 `scope-rule-revision-draft-20261012.md:13,19,31–32` 要求已批准字段相互一致，并明确“parboiled……仍待裁决”。建议：对直接本品字段的预处理反证与最终身份一起复核，继续排除烹调建议的作用域。

2. **P1：身份后取得时，先出现的食用／形态反证失效。** `identity_catalog.py:134–145,166–185`。夹具 `title="Pantry Essentials"`、`features=["Bird seed and feed."]`、`description=["Raw pearl millet grain."]`，以及 features 改为 `Canned in water`、description 改为 `White corn kernels`：检查 features 时 crops 为空，反证门槛跳过；随后取得身份／形态，最终只有类别被补查，两个对象均可能 included。草案 L13：“存在未解决的关键……形态……或食用定位反证时仍待裁决”；L19 允许多个字段共同取证。建议：最终身份确定后核对全部已划分本品陈述，不能让字段顺序决定是否发现反证。

3. **P1：Not only 真实配料续句被当否定边界删除。** `identity_catalog.py:57–59,75–85,186–195`。夹具 `title="Raw rice kernels"`、`features=["Ingredients: Rice. Not only rice but salt."]`：leading not 结束 active 列表，余下 Rice 被称 declared_single_grain；字段循环没有相应混合动词，最终 included。草案 L20 要求完整保留连续配料，L30：“分界必须有来源语义依据，不能为解析成功随意截断。”建议：区分真正不含声明与 Not only...but...；无法可靠解释时待裁决，不将截取的子集当完整组成。

两份独立 oracle 和复用评论入口未见新增实质 Spec 缺口；无未请求的模块扩展、基于评论选品或研究阈值冻结。全源与新入选语义验收仍由主代理完成，不能用静态审查替代。

汇总：Spec 3 项 P1；最严重为已披露关键范围反证被遗漏后错误入选。以上均为固定提交的具体公共可验反例，待主代理执行 RED／GREEN 验证与修复。
