# 工单13 Spec 初次独立审查

Base: `cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1`

Candidate: `ee5bb2783fdbf4c6ea8b50ebb2f077ed66f0bfb8`

固定比较：`git diff cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1...ee5bb2783fdbf4c6ea8b50ebb2f077ed66f0bfb8`。只读静态审查；未运行Python、测试、生成或上游语义复核。

阻塞：2；非阻塞：0。

1. **[P2，阻塞] Q的normal-v1范围守卫不完整。** 合同§6.2要求“只在完全匹配已接受的正常v1 Q合同时”映射Supported；“不匹配、缺来源、出现旧参考不支持的异常/版本/权限范围必须报reference_scope_mismatch”，对应A09。`.scratch/data-preparation/diagnostics/verify_joint13.py:390–410`检查eligible、五类引文及对象摘要后直接写Supported，没有检查引用原件version。公开夹具任一引用原件改为version=2，并同步重封原件/登记/参考/既有形状接受绑定，仍满足全部现有判断。这不是要求重推旧四态；最低修复是显式限制获准normal-v1范围，给版本越界公开反例，拒绝后再关联。

2. **[P2，阻塞] S2可将没有实际隔离探测的包标为通过。** 合同§8.1规定“probe可选但接受必须有探测证据”；§9要求真实全根模型投影与隔离核查。`verify_joint13.py:239–287`仅累计请求/拒绝次数，没有要求覆盖；空`private/access-probe.jsonl`循环零次也成功返回。正常S1允许省略probe，因此无须修改生产组件即可得到这种包，S2随后仍写passed check（521–529）。`deliver_joint13.py:161–162`也只看passed状态。最低修复是S2或接受门明确验证所需全根/视图请求、授权分页及越权拒绝证据集合；缺失应失败，不能只报告0次。

其他已查范围：根/C/H/b共享、模型投影与私有引用分域、独立参考来源关联、新Q与旧P0分离、prepared不回写及子范围状态均有对应实现；未发现真实工具、模型、T0/P1或统计实验越界。真实生成及后置验收尚未执行，不将其未执行本身列为缺失。
