# Standards 真实接入修订定向独立复审

Base: `cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1`。Candidate: `1f3f6bc852805b04fd4aba07878623b564428a0a`。

完整差异命令：`git diff cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1...1f3f6bc852805b04fd4aba07878623b564428a0a`；提交序列：`fb315b2`、`ee5bb27`、`7de5d37`、`2d54759`、`1f3f6bc`。本轮沿用前次两轴阻塞清零记录，仅定向复核 `2d54759cfe64111a0d4098532c2d3f0a603bb8d4..1f3f6bc852805b04fd4aba07878623b564428a0a` 的六文件差异及必要调用上下文。

标准来源：AGENTS.md、docs/agents/{issue-tracker,triage-labels,domain}.md、批准合同§8、§9、§11—12、实施授权及docs/data-sources/joint-tasks.md。未发现额外CODING_STANDARDS/CONTRIBUTING或现存领域文档。按仓库规则优先，核对技能全部十二项Fowler判断基线；未将启发式建议当硬违反，未重复工具已强制项。

**剩余硬阻塞：0。非阻塞建议：0。**

- `joint_tasks.py:243—251` 先核对精确快照，再从快照绑定的`policy.json`摘要经既有`checked/project_path`读取主体；Q另保留顶层主体一致性检查。没有放松已确认主体、路径或来源摘要要求，也没有修改既有11/Q材料，符合AGENTS“修改范围最小”和合同上游只读要求。
- 夹具改为真实11快照形状，新增测试经S1/S2公共CLI验证继承主体，没有导入生产内部实现。只读查看`tdd24-red.txt`的真实失败及`tdd24-green.txt`的31项通过日志；本代理未执行或复跑这些测试。
- 一次性定位器仍进入既有`prepare_data.py`公共CLI，仅增加异常行/缺字段名诊断；没有新增准备接口、生产取证或运行器。对应精确.gitattributes规则及TDD记录限于本次修订。

本轮仅新增此报告；未运行Python、测试、生成、模型或上游全量核查。结论仅为该固定候选的Standards定向复审，不表示真实联合包已接受、样本充分或工单14/15完成；Spec由另一独立代理报告。
