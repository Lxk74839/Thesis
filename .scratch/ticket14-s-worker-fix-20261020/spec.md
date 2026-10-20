# S worker 定向修复

继承4af304c/c9c64da及2d93692的R验收。公共测试接口沿用P1StorageGuard与既有send_response，验证真实Windows worker启动，不运行模型。固定无效PUBLIC端点和PUBLIC占位认证值，子进程在端点校验即退出，不读实际Key、不联网。

仅修正Windows实际Popen审计形状及该worker标准管道/空设备的必要接线；其他进程、socket、凭据、评价和写入保护不放开。原S授权、run_id及360秒执行许可未消耗，全部原限制延续。

本次用户重申本地180秒，但仍受继承offline1753.9884483/1800秒约束；新增包不覆盖或重置前包172.0115273秒支出。native10秒/16MiB为全部非测试/非代理操作及收尾的保守上界，不称实测。RED/GREEN后固定新candidate，仅两轴定向审查该差异，既有S/R测试证据复用。通过后执行一次S；额度或审查不满足则停止。
