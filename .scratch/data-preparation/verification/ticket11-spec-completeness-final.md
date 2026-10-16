# Spec补充复审

基线2e6594e；冻结候选f2e7d2e。D为获批ticket11审核稿，V为diagnostics/verify_sim11.py。

原五项在原复现场景解除：固定输出复用、基准事件/采样绑定、跨声明替代、schema/SHA/拒读类型、check汇总；H15缺动作读取完成性修复亦成立。未发现模型、统计或13接入越界。

- **P1阻塞：无效登记可授予外来撤销权。** V:500–516用接收登记声明的issuer确立谱系所有者，未核对原文。保留合法LAB回执，再加同id的RETAIL回执，RETAIL撤销使Supported误成Pending。违反D:99“非法/未授权动作不能撤掉合法原件”和108“其他签发者不得替SIM-LAB更正”。
- **P1阻塞：无效登记可跨对象补零售支持。** V:399–406将无效登记加入范围；613–618未重核当前对象/事件。V07追加改指PX3且registrar=UNTRUSTED的供体回执，Pending误成Supported。违反D:294“baseline_retail_event”及69“只影响实际依赖它的声明”。

两项经Thesis公共S2实证，见ticket11-registration-probes-initial.json。非阻塞：共享集合显式ID记录沿用；A17公开PX配对夹具待最终验收取证，无需实现13接口。合计新增2阻塞，最高P1；未完成全量门禁不冒作代码缺陷。
