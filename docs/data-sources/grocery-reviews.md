# Grocery 完整评论来源、关联与时间核查

工单 03 的原始来源获取与事实诊断，2026-10-10。规格正文已确认，未决规则与参数尚未冻结。真实评论继续属于 parent_asin 父商品，asin 是被评价的商品／变体标识；二者都不是模拟批次。当前没有正式商品目录、清洗数据、时间截断或联合数据包。

## 来源与完整性

- 发布者：UC San Diego McAuley Lab，Amazon Reviews'23，Grocery_and_Gourmet_Food，完整 user reviews gzip JSONL。[官方入口及字段表](https://amazon-reviews-2023.github.io/main.html)、[官方评论文件](https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Grocery_and_Gourmet_Food.jsonl.gz)。没有使用前缀、抽样、ratings-only 或 5-core 文件。
- 来源配置：[sources/amazon-2023-grocery-reviews.json](C:/Users/Kane/Documents/CodexProject/Thesis/sources/amazon-2023-grocery-reviews.json)。官方被检查页面没有发布该文件 SHA-256；下面的摘要标识本地完整快照，不声称是发布方提供的签名。
- HTTP 200，Content-Length 与实际获取均为 **1,630,860,152 字节**。响应 Date 为 2026-10-10 14:02:43 GMT；下载落盘完成的文件时间为 2026-10-10 14:05:04.6657715 UTC；完成字段扫描并写来源记录的时间为 2026-10-10 14:08:56.003388 UTC。服务器 Last-Modified 为 2025-01-16 23:30:58 GMT，ETag 为 `"6134f378-62bdb2fba2591"`，两者不替代摘要校验。
- 完整压缩文件 SHA-256：`7f6ae806af2e2dbdda8564abde3141b81c7ee3cf4d8443d361d6bdad91aea4b8`。PowerShell Get-FileHash 独立复核相同。
- **14,318,520 行，14,318,520 个 JSON 对象**，首行父商品 B00CM36GAQ，末行父商品 B0714KTNVM。gzip 读至 EOF，CRC／ISIZE 校验通过。另一个进程按字节块计数换行并第二次读至 EOF，记录数一致，解压后字节数 5,973,991,903。
- 首次请求连接超时，下载 0 字节，明确记录 source_incomplete；[失败留痕](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-acquisition-first-attempt.json)。重试才得到上述完整快照。完整来源报告为 needs_review，原因是下述 1 条越界评分；这不等于文件未取得完整，也不代表已完成清洗。

原始文件和行级诊断位于被 Git 排除的 data/；版本管理目录中的[来源报告](C:/Users/Kane/Documents/CodexProject/Thesis/records/sources/amazon-2023-grocery-reviews.json)保留定位路径、摘要、响应头、完整字段分布和关联／时间统计。压缩字节原样保存，因此全部原始评分、标题、正文和时间值均可恢复，包括异常记录。诊断中的字符串空白判断只用于计数，未写回或规范化原文。

## 字段与异常

实际全文仅出现字段表中的 10 个字段；各字段在全部 14,318,520 条对象中出现，缺失 0、null 0。rating 为 float；title、text、asin、parent_asin、user_id 为 str；images 为 list；timestamp、helpful_vote 为 int；verified_purchase 为 bool。

| 核查项 | 全量结果 | 本轮行为 |
| --- | ---: | --- |
| gzip 损坏／截断 | 未发现，EOF 校验通过 | 保存完整来源 |
| JSON／字符解码解析失败 | 0 | 夹具覆盖失败定位及继续扫描 |
| 非对象行 | 0 | 单独统计 |
| 缺失、空白或无效父商品标识 | 0 | 不回退变体标识 |
| 缺失、空白或无效 asin／user_id | 0／0 | 原值保留 |
| 非数值或超出官方评分域 [1,5] | **1** | 仅标记，原值保留 |
| 非字符串正文 | 0 | 原值保留 |
| 空字符串或纯空白正文 | **16,801** | 仅计数，继续保留 |
| 空评论标题 | 0 | 仅计数 |
| 空 images 列表 | 13,726,167 | 来源字段事实，不自行定义为坏样本 |
| 缺失／null／非整数／不可表示时间 | 0／0／0／0 | 处理规则留待工单 06 |

越界评分在原始文件第 **378,447 行**，父商品 B0C396H8QB，asin B00RQPUV0Q，原始 rating 为 **0.0**。行级错误文件仅记录行号与原因，真实数据中共 1 条；没有丢弃、替换为 1、补值或重写该行。[独立抽核](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-check.json)保存公开字段片段，不发布 user_id 或全文副本。

## 父商品关联

官方字段表说明使用 parent_asin 查找商品元数据；同一父商品可有不同尺寸、样式等商品标识。[字段依据](https://amazon-reviews-2023.github.io/main.html#for-user-reviews)。入口先复核工单 02 元数据文件的 SHA-256，再读完整父商品集合。未匹配记录不会被按 asin 回退、删除或绑定 SIM 批次。

| 项目 | 数量 |
| --- | ---: |
| 元数据父商品 | 603,274 |
| 评论中有效独立父商品 | 603,182 |
| 匹配父商品的评论行 | **14,318,520** |
| 无法匹配的评论行／独立父商品 | **0／0** |
| 有评论的元数据父商品 | 603,182 |
| 无评论的元数据父商品 | **92** |
| asin 不同于 parent_asin 的评论行 | **7,961,504** |

这里的“独立父商品”是去重标识统计，不是独立用户样本。重复 parent_asin 是多条原始评论，不能当作元数据重复或用于增加独立样本数。本阶段没有评论去重、用户充分性判定或热度筛选。

## 时间事实及 UTC 依据

官方字段表将 timestamp 描述为整数 Unix 时间，但没有直接标注存储单位；[作者论文第 2.1 节](https://arxiv.org/html/2403.03952v1#S2.SS1)说明该版本时间戳具有毫秒精度。结合全文整数分布、实际子秒值、可表示日期范围和下面的独立转换核查，本文件的核验结论为 **自 1970-01-01T00:00:00 UTC 起的整数毫秒**。这是文档与实测共同支持的解释，不是仅凭位数推测。

转换为 `UTC epoch + timedelta(milliseconds=raw_timestamp)`；原始整数不改动。诊断仅拒绝缺失、null、非整数（含 bool）及超出日期表示范围的值，不把某个研究截止日或经验时间范围当作异常门槛。全文件 14,318,520 个 timestamp 均可按该单位表示；其中 **10,953,922** 条原值除以 1000 的余数非零，保留毫秒。

| 原始行 | 原始 timestamp | 独立 .NET UTC 转换 |
| ---: | ---: | --- |
| 1 | 1587854482395 | 2020-04-25T22:41:22.395+00:00 |
| 378447 | 1595703983161 | 2020-07-25T19:06:23.161+00:00 |
| 1768274（最早） | 965820395000 | **2000-08-09T11:26:35.000+00:00** |
| 14313383（最晚） | 1694550038851 | **2023-09-12T20:20:38.851+00:00** |
| 14318520 | 1541654252673 | 2018-11-08T05:17:32.673+00:00 |

原始行按块边界提取，五点通过 `DateTimeOffset.FromUnixTimeMilliseconds` 独立转换，再用 `ToUnixTimeMilliseconds` 回验原整数；最早／最晚 UTC 与公共入口相同。[保存的核验依据](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/review-check.json)。这些是实际 Grocery 文件边界，不是批准的实验时间截断。

官方网页快速示例含 sort_timestamp 与 helpful_votes；字段表与本次完整实际文件使用 timestamp 与 helpful_vote。全文没有出现前两者，不能从网页示例擅自重命名或替代。本轮完成 D2 的字段、单位、UTC 事实子项，D2 的时间处理和其他未决研究规则仍待确认。

## 复现与验收边界

获取调用（PowerShell；TMP/TEMP 指向项目 .tmp）：

```powershell
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' python prepare_data.py --stage reviews --source-manifest sources\amazon-2023-grocery-reviews.json --metadata-record records\sources\amazon-2023-grocery-metadata.json --output-root 'C:\Users\Kane\Documents\CodexProject\Thesis'
```

退出码 0 为完整来源且无所诊断异常，2 为来源不完整或 needs_review；须结合 error、gzip_verified 和 scan 判断。本次退出码 2 来自 0.0 评分诊断，不删行后改报成功。损坏、解析失败和字段异常各自保留统计及行号。

Thesis Python 3.13.16，解释器位于项目 .conda/envs/Thesis/python.exe。18 个公共入口测试通过，[TDD 逐项留痕](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/tdd-03.md)。获取时与验收时实现摘要分别记录，评分超大整数异常修复不影响本文件全为 float 的实际评分统计。26 份原论文与既有研究材料重新计算 SHA-256，改变 0；已确认规格摘要不变。代码审查及关闭结果另存工单验收记录。
