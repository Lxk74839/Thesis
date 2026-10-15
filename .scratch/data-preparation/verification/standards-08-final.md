# Standards — 工单08最终独立复审

冻结提交`f3adc26ba9a08f7306f1bb990a2f8e66a1d89cc9`，范围仍为`git diff 90ecec3...f3adc26`；提交链为06cf2b6、480551b、aa72cdd、f3adc26。依据仍为AGENTS.md、docs/agents/issue-tracker.md、triage-labels.md、domain.md及已确认流程记录；同时复核完整smell基线。仅执行静态复审及读取现有证据，没有修改生产、配置、测试或上游。

**原P2真实关闭。** `preference_tasks.py:478`现在先对完整`Path(root)/data/preference-failures/<摘要>.jsonl`调用`project_path`，再于`:479–480`判断存在性和写入。`:65–77`同时检查解析后的项目边界及原路径各祖先的symlink/junction，覆盖原失败目录联接旁路；正常版本目录、主记录和依赖路径继续使用该检查。行为19的真实CLI证据从RED的联接目标新增1文件变为GREEN的0文件，并验证退出码2、`invalid_task`及无成功主记录（`tests/test_preference_tasks.py:486–502`；ticket08-19-red.txt／green.txt）。符合`AGENTS.md:5–6`项目内写入与独立产物规则。未发现新增硬性违反或其他真实阻塞。

**保留P3，非阻塞判断。** possible Duplicated Code仍位于`preference_access.py:10`及`preference_tasks.py:262`：相同固定请求文本分别定义及构造。未来可复用已有常量；此为smell建议，非硬规则。本轮遵循AGENTS.md最小改动和用户一次集中修订范围，不据此要求额外工程修订。

版本1.0.1的确认合同、profile与文本规则未扩展，复用原冻结密钥；首轮1.0.0拒绝记录及原产物保留。最终全项目回归日志记载197项通过、82.034秒。1.0.1真实全量独立验收、目标变更和新目录字节复现由相应报告另行裁定，本轴不提前宣布完成。

结论：Standards硬性违反0项、真实阻塞0项；非阻塞smell建议1项。原P2闭环成立。

交付附录：仅补审工作树新增`.scratch/data-preparation/diagnostics/verify_preference08_reuse.py`，SHA-256为`c5dc2c3ad4ca05b59882d2e55d0fe708659d604e295eff96426300d2c93b0f2b`；生产冻结点仍为f3adc26。脚本校验Thesis解释器，经真实公共CLI核对1.0.1复用回执及主记录字节，读取原1.0.0接受记录和组件摘要核对保留状态，比较两版密钥绑定，只将聚合结果写入项目内独立验收报告，不回显账号标签或密钥内容。未发现新增文档标准违反、真实阻塞或需处理的smell；本附录为静态补审，未重跑或改动该脚本。
