# Standards 第二十八轮

固定差异：`git diff fb5eff2d09bca20381529a5da5dac9c479a28acf...0b185d6526b376501b594fdd51d3b9e8b4a467cf`；对应`git log`确认30提交、355个变更文件。完整范围已核对，承接前轮逐块审查；本轮读取新增提交、最终两个语义边界、冲突重建及公共测试。

标准：用户8条工作准则、AGENTS.md、docs/agents/{issue-tracker,domain,triage-labels}.md、实际插件tdd／code-review及12项Fowler baseline；未发现额外CODING_STANDARDS／CONTRIBUTING或领域文档，不建占位。

## 当前硬违反

0。修改集中于已有否定列表及冲突重建流程；公共测试通过已批准CLI产物，以字面案例核对已知列表、未知项、后续肯定及一致声明。失败、首次修复失败与最终通过分别留存，旧回放另存preflight-11。未新增接口、依赖、正式视图或研究参数；原材料和历史版本保留。

## 新增启发

1项轻微possible Duplicated Code。`identity_catalog.py:38、76`新增相同的逗号／and／or分隔语法：

```python
continued_component = re.compile(r"\s*(?:,\s*(?:and|or)?|\band\b|\bor\b)\s*(?:" + pattern(components).pattern + ")", re.I)
component_list = component + r"(?:\s*(?:,\s*(?:and|or)?|\band\b|\bor\b)\s*" + component + ")*"
```

可仅复用分隔表达式，减少连接语法的同步维护。此为Fowler启发，非硬违反。根代理按工作准则3／4评估暂保留：两处分别用于分句反证与完整声明；后续语法变更须同步核对，两路径已有公共行为测试。处理判断另记，不将发现数改0。

## 历史处理

历史累计2项：context_role重复计算已修复；局部冲突更新的possible Duplicated Code评估保留，位于`identity_catalog.py:182–183、193–194、204–205、338–339`，包括最终汇总。沿用standards-scope-revision-disposition.md，不改写原发现数。

仅静态审查，未运行Python／Conda／测试。已读134项通过日志及41／86回放空失败记录，摘要ac06d61b…／2537534e…；不声称独立执行或1.1.12全源验收。

结论：硬违反0；新增轻微启发1（评估保留）；历史2（1修复、1保留），累计3项轻微启发。
