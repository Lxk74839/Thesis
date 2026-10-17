# 取证专项：公共Interface及实施候选验收映射

2026-10-17（Asia/Shanghai）。本记录为实现候选前的实际证据索引，尚不代表专项接受或独立审查通过。固定base为`ac49059ffa1f61545033b84f688eee4be58d75be`；授权先行提交`1c61360f9abf60c1ae29ddc5d4633a6f9ff1c433`。原[合同](../spec.md)和[确认表](../confirmation.md)字节未修改。

## 实际Interface

- E1位于`evidence_access.py`：`LocalEvidenceSource(snapshot_ref)`只接受宿主绑定的快照；`EvidenceSession(binding, source, limits=..., final_reserve=..., joint=...)`持有一份根账。模型侧只经dispatch调用list_evidence、read_evidence和委托原JointSession的candidate_page；tool_schemas只导出新增两个工具的封闭输入，旧投影tools=[]原样保留。
- 宿主侧audit_view返回与内部隔离的A、回执、来源映射、setup和用量副本；assess_current按1逻辑单位调用E2。advance_current只在显式评估允许后推进一个固定b队列位置并使旧ref/cursor失效，按1程序逻辑单位计；没有方法运行循环、K停止/发布、模型或账本功能。
- E2位于`evidence_verification.py`：assess_evidence仅读内存A；rank_acquired_quality只把同A转换给既有rank_quality，先在完整C保留raw q/mean分母，随后仅按宿主实际评估G筛顺序。预取的rank局部eligible不扩G。Q异常复杂scope明确拒绝。
- 原8源使用11实际`change-actions.jsonl`，正常Q使用12实际`actions.jsonl`，动作原文没有业务version字段，读取时使用登记版本1。未改写任一上游格式或文件。

## H01—H14与计量覆盖

测试均在新增`tests/test_evidence_access.py`、`tests/test_evidence_verification.py`，原有测试不修改。下表使用实际测试名称的可唯一辨认短语。

| 合同行为 | 实际公共测试/观察 |
| --- | --- |
| H01 正常完整支持 | complete_public_sample_report_and_retail；list_acquires_real_registrations；read_returns_exact_scoped_bytes |
| H02 缺件与外层损坏 | confirmed_missing_original；outer_component_damage；unavailable的原件查找来源与终局尝试分别保存 |
| H03 摘要错配与有效否定 | identical_fail_bytes_refute_only_when_registration_digest_matches |
| H04 冲突/绑定 | conflicting_lineages_need_a_sample_inside_the_inspection_event；missing_sample_or_wrong_object含缺sample、错批次、错项目三例 |
| H05 当前失效/历史无TTL | current_expiry_does_not_apply_a_ttl_to_historical_inspection，valid_to=τ |
| H06 合法新头/不回退 | legal_new_report_replaces_old_support；new_pass_or_unusable_new_head含v2/pass、摘要错及撤销头；illegal_revision_action另验收无权动作不被采用 |
| H07 撤销/未来可见性 | only_a_typed_authorized_effective_revocation含严格整数/布尔反例、τ后生效；snapshot_cutoff_excludes_future_version_and_action |
| H08 权限/身份/越界 | read_denial_is_enforced_before_any_original_request；material_kind_permission；refs_are_bound_to_root；闭合参数拒绝principal/root/snapshot/path覆盖 |
| H09 分页与未读反证 | thirty_three_records_close_only_on_the_bound_last_page；positive_first_page_cannot_hide_negative_last_page_or_unread_original |
| H10 进度与四态 | no_attempted_evidence_stays_unassessed；部分页Pending不可推进；终局缺件Pending可安全拒绝；host_cursor_cannot_advance_an_unassessed_candidate |
| H11 无关变化 | unread_unrelated_harvest_material_cannot_block_r1_or_r5；共同C/b沿只读JointSession保留 |
| H12 根账/缓存/失败 | six_roles_share_one_atomic_root_budget；metering_example；failed_adapter_request_and_host_retry；retry_cap；late_real_bytes；unknown_usage_keeps_reservation |
| H13 正常Q兼容 | q_conversion_uses_same_a_and_mean_includes_acquired_objects_outside_actual_g；q_missing_dispatch；q_conversion_refuses_nonempty_action_scope |
| H14 不读私有答案 | private_canary_changes_cannot_change_visible_trace_cost_or_assessment；固定时钟/RNG后私有gold/F/目标/计划canary变化不影响公开响应、A、成本和状态 |
| 来源/Interface补证 | receipt_items_resolve_every_returned_fact；tool_schema_exports_only_closed_list_and_read_inputs；scenario_change_action_component |
| 计量人工例 | 3登记+3初始依赖=6逻辑，批读2原件+1缺件=3逻辑/1物理，重读2缓存原件=2逻辑/0物理；初始依赖单列时人工例的主体6逻辑/2物理保持 |

实际完成30个RED→最小GREEN纵向周期。每个RED对应新增公共行为，失败与后续GREEN均按顺序保存在`data/evidence-forensics-audit/20261016/01-*`至`67-*`及同目录resource-ledger.jsonl；自然已覆盖的有效期、末页、对象/版本/Q边界仅补人工期望一致性核对，没有人为删代码制造RED。初期两次新测试插入位置错误已在对应GREEN前修正，未降低预期。

最终候选前`68-public-and-impact-regression.txt`实跑37项全部通过，含candidate_page与旧JointSession逐行相同、旧tools=[]不改，以及Q full/no_quality/mean_quality/α=1边界的人工常量。必要回归经这两个旧公共Interface穿过，不重跑上游生成型测试、295项旧全量接受、P0、SIM生成、基础评分或组包。

## 实际来源probe和独立核对

`probe_sources.py`只从07 assignment元数据与已有身份键重现08不透明根ID用于选择；没有读取目标、评价、gold、F、U8/UQ或参考文件。选开发根字节序首项，再选其既有b队列首候选；同根/同候选遍历原8及Q1/Q2的10个既有来源。安全投影/完整C/b只读复用。

首轮`57-source-probe-01`在首源列取时发现Adapter只识别Q动作文件名，保留失败及资源账；未完成来源为0，未交付方法事实A。公开`58-scenario-adapter-red`复现，`59-*`修正为按实际快照动作组件读取。后续失败会单独保存失败源audit_view，不覆盖原证据。

`60-source-probe-02`实际10/10通过。各源67逻辑/2物理：32候选分页、15登记、3初始依赖、15实际原件、1缓存重读、1程序核验；根候选数1，模型/API/重试0。每源actual-a.json保留原文、登记、事件、策略/快照、回执及来源定位。独立代码从实际文件按offset重读并核SHA-256、回执ID与逻辑/物理守恒，不调用生产内部辅助函数推导预期，不回灌额外事实。

该首候选在10个来源均观察到Supported；这不假定其属于原S，更不证明实际源的所有异常对象已全量复核。语义覆盖来自上表人工事实/期望。probe只给一个固定对象的实际适配接入证据；测试limits/reserve不是F3执行预算，不产生推荐运行、效果结果或T0结论。

截至上述候选前最后一次执行，全部项目Python累计60.306586秒；初始保护快照实际覆盖1,819文件/23,351,408,107字节。最终用量、保护后验及代码绑定由接受阶段另行给出，不用本历史数值冒充最终资源总账。

## 尚待完成

固定候选提交后按同一base/candidate由Standards和Spec两独立代理并行审查；阻塞集中处理、必要补测及定向复审。最终真实probe需绑定实际交付生产字节，最终保护核查/资源汇总与专项接受另写，不回改已接受上游。T0/P1、运行器、模型/计费、可执行预算、链及15门禁保持。
