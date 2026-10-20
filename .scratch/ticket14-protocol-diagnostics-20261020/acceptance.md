# 协议诊断及失败usage离线验收

代码candidate8962337cbd1da0ace57f27e06975d77c7e9c71e9，BASE3df1d06。仅provider_fourrouter.py与p1_engineering.py应用增量：本地ProtocolError提供固定stage/code、字段/结构索引、JSON字符position/line/column；覆盖响应状态、输出项/content类型、工具调用及ID复用、JSON、角色Schema、原生usage。未知项仍拒绝，strict Schema未关闭。JSON位置为字符偏移，不是Token计数。无通用校验框架。

invoke不再把这些已识别错误吞成engineering_response_error；transport及无法识别的内部校验分别标transport/unknown，不输出原异常。合法usage在协议、输出cap及超时失败路径独立保留，HTTP及发送计数照实记录。费用仍null，reasoning是output子量。缺失/null/解析拒绝分别保留，计量保持unknown/incomplete。超时与原协议诊断可以并存，禁止重试保持。

TDD详见tdd.md：诊断缺失、泛化吞错、已知usage100丢为null均已RED→GREEN。pdiag_008共10项（多个PUBLIC响应分支）通过，包括缺失usage、strict/无重试/输出cap/最终容量保留，原无usage PUBLIC S仍完整发布。所有手写响应明确PUBLIC fixture，绝非旧HTTP回放。未运行真实S、R、worker、回执全套或上游全套。

固定同一candidate独立Standards PASS、Spec PASS，无阻塞或P3。测试与审查均无网络/实际Key/独立标签读取；本轮generate/count/other=0，没有新许可或执行入口。

## 已确认与未知

已确认代码原因：旧normalizer抛出的普通异常缺少可归档stage/code；旧invoke合并捕获并重建error_result时没有传入已经合法解析的usage，因此丢失该路径的已知计数。新离线fixture证明两处均修复。

旧HTTP200、gpt-6-luna、原生解析255485输入/240输出（reasoning157包含在240中），由旧回执和审计两处一致核对。old-usage-supplement.json记录原路径、SHA及JSON pointer，派生input+output=255725，未额外加157。原始usage归档仍null、旧累计结算仍null、旧失败仍failed_model、无publication；没有伪造原始归档或修改旧记录。

旧响应completion status、output项类型、JSON文本及确切失败条件均unknown。reasoning157不能证明含reasoning输出项。新PUBLIC reasoning项拒绝示例仅是手写测试，不是对旧响应的判断。

## 待授权诊断

one-request-diagnostic-plan.md给出最多1次首请求方案：旧POST602539字节，新请求发送前按实际序列化字节/SHA核验且≤2MiB；完整1493输入、max_output_tokens8192、reasoning none、响应≤64KiB、HTTP30秒、无重试/回退/重定向，0count/other。仅保存必要状态/类型/字段存在/位置/ID/usage/边界元数据，无正文或异常原文。新授权独立，旧许可不复活。费用未知，须最终确认；本轮未执行或新增发送入口。

## 资源

继承offline2040.0128015，本包123.2295959/180秒，余56.7704041，30秒收尾满足；累计offline2163.2423974/2280秒。native20秒及16MiB是全部非测试非代理操作/归档收尾保守上界，不称实测。写入上界19,726,871/67,108,864字节，Job峰值及SHA核对见resource-closeout.json。

旧审计/预算/回执/claim/执行账、原offline账前缀和T0账保持原字节；历史时间/写入超限保留。此前S独立执行账28.1520212秒不动，本轮无新增执行；汇总历史计费2191.3944186秒。离线修复及本包资源验收通过，不构成真实S链路或Token/费用完整性验收。
