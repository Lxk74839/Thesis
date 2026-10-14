# 工单07公共CLI逐行为TDD

授权：[接口及实施确认](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-implementation-authorization-20261014.md)。固定边界为子进程调用prepare_data.py，验证退出码、JSON状态及文件；没有导入生产分组模块、内部函数或修改旧测试断言。

全部使用 `conda run -p C:/Users/Kane/Documents/CodexProject/Thesis/.conda/envs/Thesis --no-capture-output python -m unittest discover -s tests -p test_user_split.py -v`。每行的RED日志先于相应生产实现，GREEN后才编写下一行为；未横向一次写完所有测试。

| 顺序 | 公共行为 | RED／GREEN日志前缀 |
| --- | --- | --- |
| 01 | 新stage必须显式指定来源及配置 | ticket07-01 |
| 02 | 固定微型账号、已知哈希向量、旧账号优先及floor名额 | ticket07-02 |
| 03 | 非批准算法、盐、政策、取整及不安全版本拒绝 | ticket07-03 |
| 04 | 来源和全部六类06组件字节摘要绑定 | ticket07-04 |
| 05 | 接受状态、组件、勘误与资格快照交叉绑定 | ticket07-05 |
| 06 | 非法／重复来源身份不得被静默覆盖或丢弃 | ticket07-06 |
| 07 | 暴露事实校验、已知结果风险及unknown保留 | ticket07-07 |
| 08 | 强制开发超过名额时阻断 | ticket07-08 |
| 09 | 同账号引用继承、引用不增加账号、非法引用阻断 | ticket07-09 |
| 10 | 原样复用、输入变化及数据损坏不得覆盖 | ticket07-10 |
| 11 | 初始输入和输出位置限定项目范围 | ticket07-11 |
| 12 | 资格与商品关系异常失败且不打印私有标签／身份 | ticket07-12 |
| 13 | 嵌套元数据结构异常返回机器可读失败 | ticket07-13 |
| 14 | 不完整版本及暂存记录保留，不擅自覆盖 | ticket07-14 |

日志均位于本目录，后缀为 `-red.txt`、`-green.txt`。10的第一次GREEN因内存Counter整数键与读取JSON字符串键的比较差异未通过，原日志保留为 `ticket07-10-green-attempt1.txt`，修正JSON比较后GREEN。11首次RED中新增测试位置误把旧用例后半段带入，保留 `ticket07-11-red-test-placement.txt`；恢复原用例边界后重新记录真实RED，再实现路径检查。未删除失败日志或降低断言。

14轮结束后当前14个新增测试通过。每次同时运行此前已完成的新行为，红绿日志包含当时的完整结果。既有164项回归、真实1,603账号独立核查、行序挑战、新目录复现及双轴审查另行记录；本文件不预称这些门禁通过。

微型账号的哈希排序作为事先固定的演算结果：002、005、010、007、008、003、006、004、001、009、011（统一fixture-user-前缀）。旧001强制开发、其余按序补002；11//5=2。测试使用字面期望和已经确认的001哈希向量，不调用生产排序计算期望。

工程审查修订轮次目前0；正常红绿实施中的迭代不混记为首次完整验收后的阻塞修订。正式阶段仍只发布分组组件，不发布模型输入、SIM或充分性结论。

首轮完整回归：`python -m unittest discover -s tests -v`，178项通过（原164＋新增14），69.758秒；完整输出见 `ticket07-full-tests.txt`。实际来源的独立验收与双轴审查仍在后续执行。
