# 独立评价器离线子项

Status: ready-for-agent
BASE: 73914774e2fedd53071c7240c50b28b85be86194
Spec来源：draft.md、confirmation.md及原F1/F2已确认正文；最新人类确认优先。

## 公共Interface与数据合同

- score_task(task, execution, reference)是纯函数。task包含task_key/root_task_id/view_id/scene/method/repeat、完整有序C及相应batch映射、snapshot_id/request_profile_id。reference仅评价侧：同一绑定、完整C四态、唯一留出target、来源定位/摘要；不生成或调用生产gold。按source_ref与完整绑定核对，缺键/错配为pipeline_error。
- execution显式包含task_key、started和terminal；started=false且terminal=not_started/configuration_required是未执行；None/缺记录和未决意图为missing_record/unresolved，null且阻止完整结果。已开始的合法失败终态按F1计0。released/valid_empty需整表结构、共同门禁、publication一致性及G的记录。输出保留执行状态、NA原因和管线错误，不静默删任务。
- 必要臂独立算HR/NDCG_P/EG/SJ的K1/5/10、违规/满足率、覆盖/填充、四态含Unassessed的混淆统计（固定S与其他候选分开）。参考NA不影响偏好评价。整张L门控，重复/C外/超K或非法尾部不能被前缀掩盖。空列表违规项率NA；F空的合法空需完整C闭合证明。
- Q使用M的实际acquired(A_M)、G、cursor、终态及full/no_quality/mean_quality组件。组件冻结anchor字段和A摘要、G/C/base等绑定；原始q/m/z只取实际取得范围。评价侧无I/O地核验组件公式与排序、mean分母及full实际发布一致性，绝不从reference取q/m/z或补证；失败三组件共同0（参考NA仍NA）。不要求生产函数生成gold。
- summarize(plan, task_scores)是纯函数。plan包含source_scope、plan_id、users/scenes/tasks及评价侧预封存U8/UQ；输入任务唯一且全集外连接。原8固定各1/8，新8逐场景，Q各1/2。r=1。cohort由reference适用性与预封存掩码核对，不依结果成功。相关必需项缺失则对应用户/点估计/区间null，不缩cohort；全包未齐状态incomplete。
- C1=M-S、C2=M-R、C3=full-no_quality、C4=full-mean_quality。先用户内汇总，再配对均值。U8/UQ排序为UTF-8字节，随机Random(seed).randrange(n)顺序；各50,000整行重采样，两比较共享索引与索引摘要；seed=20261016/20261017，type7的.00625/.99375，近似同时95%，无主p值。n<2不造区间，退化标注；实际精度单列，不据此宣称充分。975仅historical说明。
- usage每个真实task只计一次（Q三组件不复制），包含失败与重试；保留单位/usage_basis，未知null+已知小计/未知数量。价格未绑定cost=null；不得将公开合成单位称官方token或报价。
- CLI只读取项目.tmp/experiment-evaluation中的PUBLIC手写夹具，引用须含path/bytes/sha256；不接真实计划/私有参考、不调用网络。输出task-scores.jsonl、user-pairs.jsonl、scene-summary.jsonl、summary.json；manifest含输入/源码摘要及fixture_only、真实/API运行0。独占新目录发布，拒绝越界/重解析路径和覆盖。失败退出2且不发布成功结果。

## 验收与资源

逐公共行为TDD，已满足行为如实记录，不制造RED。只新增及直接影响回归。固定candidate后同一BASE...candidate双轴并行审查，修复仅范围内阻塞并定向复验。原计划/上游/运行器只读，旧P3和T0不变。资源按confirmation.md执行，原账仅追加，历史前缀保护。scope标签eval100_；到限停止。最终只接受独立评价器离线子项。
