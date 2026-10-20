# Spec 独立审查（首轮）

BASE：73914774e2fedd53071c7240c50b28b85be86194。
candidate：1ac5185d19a67d1c27dce7c1084fed85f4339c7f。
审查者：独立代理/root/evaluation_spec；未读取Standards报告。

## 原报告

Spec轴：4项阻塞，最高P1；无范围扩张。

1. P1：experiment_evaluation.py:159–160解析每个取得原件后访问kind，但实际原件含没有kind的batch/event对象。正常Q取证会变成pipeline_error。依据：Q使用M的实际acquired(A_M)。需区分对象类型并覆盖公开实际取证形状。
2. P1：第156–177行由组件提供z；z=0只检查q/m=0，没有对实际取得的支持核对。把公开例c的z/q/m改0并把mean元数据改成.7/3能通过，虽A中仍有四项支持。依据：mean分母必须为同A内完整C中的支持对象，组件公式必须核验。应从实际A推导/核对z。
3. P2：第84–88行running/unresolved_attempt在复制usage前返回，丢失已开始执行的已知调用、重试和用量。依据：usage包含失败/重试、已知小计和未知数量。用量留存应独立于指标是否完成。
4. P2：第97–109行valid_empty且delivered=['b']虽发布有效性失败，仍给HR/NDCG_P=1，status=scored。依据：released/valid_empty需整表与发布一致性，非法输出偏好得0。应先核对发布一致性再给偏好分。

## 资源与处置

审查者报告9次只读PowerShell/Git命令（含1次解析失败），累计1.581492秒；无Python/测试/API、私有数据读取或写入。保留本报告；仅修这4个范围内阻塞，各配公开反例RED→GREEN及固定新candidate定向双轴复审。
