# Standards 第二十五轮

固定差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...b7490016b2e8e83b9ee152a5680594ad3a5a4869`；对应`git log`确认27提交、327个变更文件。完整范围已核对，承接此前逐块审查；本轮读取新增提交、最终判据、配置、公共测试及回放留痕。

标准：用户工作准则、AGENTS.md、docs/agents/{issue-tracker,domain,triage-labels}.md、实际插件tdd／code-review技能及12项Fowler baseline。未发现额外CODING_STANDARDS／CONTRIBUTING；缺失领域文档不补占位。

## 硬违反

0。`identity_catalog.py:24、262`在原用途／混合判据中加入mixed；`config/grain-A-1.1.12.json`的excluded_forms增加`powder`／`powdered`，均对应既有A边界的必要解释修正。`tests/test_prepare_data.py:251–278`通过已批准CLI产物和独立字面预期验证本品混合、声明冲突、食谱／条件、粉类和否定，没有新增内部测试接口。

修改符合工作准则3／4的简洁与最小范围；没有新增依赖、正式视图、SIM事实或未批准参数。旧通过回放另存preflight-08，历史失败、旧配置、原材料和审查保留。最终回放的生产器bd9e7dd0…、配置2537534e…与执行记录一致。

## 启发性判断

新增0。修订复用现有角色与配置机制，未添加无实际需求的抽象或重复解释路径。

历史轻微possible Duplicated Code仍涉及`identity_catalog.py:172–173、183–184、194–195、328–329`：

```python
decision.update(status="pending", reason="composition_declaration_conflict", composition_status="conflict",
                counter_evidence=[*decision["counter_evidence"], *composition])
```

依工作准则3／4及standards-scope-revision-disposition.md继续评估保留；维护范围包含三处售卖分支及最终汇总。另一历史context_role重复计算已修复，不改写原发现数。

仅静态审查，未运行Python／Conda／测试；读取131项通过日志及41／86回放空失败记录，不声称独立执行或1.1.12全源验收。只覆盖固定提交。

结论：硬违反0；新增启发0；历史累计2（1已修复、1评估保留）。
