# Spec独立审查：cd4a2e7

固定BASE：`023a6cc5b906541f01b56cfd805594719bfac557`；候选：`cd4a2e7368c81a406df2fe9e6258736559382c8c`。比较：`git diff 023a6cc5b906541f01b56cfd805594719bfac557...cd4a2e7368c81a406df2fe9e6258736559382c8c`。

依据为已确认的`model-preconditions-confirmation-20261018.md`与独立授权`authorization-model-offline-20261018.md`。仅静态阅读固定差异、规格、公开测试与TDD记录；未运行Python/测试/API、未读取凭据或正式表现、未读取Standards报告、未修改实现或另行委派。

## 阻塞

1. **[P1] 全量目录仍可遗漏全部S/M请求并被导入为官方完整覆盖。** 规格第75—76行要求“每个开发根/方法/视图…列出每次完整W/P”“R没有模型请求，计数0”，第89行要求“少一条就只能报告部分覆盖”。`token_counting.py:48`只验证9600个根的声明笛卡尔积，`:55`只比较引用与同一输入中的自声明`expected`。提交完整根声明但`expected=[]`、无prepared行时，export仍产生`complete=true`；无日志/回执的import在`:305`由空集合的`all(...)`得到`official_complete=true`、`imported_official`，并把所有S/M根累计写为0。应拒绝未覆盖任何已声明S/M根的目录，并避免空回执真空通过官方覆盖门。

2. **[P1] 错误响应绕过计数一致性门，可能在输入漂移后继续重试。** 规格第67行：“发送后的usage与预计输入不一致…保留原件和占用并停止”。`model_adapter.py:221`只在成功normalize分支检查计数与预留；`:225`的错误分支直接接受可解析usage。举例：回执I=100，响应输出为畸形JSON或incomplete、usage.input_tokens=99且其余明细自洽，会得到已知usage的可重试format/truncated；`recommendation_runner.py:407`按99结算并释放差额，`:417`允许宿主重试。应对成功和错误原件统一执行I/O/费用一致性门；漂移保留原件且禁止重试与释放相关保护占用。

## 非阻塞

无。未发现其他需要扩展授权范围的要求。

本轴结论：**阻塞2，非阻塞0；最高严重性P1，需修复后定向复验及固定候选复审。** 不重审已接受批处理实现；不据此宣称供应商可达或真实容量通过。
