# Spec 首轮独立审查

BASE: dcd7f1971a41af7dd1b29421e250596af06faffd
candidate: fc70fae675b004ce0e6cc1062a47ec38fbbfac1f
以下为 /root/live_a_spec 报告，原意保留：

固定 refs 已解析，精确三点 diff 非空；仅审查指定 candidate，发现 **3 项范围内阻塞问题**：

1. **[P2] 新增八场景的评价视图无法按既定来源结构装配。**
   experiment_io.py:135 强制读取 existing_binding_ref，而新增场景合法使用 request_template_ref（冻结脚本也如此写入）；因此完整18场景视图会抛 KeyError。此外 _read 忽略逐行引用的 offset，会把共享 JSONL 当单个 JSON。违反 spec.md:13–14 的“新增8接工单11独立参考”“18场景50槽”，以及 draft.md:94–97。现有 PUBLIC 测试为每场景单造文件和 existing_binding_ref，掩盖了该缺口。

2. **[P2] 计数漂移造成的未知 usage 被转换回确定数字。**
   experiment_io.py:83 直接累加 response_summary.usage。合法 usage_mismatch 路径保留原响应数字，但运行器已在 recommendation_runner.py:490–492 将结算 usage 置 null、保留未知占用；转换忽略这项状态，随后报告确定 token／费用。违反 spec.md:14“未知usage null”和 draft.md:86“未知保持 null 和已知小计”。应按实际尝试／结算回执关联处理，补 PUBLIC 漂移拒绝测试。

3. **[P2] 缺少必需 trace 或闭合结算仍可能获准评分。**
   experiment_io.py:65 只检查 journal 的 final 成功记录，未核同次 commit、seal_audit 结算，也完全未读取审计／journal 的 request_ref、response_ref。因此删除实际响应 trace 后，其余文件未变仍可完成转换。违反 spec.md:12“核…budget/trace”和 draft.md:84“核同一次宿主 final/commit/封存结果”、86“原件由引用定位”。

未发现需另报的范围扩张；未将 B 缺失列为问题，未重开旧 P3。未运行项目代码、测试、推荐、评价或统计，未写文件。

原生工具返回 wall_time_seconds 累计：**2.5540851 秒**。
