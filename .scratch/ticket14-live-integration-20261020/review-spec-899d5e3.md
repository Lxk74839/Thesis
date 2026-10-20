# Spec 第二轮独立审查

审查代理：/root/live_a_spec。
区间：dcd7f1971a41af7dd1b29421e250596af06faffd...899d5e33c7a68665953efbd9983259f8921fe9dd。

对固定区间独立复审：首轮3项问题均已修复，**仍有1项范围内阻塞**。

- **[P2] 实际 A 与运行审计的 assessment／G／完整性证明仍未关联核验。** experiment_io.py:131 直接采用审计的 evidence_state，135行仅凭 cursor == len(C) 和 assessment 键齐全生成 complete_C；未与封存 A 的 assessments 核对，也未检查 advance_allowed／completion。64–68行对 A 只校验来源绑定和候选信息。对于非 Q 场景，既有评价器不会补做这种关联校验，因此摘要有效但 assessment 与实际 A 冲突的产物仍可进入评分，污染混淆矩阵；未闭合 assessment 也可能被表示为完整 C。违反 spec.md:12“核…实际A/G/assessment/components”及 draft.md:83“complete_C 需要实际 cursor 和完整 C 的闭合评估证明”。应补 PUBLIC 矛盾产物拒绝测试，并在转换层核封存 A、审计 assessment、G 和闭合证明的一致性；无需重跑取证或修改评价器核心。

已确认的修复：18–27、178–186行支持逐行引用和新增场景模板；103–130行按结算回执保留未知 usage 与已知小计；75–124行核 final／commit／seal 结算及请求／响应 trace。

未发现额外范围扩张；未把 B 列为缺失，未重开旧 T0/P3。仅静态读取固定候选及 PUBLIC 原件，未执行项目代码、测试、推荐、评价、统计或 API，未写文件。

本轮原生工具 wall_time_seconds 累计：**0.9430377 秒**。
