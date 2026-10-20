# S Windows worker 定向修复：代码通过，资源验收失败，真实S未开始

代码candidate c9275953b27e9505b0db859a98956a6b7ed1e1a9；继承4af304c及已通过R验收，不回退重做上游。

- RED：真实send_response→subprocess.Popen→既有worker不能启动（outcomes为空）。
- GREEN：只适配Windows的精确命令行字符串/默认executable，以及授权sender标准stderr所需的os.devnull。真实worker用固定无效PUBLIC端点在连接前返回，PUBLIC占位认证，未联网或读实际Key。
- 两项定向测试通过：真实worker启动，以及原凭据/评价/其他进程/socket拒绝边界。此前无usage PUBLIC完整S、严格拒绝及1493非执行预检复用，不重跑。
- 同一新candidate独立Standards PASS、Spec PASS，Windows阻塞解除；未扩展方法、供应商或数据许可。

**资源验收失败**：继承offline1753.9884483/1800秒；新包native10秒为非测试/非代理操作及收尾的保守上界。测试及Conda结算4.1167555秒；两轴审查开始至本地结算70.437秒（保守计费，包含根代理结算延迟，并非两代理各自纯工作时间）。新增84.5537555秒，offline1838.5422038/1800秒，超出38.5422038秒。未及时在审查后结算停止是本轮执行控制失败，超限不冲销，不改旧账，不借用360秒S执行许可。

真实S执行0次、生成/count/other API均0、实际Key读取0、评价标签读取0。终态not_started；实际核验/推荐数量、审计、publication、usage及费用均null，未生成实际推荐结果。工程链路尚未通过；Token/费用计量未完成。原失败证据、旧not_started记录和P1目录全部保留。

到限停止，不启动当前S。后续必须先明确原离线总额的追加授权；实际运行还应使用新的记录目录保留原not_started文件（旧入口会因result.json存在而停止），并绑定同一已审查脚本身份，不删除或覆盖旧记录。M及正式实验仍未授权。
