# Standards 独立静态审查

Base: `cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1`。Candidate: `ee5bb2783fdbf4c6ea8b50ebb2f077ed66f0bfb8`。

范围：固定三点差异；读取 AGENTS.md、docs/agents 三文档、批准合同、授权和 docs/data-sources/joint-tasks.md。未发现额外 CODING_STANDARDS/CONTRIBUTING。只读静态审查，未运行 Python、测试、生成或上游语义复核。

**硬阻塞：1。非阻塞建议：0。**

- **[P1] 暂存目录绕过路径守卫，reparse 拒绝范围也不完整。** 合同 §8（第162行）规定“所有来源/临时/最终/失败路径”检查全部祖先的 symlink/junction/reparse 与越界。`joint_tasks.py:266` 直接以 `ROOT/'.tmp'` 创建 TemporaryDirectory，未调用 `project_path`。真实配置和来源位于 config/data 时，不会间接检查 `.tmp`；若 `.tmp` 已是 junction/symlink，暂存组件会先写入其指向处，破坏项目内写入保证。另 `joint_tasks.py:50–55` 与 `verify_joint13.py:42–46` 只检测 symlink/junction，未覆盖其他 Windows `FILE_ATTRIBUTE_REPARSE_POINT`。最小修正：创建暂存目录前通过统一路径守卫，并在两个独立程序各自检查所有既存祖先的 reparse 属性；补充公共 CLI 拒绝反例，不修改上游。

其余已检查的工程边界未见硬违反：唯一准备入口只增加分派；新模块使用标准库；模型投影和私有来源分域；固定原件以引用保留；独立参考程序未导入生产计算；准备、独立关联和子范围接受状态分开。未据此声称实际包已接受或资源实测通过。

Fowler 基线逐项作为判断建议应用；未发现应单独阻塞或建议本轮重构的代码气味。独立验收复算没有作为重复代码要求合并。
