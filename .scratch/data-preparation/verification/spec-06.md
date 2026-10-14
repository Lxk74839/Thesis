# 工单06 Spec 静态审查

固定范围：`git diff 34aa1491b71906ec6e47e63ea6c8ecaec72154f2...a76a75aebfe9869472d841d0d96f181ebd413296`；范围内仅提交 `a76a75a`。

发现总数 **1**；真实阻塞 **0**，非阻塞 **1**；最高严重性 **P3**。

## (a) 请求但缺漏／部分要求

未发现本轮已批准要求的阻塞性缺漏。以[工单最新确认](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/issues/06-cleaning-eligibility.md:30)为准，历史草案的“尚未批准”文字不覆盖后续确认。来源绑定、逐行引用校验、完整对象归并、两类冲突、异常时间隔离，以及窗口内原始最大时点和全部更早原始已见集合均已实现（`review_cleaning.py:32–65,85–113,141–188`）。

## (b) 未请求行为／扩围

未发现。公共入口阶段及参数来自工单第30行的明确批准；分组、模型输入、SIM 和充分性仍分别标记未构建、未发布或待判定（`review_cleaning.py:211–213`），不要求在06实现后续D5／D6／D10。

## (c) 实现却错误的要求

- **[P3，非阻塞] 稳定序列化声明与 Windows 实际换行不符。** [规格第199行](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/spec.md:199)要求“稳定数据序列化与排序规则须明确”。[review_cleaning.py第220行](C:/Users/Kane/Documents/CodexProject/Thesis/review_cleaning.py:220)声明 `LF`，但第163–189行的 `Path.write_text` 未指定 `newline`，在 Windows 写出 CRLF。只读检查现有 `reviews.jsonl` 前65,536字节，观察到75个CR和75个LF，首个LF前为CR。建议显式固定LF或如实声明平台换行；该问题不改变本次记录语义，同一Thesis Windows环境内仍可复现摘要，无需作为阻塞修订。

本报告只做静态审查及只读字节检查；未运行Python、Conda、测试或独立SQL验收，不据此宣称全量06验收完成。原料及04／05产物未修改。
