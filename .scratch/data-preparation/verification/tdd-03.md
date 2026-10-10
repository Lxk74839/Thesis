# 工单 03 TDD 记录

实际使用 mattpocock-skills 1.3.1 的 engineering/tdd/SKILL.md、tests.md 与 mocking.md。唯一公共测试接口继续是 prepare_data.py CLI；测试通过 subprocess 使用父测试进程的 Thesis 解释器，没有新增公开 Python API、第三方依赖或内部函数 mock。

全部测试命令：`D:\Work\Anaconda\Library\bin\conda.bat run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis python -m unittest discover -s tests -v`。TMP/TEMP 均设为项目 .tmp。原有 11 项行为测试作为回归保护；下面每项先新增单个行为测试、实际观察红灯，再写最小实现并跑到绿灯，没有先批量编写测试或生产逻辑。

| 顺序 | 公共接口行为 | 实际红灯 | 绿灯实现与结果 |
| --- | --- | --- | --- |
| 1 | 完整评论包含末条，原压缩字节、文本、评分保留 | reviews 阶段尚不被 CLI 接受 | 在同一入口允许 reviews，复用完整获取与扫描；12 项通过 |
| 2 | 只用 parent_asin 关联，重复父商品评论仍是不同原始行 | association 结果缺失 | 读取完整元数据父商品集合，统计匹配／未匹配，绝不回退 asin；13 项通过 |
| 3 | epoch 毫秒保留子秒精度并映射 UTC | time 核查结果缺失 | 使用 UTC epoch 与整数毫秒偏移，固定例子 1609459200123 对应 2021-01-01T00:00:00.123+00:00；14 项通过 |
| 4 | 缺失、null、错误类型、超大时间与字段异常分开诊断且继续后续行 | 超大整数时间使入口抛 OverflowError，stdout 无机器报告 | 行内记录 missing／null／not_integer／unrepresentable，不删除原始行；末条仍纳入统计；15 项通过 |
| 5 | 关联不能使用摘要已改变的元数据 | 改变元数据字节后仍继续关联，得到 needs_review | 读取前重新计算并核对完整元数据 SHA-256；改变后明确 source_incomplete，扫描行数为 0；16 项通过 |
| 6 | 不推测未明确或不支持的时间单位 | null／seconds 配置仍按毫秒解释 | 仅接受来源事实明确为 milliseconds 的配置；17 项通过 |
| 7 | 超大整数评分诊断不能中断全量扫描 | 10**400 经浮点有限性检查抛 OverflowError，stdout 无报告 | 直接检查数值类型及官方评分域 [1,5]，避免不必要浮点转换；18 项通过 |

最终结果：[实际测试输出](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket03-tests.txt)记录 18 项全部通过。评分域检查仅标记来源事实异常；本次真实文件中的 0.0 评分仍保留，不据此清洗、填补、归一化或筛选商品。
