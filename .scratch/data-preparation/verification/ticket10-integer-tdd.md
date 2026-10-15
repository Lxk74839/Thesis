# 工单10整数合同定向修复证据

本次授权从2b44220继续，保持原I1—I6与sim-normal-1.0.0配置，未改生产生成器、协议或上游。独立程序仍仅使用标准库，不导入生产校验函数。

七个外部行为依次RED→最小GREEN，S1生成可信小目录夹具，S2经真实子进程读取。每次重算相应原件/登记摘要、组件文件摘要及snapshot_id；不以摘要损坏代替类型拒绝，不使用生产内部函数产生期望。原始输出为ticket10-integer-NN-red/green.txt；命令、时间、环境及源码摘要保存在ticket10-integer-tdd-history.jsonl。

| 循环 | 外部行为与真实RED | GREEN |
| --- | --- | --- |
| 19 | 主记录和快照policy.records=true被S2错误passed | 主记录组件records先严格整数检查，拒绝为integer_type |
| 20 | 仅快照组件records=true/1.0等，仍被相等比较或其他原因处理 | 快照组件records在比较前严格检查类型和范围 |
| 21 | 输入/主记录组件/快照组件bytes可接受同值浮点或先落入绑定比较 | bytes先严格检查类型与0..2^53−1 |
| 22 | counts同值浮点被接受或坏类型先作数量相等比较 | counts逐值先严格整数检查 |
| 23 | 截止序号、快照及主记录核验时间缺少一致的前置类型检查 | 所有对应字段先严格检查，再比较数量/时间 |
| 24 | 绑定配置的目录数量、数量事实和时钟可按同值浮点参与推导 | 配置及目录计数先严格检查 |
| 25 | 业务原件/登记中的版本、序号、时间及材料事实先进入其他检查 | 解析后立即检查既定整数，再做排序/关联/时间比较 |

代表性反例包含bool、同值float、负数、2^53、字符串及null。原件反例保持原件—登记—快照摘要一致；所有反例只存在项目.tmp。合法输入另行GREEN验证：batch_created_at_ms=0、retail_valid_to_ms=2^53−1的受信任小夹具被接受，may_create_batch八个真实JSON布尔值仍为[true,false,…]，R1正常两批均Supported；未伪造该既有合法行为的RED。

整数核对清单（类型均为type(value) is int，范围均为0..2^53−1）：

- 主记录：inputs各bytes；六components各bytes/records；counts五项；sim_verify_at_ms。
- 快照：cutoff_sequence、sealed_at_ms、verify_at_ms；五个components各bytes/records。
- 绑定配置：catalog_binding.expected_parent_count、facts.quantity_units、clock各值、events及materials各日程值；目录来源counts.included。
- 批次/事件/材料/登记：version；所有既定顶层毫秒字段；sequence。材料facts中的既定毫秒及quantity_units/stock_units；储存各分段start_ms/end_ms。
- 参考中的选定版本、登记总数、审核计数均从已验证整数或实际长度产生，不接收外部答案。

只在已有integer检查函数处增加明确的局部调用/循环；没有通用schema框架或全局禁用布尔值。policy.may_create_batch的bool检查保留。既有协议、profile、数值语义、公共接口和历史失败证据不改。

证据脚本只将新保护/复现报告按实际Git候选命名，防止覆盖旧final文件，并同时检查982份本次起始保护文件。此前919清单和所有历史失败报告继续核对；受信任证据脚本仍通过唯一prepare_data.py生成，没有新增数据准备入口。
