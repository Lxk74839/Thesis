# 工单13 TDD与验收映射

固定起点cfec0e5，授权归档提交fb315b2。确认的S1/S2及A01—A12保持；本文件记录实现行为，不把代码测试视为真实联合包接受。真实门禁尚待审查后执行，完成结果另行归档。

| A项 | 公共行为及对应证据 |
| --- | --- |
| A01 | complete_raw_comments...、independent_audit_rejects_resealed_false_raw_comment_count；完整原料引用、行数对账与私有用途。后续真实源图核查/保护 |
| A02 | one_shared_root...、all_views_share_root...、future_history...；全C/一批次/共同H/b/视图绑定。后续全根核对 |
| A03 | base_scores...、constant_content_and_single_candidate...；人工b=(1,0)/同分=.5及S2独立公式复算 |
| A04 | actual_model_request...、candidate_paging_uses_returned_cursor...；32+3实际页遍历35候选，后续真实全C文件与全根首分页核对 |
| A05 | private_target_mutation...；改变合法私有目标三元组/来源，全部模型组件、b与实际请求字节不变，私有配置摘要确实变化 |
| A06 | resource_and_cross_session...、malformed_page_order...、independent_audit_rejects_private_field_inside_resealed_request；真实分派默认拒绝及嵌套请求闭包 |
| A07 | q_reference_citation_must_resolve...、resealed_q_answers...；独立接受来源与原件/登记/事件精确定位；既有四态语义直接引用11接受，合成参考涵盖四态 |
| A08 | q_cohort_is_new...；公开测试pool3、旧n8=2、新nQ=3、HHI=5/9，开发另列 |
| A09 | missing_q_reference_key...；漏键失败而非NA；reference-index保留四态/eligible及全根，不按方法成功裁人。合法空发布属于后续运行器，不冒称本轮已验证 |
| A10 | new_q_coverage_preserves_legacy_exposure...、各S2篡改反例；完整0格/分母/旧暴露unknown及新覆盖，旧P0只引用 |
| A11 | missing_joint_inputs...、config_cannot_authorize_execution...、output_root_cannot_write_inside...；配置/路径/时间/未知运行预算门禁 |
| A12 | identical_reuse...、prepared_record_binds_actual_runtime...；一致复用/损坏拒绝、实际运行时/提交。后续真实新空根字节、mtime及上游保护 |

20个逐行为RED→GREEN循环：01参数、02贯通、03评分、04严格历史、05共同视图、06实际投影/分页、07配置执行拒绝、08复用、09独立偏好、10新Q、11参考接受来源、12全部评论、13候选截断、14旧暴露、15引用定位、16只读输入路径、17实际运行时、18非法页参数、19嵌套私有请求、20来源图虚假计数。

每个RED实际失败，随后只实现对应行为，保留原日志。第15轮首个GREEN尝试因公开policy元数据漏records而失败；修正夹具字节/行数合同后GREEN，通过前不记完成。没有隐藏失败或将其排除出资源账。

最终新增26项测试：20个有RED/GREEN的行为，6个现有行为的定向特征/影响检查；最后一次26项全部通过。原295项、旧P0、SIM生成及上游全量语义未重跑。既有四阶段只做缺参数分派回归，没有重新构造上游组件。

实际日志和资源原账在data/joint-audit/joint-task-package-0.1.0/tdd*.txt及resource-ledger.jsonl，均不入Git。日志包含测试名、原失败与后续通过；原资源账记录命令执行退出与进程树计时/Windows Job峰值。最后特征检查日志为behavior-characterization-and-impact.txt。正式接受将绑定这些日志的冻结清单，不把subTest、文件行、场景或引用当独立用户。

Standards与Spec待固定实现候选提交后由两个独立代理并行审查，两个轴分别结论。文档和源数据接受范围继续区分，整体样本充分性not_determined。
