# A7接线及HTTP错误采集：离线通过，真实A7未开始

BASE3a087b2；受审候选1df9e597fe71a5903b4bf62506b543ec11ad7f64。Standards/Spec对同候选PASS；Standards仅记录复制测试名含旧数字P3，断言为历史12/共享24，不扩修。
HTTP_red因缺http_diagnostic复现；HTTP_green通过。HTTP408/非JSON/缺标识/凭据回显/本地timeout/连接异常/未知worker及错误仍停止四项PUBLIC夹具通过。A7 quota_red复现旧上限拒绝；新额度、1493非执行准入发送链、完整S fixture九轮或错误三轮、旧marker及worker回归共10项PASS。非真实响应回放，没有PUBLIC联网探针。
HTTP实际发送器新增UTC起止及单调耗时，原真实HTTP状态；本地timeout/connection/unknown_send分类。错误仅code/type/message白名单，512字符message或256字符非JSON短片段，诊断≤4KiB；读≤65537字节，截断/缺失/过滤明确说明。认证/实际Key/推理内容过滤，原生解析、画像和工具发布业务继承。
A7额度独立12/91612，共享24/189916，历史12/98304及207.3560245秒保留，余额1592.6439755，HTTP120/最终145秒及原根-20/Job-10/回收5保持。128MiB根、64MiB run真实守护保持。
启动门before_A7记录仅剩111.054秒，低于180秒收尾预留，抛出remaining_budget_requires_stop。在创建A7-ready、控制目录、claim及调用sender之前停止。真实A7未执行，不是执行失败；原许可未消费，本轮generation/count/other=0，实际Key读取0。
没有新增真实HTTP错误样本；旧A6只确认HTTP408，具体服务侧错误正文与原因仍未知，不能把合成upstream_timeout等字段当作真实原因。旧A1—A6及全部证据不改，S未通过，publication没有新增。
本包完成代码与离线验收，A7实际试跑仍待执行。继续需要一个明确的准备/归档离线工作段；不能重启本包、绕过收尾门或自动扩大额度。M/异常Q/正式100及A8均未启动。
