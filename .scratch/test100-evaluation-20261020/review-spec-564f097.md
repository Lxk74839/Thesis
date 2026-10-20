# Spec 独立复审

BASE: 73914774e2fedd53071c7240c50b28b85be86194
Candidate: 564f097faa554ba06337996a772d9aae8de68b08
Reviewer: /root/evaluation_spec
日期：2026-10-20。同一 BASE...candidate；另查看首轮候选至本候选的修复差异。

结论：0 项剩余发现；首轮 4 项阻塞全部关闭。

- batch/event 兼容：experiment_evaluation.py:162 使用已接受纯评分组件区分实际对象形状；公开手写原件包含没有 kind 的 batch/event。
- z 与 mean 分母：163–182 从实际 A 推导因素和支持集合，对照各组件并核均值与分母；148–160 核冻结 fusion 及 anchor 摘要。
- 未决 usage：84 在保留未决状态与 null 指标前复制 usage。
- valid_empty 矛盾：104 对偏好信用要求有效发布，矛盾发布记执行失败。

没有新发现的实质正确性或范围问题。纯组件核验只接收 fusion 与实际 A；独立参考适用性、目标评分及 F2 汇总仍独立。期望为手写字面量，没有生产输出生成 gold。

隔离：未读取 Standards 报告；未运行测试、Python、API或真实数据正文；无写入。
资源：2 次只读 PowerShell/Git 调用，工具累计 wall time 0.354700 秒，原资源账追加，不退款。
