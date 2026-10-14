# 工单06清洗与用户资格验收

2026-10-14。**工单06验收通过；交付清洗及资格组件，未生成用户分组、模型输入、SIM或正式联合实验包。统计样本充分性仍待判定。**

用户已明确确认完整固定快照、排他上界1694550038852、整数毫秒UTC、原文完全对象归并与两类事实冲突隔离、最后原始时点唯一未见≥4非空目标，以及至少1个严格更早不同正向历史商品。公共入口新增review_clean和cleaning-config已另外取得用户明确确认。研究规则仅冻结此次D2—D4相应子项，D5以后及D10未关闭。

规则版本[review-cleaning-1.0.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/config/review-cleaning-1.0.0.json)。实现提交a76a75aebfe9869472d841d0d96f181ebd413296，审查起点34aa1491b71906ec6e47e63ea6c8ecaec72154f2。复用已验收grain-A-1.1.15目录／05提取，不重新扫描14,318,520行来源或修改原料。

## 实际流失

| 评论阶段 | 条数 | 来源账户 | 目录商品 |
| --- | ---: | ---: | ---: |
| 原始05提取 | 56,903 | 53,576 | 1,494 |
| 完整固定窗口 | 56,903 | 53,576 | 1,494 |
| 完全对象归并后的清洗账本 | 56,427 | 53,576 | 1,494 |
| 非空有效文本视图 | 56,363 | 53,513 | 1,494 |

443个完全重复组归并476个额外副本，全部来源行引用保留。64条空正文保留在原料、清洗账本和适用的原始已见集合中，不能进入有效文本；文本门槛使63个账户及1个商品失去可用文本，但该商品仍在1,494商品清单。11,916条低于4星的原始评价保留，低评分正文可以进入有效文本，只不充当正向画像。四元组／同商品等时事实冲突、异常时间／评分／标识／正文类型、窗口外记录均为0；隔离文件因此为空，负例由CLI夹具验证。

| 账户资格阶段／互斥排除 | 数量 |
| --- | ---: |
| 全部来源账户、时间可判定、最新父商品唯一 | 53,576 |
| 最新商品已见，排除 | 276 |
| 其余最新目标非正向或正文空，排除 | 11,366 |
| 最新唯一未见正向非空目标 | 41,934 |
| 以上缺少至少1个不同正向历史商品，排除 | 40,331 |
| 最终工单06合格来源账户 | **1,603** |
| 全部排除账户 | 51,973 |

排除按已记录的主原因顺序互斥对账，全部账户都有资格记录。多最新父商品、最新事实冲突、无效最新事实、无法可靠确定时间及无窗口交互在此真实快照中均为0；相应处理由逐行为TDD验证。目标先取最后原始时点，再判断资格，不向前找更早正向记录。已见集合包含全部严格更早原始交互，包括低评分、空正文和隔离记录；正向历史必须来自安全非空有效文本，按父商品去重。所有账户及行级明细仅在Git排除的data/内，不作为模型输入。

1,603是当前冻结规则下的可观测合格来源账户，不等于1,603个已证明独立自然人或最终测试样本。尚未分组、应用后续请求／材料／字段可用条件或进行D10论证，不声称充分或不足。

## 产物与独立验收

主记录：[grain-A-1.1.15-review-cleaning-1.0.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json)。六类数据位于data/cleaning/grain-A-1.1.15/review-cleaning-1.0.0/：reviews.jsonl、valid-text.jsonl、quarantine.jsonl、products.jsonl、account-eligibility.jsonl、source-row-audit.jsonl。保存全部源引用、原始字段、整数毫秒／UTC和每行／每账户去向；没有生成开发／测试分区、模型载荷、SIM材料或实验任务。

15个新增公共CLI行为各自先RED后GREEN，日志完整保留；完整164项回归通过（60.819秒）。没有用内部函数、生产输出重算期望或删失败测试来通过。实际采用插件TDD与双轴审查，见tdd-06.md、code-review-06.md及两份独立审查报告。

[独立SQL验收](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-cleaning-1.0.0-independent-check.json)未导入生产模块，读全部56,903条冻结05提取，独立检查完整对象分组、每个成员／来源行摘要、商品集合、全部输出行、原始最大时间、严格历史及账户排除。通过不表示重新扫描14M源；全源完整性由已验收05及未变摘要继承。

[全新目录复现](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket06-reproduction-check.json)通过：六类数据逐字节及SHA-256一致。**主记录中LF描述有误，实际Windows输出为CRLF；应随附[绑定摘要格式勘误](C:/Users/Kane/Documents/CodexProject/Thesis/records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-format-erratum.json)使用。** 完整字节核查确认UTF-8无BOM、所有非空组件使用CRLF；不声称原描述正确或跨运行平台字节一致。Standards有1项P3写出重复建议评估保留；Spec有1项P3格式说明问题附勘误；均无阻塞，不重开生产修订。

全部运行显式conda run -p C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis。Python3.13.16，实际解释器同目录python.exe；18个已装包及版本与基线一致，新增依赖0。47份上游保护文件、26份原稿／研究材料摘要均未变；04／05配置、目录、提取及验收没有覆盖。必要工程修订0轮。

## 复现调用

```powershell
$env:TMP='C:\Users\Kane\Documents\CodexProject\Thesis\.tmp'
$env:TEMP=$env:TMP
$env:PYTHONUTF8='1'
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage review_clean --catalog-record records/catalog/grain-A-1.1.15.json --review-record records/reviews/grain-A-1.1.15-review-diagnostics-1.0.0.json --cleaning-config config/review-cleaning-1.0.0.json --output-root .
```

已有版本校验依赖、生产器及组件摘要后返回原记录，不覆盖；新鲜生成可把output-root指定为项目内尚不存在的独立复现目录。实际新鲜复现目录为.tmp/ticket06-reproduce-1.0.0，命令日志ticket06-reproduce-run.txt。独立验收程序位于.scratch/data-preparation/diagnostics/verify_cleaning06.py，实际记录及全部日志可版本管理；运行环境、原料、生成数据和账户明细排除在Git外。稳定组件摘要及完整依赖链见主记录、验收清单与格式勘误。

本轮停止于工单06。07分组、08输入隔离和其余研究参数必须依对应工单另行确认，不自动推进。
