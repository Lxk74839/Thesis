# Standards 定向独立复审

Base: `cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1`。Candidate: `7de5d37220cb4a70bc2b6148a60698b4870917a6`。

静态范围：沿用初审标准来源，检查 `ee5bb2783fdbf4c6ea8b50ebb2f077ed66f0bfb8..7de5d37220cb4a70bc2b6148a60698b4870917a6` 集中修订、初审路径阻塞及修订影响。未重新全面审查上游，未运行 Python、测试、生成或模型调用；本轮仅新增此报告。

**剩余硬阻塞：0。非阻塞建议：0。初审路径阻塞已清零。**

- `joint_tasks.py:269` 在创建 TemporaryDirectory 前将 `.tmp` 通过 `project_path`，消除原暂存目录绕过。`joint_tasks.py:51–58` 和独立 `verify_joint13.py:43–50` 分别检查所有既存祖先的 `lstat().st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT`，并保留 symlink/junction 与根边界拒绝，满足合同 §8 的本次路径要求。
- 新增公共 CLI junction 反例经实际准备入口检查拒绝及无发布，`finally` 恢复测试暂存目录；未以测试导入生产内部实现。RED/GREEN 实际结果由主执行资源账及日志提供，本审查没有复跑。
- 其余修订限于独立参考的正常 v1 适用守卫、全根/视图 probe 证据闭合及对应公开夹具、定向测试和说明，未新增生产取证、模型运行或上游写入；独立验收继续不导入生产模块。未发现新的工程标准违反或需要本轮处理的 Fowler 判断建议。

该结论只表示固定候选的 Standards 阻塞清零，不代表真实联合包、样本充分性、执行预算或工单14/15已接受；Spec 由另一独立代理报告。
