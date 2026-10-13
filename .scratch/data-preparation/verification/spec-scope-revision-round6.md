# Spec 复审：规则修订第六轮

固定基线：`fb5eff2d09bca20381529a5da5dac9c479a28acf`；固定目标：`59afdc084cb89623267a0e53d6d88d4bcc70d35a`。确认非空 three-dot diff，按实际 code-review 技能及完整规格静态复审固定提交；未运行 Python／Conda、未查看变化中的正式产物。第五轮三项具体机制已闭合，均有公共 CLI 回归记录：先收集身份，再核对全部本品字段；非标题预处理参与判定；Not only 配料续句保留。明确范围外形态不再被后续泛义描述覆盖，完整声明冲突仍保留待裁决。

1. **P2：否定的非粮成分／预处理仍被当作本品反证。** `identity_catalog.py:145–178`。夹具 `title="Raw rice kernels"`、`features=["Ingredients: Rice. No oil."]`：成分解析已正确结束于 No oil，得到 declared_single_grain；但字段核查的否定分支只处理紧接粮种别名的情况，随后 excluded_forms 命中 oil，最终 pending/field_form_conflict。同一标题＋`features=["Not parboiled."]` 则由 processing_claims 命中 parboiled，得到 field_processing_ambiguity。草案 `scope-rule-revision-draft-20261012.md:19` 允许一致正向身份／形态支持目录，L29 要求“否定声明……不能拼成商品身份或配料”。建议：记录否定语义与作用域，使明确不含／未经处理的对象不成为肯定反证；真正 Parboiled 和 This product is not rice 仍须阻断。两个具体反例须由主代理通过公共入口验证，不代表本审查执行了测试。

未发现其他新增实质 Spec 缺口。单一 prepare_data.py 公共入口、逐源旧新迁移与摘要、独立 oracle、零评论及低评分／空文本原值保留的实现约定继续有效。1.1.0、1.1.1 的拒绝记录与各六个摘要保留，没有用来源对账替代语义验收；1.1.2 的提交内 41 案例记录为 9 入选／25 排除／7 待决，不能据此宣称新总体全部人工裁决正确。

`diagnose_ticket06_options.py` 仅输出 hypothetical_options_not_approved 汇总；3／4／5、历史 0／1／2／3／5 与 2023 年起点截断均用于条件比较，保留严格早于目标、全部早期记录决定已见关系。没有生成正式清洗视图、分组、模型输入或私有标签，未冻结研究参数或宣称样本充分；属于用户要求的建议及数量影响准备，无 scope creep。

汇总：Spec 1 项 P2，最严重为否定声明造成错误待裁决；全量验收与新版评论运行仍由主代理完成，不把尚未执行的结果当代码缺失。
