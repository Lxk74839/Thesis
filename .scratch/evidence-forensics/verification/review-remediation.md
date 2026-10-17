# 首轮双轴审查阻塞处理

固定基线为`ac49059ffa1f61545033b84f688eee4be58d75be`，首轮候选为`6bbcb800b319ee813f1a94284212f8dfb3d84ca9`。原始[Standards](standards-initial.md)与[Spec](spec-initial.md)独立报告保留。收到两轴后集中处理以下阻塞；本记录不替代定向复审或专项接受。

| 轴/原项 | 最小修复与公共观察 | 实际RED→GREEN资源账标签 |
| --- | --- | --- |
| Standards P1：中断漏账 | 子进程启动前独占创建并fsync未结算资源占用；完成行fsync后才清除。遗留占用拒绝新工作。受控嵌套守护被强杀后，第二次不得启动子进程，原占用保留；嵌套实验整个树由外层实际守护计量，不把未知占用从正式账抹掉 | `69-guard-interruption-red`→`70-guard-interruption-green` |
| Spec 1：来源绑定 | E1实际读取固定snapshot/policy后先校验snapshot/τ/principal/策略关系，再扫描候选事实。三种错误绑定均停止，A仍无候选事实，后续请求无I/O | `71-source-binding-red`→`72-source-binding-green` |
| Spec 2：重发绕过重试 | 失败的范围/ref保留续接request；公开dispatch重复、换序或拆批重发仍占共同两次重试，引用retry_of并退避1/2秒；宿主retry复用相同根账 | `73-dispatch-retry-red`→`74-dispatch-retry-green` |
| Spec 3：时间未预留 | 入场保留45秒最坏操作时间，另加1/2秒退避；不足时0逻辑/0物理拒绝，回执单列时间held/settled/released及deadline。迟到保留事实并停根，不继续占用最终预留开展新工作 | `75-time-reservation-red`→`76-time-reservation-green` |
| Spec 4：空终页永久未评估 | 实际空登记范围在A保留带来源/回执的枚举观察并计1逻辑；显式核验为Pending、必需原文未取得、尝试终局、可安全拒绝；未取证仍Unassessed | `77-empty-range-red`→`78-empty-range-green` |
| Spec 5：未执行批项计费 | `[ok,io_error,not_attempted]`只结算2逻辑/1物理，释放未执行的1逻辑，逐项失败/未执行观察保留，不冒充原件 | `79-unexecuted-batch-red`→`80-unexecuted-batch-green` |

`81-review-fix-public-and-impact-regression`首次全回归发现真实sleep有微小调度开销，已入场的退避被错误要求仍剩整45秒而过早拒绝。修正为在已预留的总deadline内执行，deadline到达即停止；没有扩大时间额度。`82-review-fix-regression-green`实跑42项全部通过，资源账累计68.856333秒。新生产行为均先用E1/E2公共反例RED，守护诊断通过实际命令边界复现；没有对生产私有辅助函数写测试。

Standards唯一非阻塞项是重复scope-seed构造，按授权只记录，未提炼新抽象。仍只新增/修改本专项白名单，无上游修改。最终10来源probe将另存执行候选号及生产文件/探针脚本精确摘要；此前probe-01失败及probe-02成功原证据均保留，不冒充最终候选实测。
