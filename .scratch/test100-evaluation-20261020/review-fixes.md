# 首轮阻塞修复

BASE=7391477；首轮candidate=1ac5185d19a67d1c27dce7c1084fed85f4339c7f。

| 首轮Spec项 | 必要修复 | 实际验证 |
| --- | --- | --- |
| P1 kindless batch/event | 接受已有实际取得对象形状；最终复用已有纯质量重排处理完整注册对象 | 052 RED，053 GREEN，055/056通过 |
| P1 组件伪造z缩分母 | 实际A及冻结fusion纯重排得到z/m/q，组件因素逐项比较；不从reference补证，不生成gold | 054 RED，055 GREEN，056通过 |
| P2 未决执行用量丢失 | 已开始执行先复制usage，评分null与资源留存分开 | 048 RED，049 GREEN，056通过 |
| P2 矛盾合法空获偏好分 | 发布一致性与结构同时决定偏好信用；非法发布执行态failed，联合仍按NA规则 | 050 RED，051 GREEN，056通过 |

源码只修改experiment_evaluation.py及其新增测试。原运行器/纯质量接口、上游与冻结清单均未改；run_check自首轮候选后未改。未修Standards可选P3。新候选须固定后，对同一BASE...candidate独立双轴复审。
