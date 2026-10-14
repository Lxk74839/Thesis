# 工单07：方案A确认记录

2026-10-14。**用户已明确确认方案A及第一阶段审核草案第3节的研究规则；公共接口尚待确认，当前未开始实现。** 审查固定起点为 `e2617ada7a182685fef00567dbf064fc096d46f4`，后续保存文档或实现的提交不改变该起点。

## 确认来源和生效范围

来源为本聊天中用户在第一阶段交付后的明确指令：“我确认采用工单07审核草案的方案A，并确认第3节的精确划分算法、公共盐、取整及旧数据复用政策。”用户同时要求先保存诊断与确认记录、展示最小接口及公共测试边界，接口确认后再实施。

本记录使以下D5子事项生效，不回写历史草案以伪装其当时已获批准：

1. 固定使用06已验收的1,603个合格来源账号Q；不重新筛选资格、替换目标或重跑清洗。
2. 开发名额为 `len(Q)//5 = 320`，旧165资格探索账号与旧19机制任务账号并集同Q的交集E共16个，全部进入开发。
3. Q\E按第4项排序，前304个补开发，余下1,283个测试；不另选盐、种子或按表现择组。
4. 精确输入为 `salt.encode('utf-8') + b'\x00' + user_id.encode('utf-8')`，取完整SHA-256摘要；按 `(digest_bytes, user_id_utf8_bytes)` 升序。来源user_id不trim、不改大小写、不做Unicode归一化。
5. 已确认的公共盐为 `Thesis-ticket07-grain-A-1.1.15-review-cleaning-1.0.0-split-v1`，无引号、空格或换行；floor取整不改为概率阈值或四舍五入。
6. 其他旧原料程序处理账号允许按此政策划分，逐账号阅读状态保持未知，不标记为从未暴露。至少2个当前账号旧逐账号推荐结果进入代理上下文的证据保留；不据此推断人类实际阅读或其他账号未读。
7. 同一来源账号的全部根任务、场景与重复运行继承同一组，任何场景扩充都不增加独立账号数。
8. 不宣称全新盲测。D10充分性继续待判定，模型输入、SIM和07以外的工作不随本次确认获准实施。

## 实施及审查约束

- 当前只准备接口提案，用户确认stage、参数、配置、受限输出及公共测试边界后，才写生产代码、正式配置和新增测试。
- 唯一公共入口为 `prepare_data.py`。随后按mattpocock-skills逐个公共行为RED→GREEN；不先批量写全部测试或导入生产内部函数验证。
- 项目代码、测试、核查与复现均显式使用 `conda run -p C:/Users/Kane/Documents/CodexProject/Thesis/.conda/envs/Thesis`；当前环境Python 3.13.16，未安装依赖。
- 最终Standards与Spec分别审查，固定比较起点始终为 `e2617ad`，不能改为保存第一阶段的文档提交。
- 首轮完整验收／审查后，如有真实阻塞缺陷，最多统一修订一轮并复核；仍不通过则如实报告未通过项目并结束，不自动扩大范围。正常逐行为RED→GREEN日志与审查修订轮次分别记录。
- 原稿、06及其上游材料只读；不重开已接受的格式勘误，不覆盖已有版本。最终交付须包含版本化规则、受限名单、暴露记录、统计、独立核查、复现报告及实际提交编号。

## 第一阶段保存清单

下列7项保持第一阶段交付时的原始内容；旧“待确认”状态表示历史时点，现有结论以本确认记录为补充。没有把支持代码当作新公共入口，也没有把当时试算写成正式分组。

| 项目内路径 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `.scratch/data-preparation/diagnostics/diagnose_ticket07_stage1.py` | 16,151 | `dc79cc4760885ad433df5ab66848651e8bf713b68384d64c85405699a99a1476` |
| `.scratch/data-preparation/ticket07-legacy-exposure-audit.md` | 15,610 | `b128483ec93fe409bc1c08694cf9b35366eb360369b0743c677a9b48a88e7b01` |
| `.scratch/data-preparation/ticket07-sample-diagnostics-stage1.md` | 16,429 | `8f63a7fb8cc6ad1a84100f73cbbb92e57d16840b69045d47be315e05322f38ee` |
| `.scratch/data-preparation/ticket07-split-review-draft-stage1.md` | 10,759 | `3f370a67ee8c2421530f0974e65024230205876219dca80c92009c3948646b6c` |
| `.scratch/data-preparation/ticket07-stage1-pending-decisions.md` | 4,186 | `62d5b6c5ce3cdc4cceeac0ed12176a830d1dcf0526e6e8ad7c6e1bb52bec1459` |
| `.scratch/data-preparation/verification/ticket07-stage1-aggregates.json` | 24,495 | `2042c2ee63b0196ca95ea9fd2e6129e1dc8dadef1d8d5ac6d5255ed3842f0e13` |
| `.scratch/data-preparation/verification/ticket07-stage1-check.json` | 1,559 | `246ce06b47f156281e1b124ff79cdfaf5f5aef664109ef9a0373e3941c74d22f` |

保存时已核对支持代码与汇总的摘要符合第一阶段核验记录；06主记录仍为 `087134e66aec971070aaca11eee837112fd39a0893993b16b94b2194b19d89a5`。Git保存提交号由提交完成后实际报告，不写自引用提交号。

`.gitattributes`仅对上述7项禁用换行转换，以便Git保存和检出时保留本表绑定的原始字节；不改变原稿、06产物或其他已有文件的格式政策。
