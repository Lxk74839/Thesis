# Grocery 完整元数据来源核查

本文件记录工单 02 的原始来源与诊断事实。规格正文已确认，未决规则与参数尚未冻结；本阶段没有筛选谷物商品、清洗评论或建立正式联合数据包。

## 来源与完整性

- 官方入口：[Amazon Reviews'23](https://amazon-reviews-2023.github.io/main.html)。下载链接指向 UC San Diego McAuley Lab 的完整 Grocery 元数据压缩文件，地址及官方字段类型保存在 `sources/amazon-2023-grocery-metadata.json`。
- 获取完成时间：2026-10-10T12:28:56.478811+00:00。HTTP 200；实际字节数与 Content-Length 均为 324,346,561。
- 来源响应 Last-Modified：Thu, 16 Jan 2025 22:23:14 GMT；ETag：`"135522c1-62bda3d801e5f"`。它们是文件快照线索，不是研究参数。
- 原始压缩文件 SHA-256：`ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2`。另用 PowerShell Get-FileHash 对落盘文件独立复核，结果一致。
- 扫描到 gzip EOF 并通过 CRC/尾部校验：603,274 行、603,274 个 JSON 对象、603,274 个唯一有效 parent_asin；解析异常、非对象行、无效父标识及重复父标识均为 0。首尾父商品为 B00NE08WM6 与 B000N7WXDM。
- 检查的官方页面未提供该文件的发布方摘要。HTTPS 来源、响应长度、gzip 校验及本地 SHA-256 支持已捕获文件的完整性与后续一致性复查；不能宣称已对照发布方独立发布的密码学摘要认证。
- 官方页面的商品统计基于评论中的商品，不能用作元数据文件的精确预期行数；本次行数来自实际全量扫描。

机器记录见 `records/sources/amazon-2023-grocery-metadata.json`。原始字节位于该记录的 raw_path，未经筛选或改写；整个 data/ 均被 Git 忽略。records/、sources/ 和本核查说明可版本管理。

## 字段实测

“缺失”指 JSON 对象没有该键；“null”另计。“空”仅统计空白字符串、空列表或空字典，不代表已决定剔除。除新增字段 author、subtitle 外，官方列出的 14 个键均出现在全部 603,274 条记录中。

| 字段 | 官方声明类型 | 实际类型及数量 | 缺失键 | 空值容器/字符串 |
| --- | --- | --- | ---: | ---: |
| parent_asin | str | str 603,274 | 0 | 0 |
| title | str | str 603,274 | 0 | 38 |
| main_category | str | str 595,314；null 7,960 | 0 | 0 |
| categories | list | list 603,274 | 0 | 68,198 |
| description | list | list 603,274 | 0 | 225,223 |
| features | list | list 603,274 | 0 | 167,424 |
| details | dict | dict 603,274 | 0 | 16,930 |
| price | float | float 224,318；null 378,955；str 1 | 0 | 0 |
| average_rating | float | float 603,274 | 0 | 0 |
| rating_number | int | int 603,274 | 0 | 0 |
| store | str | str 585,994；null 17,280 | 0 | 1 |
| bought_together | list | null 603,274 | 0 | 0 |
| images | list | list 603,274 | 0 | 88 |
| videos | list | list 603,274 | 0 | 428,743 |
| author | 官方字段表未列出 | dict 17；null 7 | 603,250 | 0 |
| subtitle | 官方字段表未列出 | str 20；null 4 | 603,250 | 0 |

类型偏差和稀疏字段已如实保留；当前诊断成功仅表示来源获取与扫描完成，不表示每个字段都满足将来的清洗规则。尤其不能将 null 改称缺失键，也不能自动把价格字符串转成数字。

独立复核按解压数据块统计换行：1,382,105,675 个解压字节、603,274 个换行，文件以换行结束，与扫描行数一致。唯一价格字符串位于第 113,255 行、父商品 B004PYDISS，原值为 `—`。

## 关联与时间事实

官方说明使用 parent_asin 将评论关联到元数据；不同变体可共用父标识。本阶段获取的是父商品材料，真实评论未来仍归父商品，不归模拟批次。

此文件的实际顶层字段没有评论时间或历史快照时间。官方将 price 描述为抓取时美元价格；average_rating 和 rating_number 为商品页面汇总值。HTTP Last-Modified 不能替代用户行为时间，也不能证明这些字段在某一历史目标时点已知。评论时间字段及单位要在工单 03 核实；这些汇总字段是否允许进入模型由 D6 对应工单确认。

D1 商品边界、缺失处理、去重、时间截断、用户划分、样本充分性与实验场景等规则继续待确认。空类别/空描述等计数仅为后续筛选及样本流失诊断提供事实，不代替规则审批。

## 公共入口与复查

在 Thesis 根目录运行；环境内只有 Python 与其运行库，无项目第三方依赖：

```powershell
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage metadata --source-manifest sources/amazon-2023-grocery-metadata.json --output-root 'C:\Users\Kane\Documents\CodexProject\Thesis'
```

入口完整下载并扫描；原始文件以内容摘要命名，失败刷新不会覆盖此前完整捕获的原始字节。完成诊断返回 0；来源损坏或解析/父标识异常返回 2，并输出及保存机器诊断。未生成正式数据包，formal_package_status 始终为 not_built。

错误行文件在每次获取开始时重置，始终属于当前尝试。下载失败而未开始扫描时文件为空，须结合 source_incomplete 状态和零扫描计数解释，不能据此认定来源没有异常。HTTP 分块响应截断也会保存当次机器诊断。

测试也使用同一公共入口；通过真实本地 HTTP/文件边界的微型夹具验证后段记录、字节摘要、CRC/截断、HTTP 片段/短响应、坏行继续诊断、父标识、字段空值、刷新保留与空来源。审查后另以失败测试复现并修正 HTTP 分块截断及旧错误行混入，共十一个行为逐项经历失败测试后再通过；完整来源另有本次实际获取与核查记录。

```powershell
$env:TMP = Join-Path (Get-Location) '.tmp'
$env:TEMP = $env:TMP
& 'D:\Work\Anaconda\Library\bin\conda.bat' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' python -m unittest discover -s tests -v
```

环境版本及精确包构建见 `environment-win-64.lock.txt` 与 `.scratch/data-preparation/verification/installed-packages.json`。来源字节、字段计数与独立复核见机器记录及 `.scratch/data-preparation/verification/metadata-source-check.json`。这些记录冻结的是本次获取事实，不是 D1—D12 的研究规则。
