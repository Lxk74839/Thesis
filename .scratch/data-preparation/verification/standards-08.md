# Standards — 工单08冻结实现审查

范围：`git diff 90ecec3...480551b`；提交为`06cf2b6`及`480551b`。依据：AGENTS.md、docs/agents/issue-tracker.md、triage-labels.md、domain.md，以及已确认流程记录。未发现其他CODING_STANDARDS、CONTRIBUTING、GLOSSARY或ADR。静态审查；未修改生产、配置或测试，未读取测试组逐账号标签。

- **[P2，阻塞] 异常明细写入绕过项目路径检查。** `preference_tasks.py:478–480`仅检查`project_path(root)`，再拼接`data/preference-failures/<配置摘要>.jsonl`并交给`write_rows`。若`preference-failures`是目录联接，失败分支会追随联接写入目标；正常版本路径的祖先检查不会覆盖这个兄弟目录。由此可写出项目，或向上游目录写新文件。违反`AGENTS.md:5`“新文件和写入操作均在本项目内完成”及`:6`“新产物使用独立路径”。最小处理：对完整失败文件路径调用既有`project_path`，在创建任何目录或文件前拒绝联接，并通过CLI验证失败目录联接的真实拒绝及哨兵目标无新增文件。

- **[P3，非阻塞判断] possible Duplicated Code。** 固定请求文本在`preference_access.py:10`的`REQUEST = '根据较早正向评论和商品标题，对完整候选谷物商品按偏好排序。'`与`preference_tasks.py:262`的`'text': '根据较早正向评论和商品标题，对完整候选谷物商品按偏好排序。'`重复。以后单处修改会令构造器与验证器冲突；可直接复用已有常量，不需要新抽象。此项为smell启发式，非项目硬规则，不影响本次正确性。

其余变更保持唯一CLI入口、受限改动及独立模块；无为smell强行拆分大型领域验证流程的要求。TDD日志和回归记录明确使用Thesis环境。工单仍为claimed，符合尚待完整验收的状态。

结论：文档标准违反1项，最高P2；非阻塞smell建议1项。应将异常写入缺陷纳入首轮验收的集中修订集合。
