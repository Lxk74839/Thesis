# 工单08双轴代码审查汇总

固定起点90ecec3c9b7d2edb7a2c9f46aa8b8523dbb6a4c8，最终生产代码f3adc26ba9a08f7306f1bb990a2f8e66a1d89cc9。mattpocock-skills:code-review的两个并行独立子代理分别执行Standards／Spec，不混合重排。首轮480551b的Standards有1个P2阻塞及1个P3建议，Spec为0；P2经唯一集中修订及CLI行为19 RED→GREEN关闭。原版拒绝记录及首轮审查保留。交付附录仅增加已补审的独立复用脚本及报告。

## Standards

冻结提交`f3adc26ba9a08f7306f1bb990a2f8e66a1d89cc9`，范围仍为`git diff 90ecec3...f3adc26`；提交链为06cf2b6、480551b、aa72cdd、f3adc26。依据仍为AGENTS.md、docs/agents/issue-tracker.md、triage-labels.md、domain.md及已确认流程记录；同时复核完整smell基线。仅执行静态复审及读取现有证据，没有修改生产、配置、测试或上游。

**原P2真实关闭。** `preference_tasks.py:478`现在先对完整`Path(root)/data/preference-failures/<摘要>.jsonl`调用`project_path`，再于`:479–480`判断存在性和写入。`:65–77`同时检查解析后的项目边界及原路径各祖先的symlink/junction，覆盖原失败目录联接旁路；正常版本目录、主记录和依赖路径继续使用该检查。行为19的真实CLI证据从RED的联接目标新增1文件变为GREEN的0文件，并验证退出码2、`invalid_task`及无成功主记录（`tests/test_preference_tasks.py:486–502`；ticket08-19-red.txt／green.txt）。符合`AGENTS.md:5–6`项目内写入与独立产物规则。未发现新增硬性违反或其他真实阻塞。

**保留P3，非阻塞判断。** possible Duplicated Code仍位于`preference_access.py:10`及`preference_tasks.py:262`：相同固定请求文本分别定义及构造。未来可复用已有常量；此为smell建议，非硬规则。本轮遵循AGENTS.md最小改动和用户一次集中修订范围，不据此要求额外工程修订。

版本1.0.1的确认合同、profile与文本规则未扩展，复用原冻结密钥；首轮1.0.0拒绝记录及原产物保留。最终全项目回归日志记载197项通过、82.034秒。1.0.1真实全量独立验收、目标变更和新目录字节复现由相应报告另行裁定，本轴不提前宣布完成。

结论：Standards硬性违反0项、真实阻塞0项；非阻塞smell建议1项。原P2闭环成立。

交付附录：仅补审工作树新增`.scratch/data-preparation/diagnostics/verify_preference08_reuse.py`，SHA-256为`c5dc2c3ad4ca05b59882d2e55d0fe708659d604e295eff96426300d2c93b0f2b`；生产冻结点仍为f3adc26。脚本校验Thesis解释器，经真实公共CLI核对1.0.1复用回执及主记录字节，读取原1.0.0接受记录和组件摘要核对保留状态，比较两版密钥绑定，只将聚合结果写入项目内独立验收报告，不回显账号标签或密钥内容。未发现新增文档标准违反、真实阻塞或需处理的smell；本附录为静态补审，未重跑或改动该脚本。

## Spec

固定范围：`git diff 90ecec3...f3adc26`；提交依次为 `06cf2b6`、`480551b`、`aa72cdd`、`f3adc26`。依据正式规格、工单08、实施授权及冻结审核稿C1—C9／第6.2、8、9节。本报告仅复审，不实施第二轮工程修订。

## (a) 缺失或部分实现

未发现真实阻塞或P3。C1—C4要求的标题／粮种、完整合格较早正文和真实历史评分、全部原始已见及完整未见候选、全部评价账号背景排除由 `preference_tasks.py:209`—`:279`、`:427` 构造，历史标题仍关闭。私有目标与来源追溯分别见 `:280`—`:289`、`:254`—`:256`；有限处理仍为 `preference_text.py:65`—`:119`，无目标相似度过滤或截断。

## (b) 未经要求的范围扩展

未发现。第8.3节要求“变更或损坏不得原地覆盖”：保留被拒绝的1.0.0、另建1.0.1符合该约束。`config/preference-task-1.0.1.json:1` 沿用批准profile、文本、schema合同和原私有密钥；`preference_tasks.py:233` 的版本域使根ID变化，未重判06资格或重分07组别。唯一生产修订用于关闭已证实的失败路径旁路，没有额外模型、SIM或推荐方法。

## (c) 看似具备但行为错误

未发现剩余真实阻塞或P3。首轮Standards阻塞已在 `preference_tasks.py:478` 对完整失败文件路径应用 `project_path`；`:65`—`:77` 检查项目边界及各级junction／symlink，写入前拒绝。行为19从联接目标新增1文件的RED变为0文件的GREEN，最终全项目197项回归通过，证据见对应日志。

第7.2节要求的A通道仍由 `preference_access.py:68`—`:71` 真实构造请求并默认拒绝资源／工具，探测调用同一分派器；不把API能力隔离宣称为NTFS或供应商部署验收。第9节所需1.0.1真实全行／SQL／全文、目标变更及新目录字节复现由本轮独立验收报告裁定，复审不预判未完成结果。

结论：最终Spec发现0项，真实阻塞0项，P3为0项；无需第二轮工程修订。

交付附录：补审工作树新增的 `.scratch/data-preparation/diagnostics/verify_preference08_reuse.py`（SHA-256：`c5dc2c3ad4ca05b59882d2e55d0fe708659d604e295eff96426300d2c93b0f2b`），生产仍冻结于f3adc26。脚本通过同一CLI核对1.0.1回执及主记录字节一致复用，独立比对被拒绝1.0.0主记录／六组件摘要和两配置的同一密钥绑定；只输出汇总，不读取或披露密钥内容。运行结果 `ticket08-1.0.1-reuse-check.json` 通过，符合第8.3节不可覆盖与第9节重跑合同；未发现额外阻塞或P3。本补审不重复全diff，也未实施工程修订。

Standards：硬违反0、阻塞0、P3建议1（最高P3）；Spec：发现0、阻塞0。
