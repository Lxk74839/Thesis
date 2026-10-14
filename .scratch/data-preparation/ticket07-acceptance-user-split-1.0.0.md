# 工单07正式验收与交付

2026-10-14。**工单07已验收关闭，正式分组版本为user-split-1.0.0。** 复用e2617ad交付的06资格池，按已确认方案A和公共接口实施。首轮完整验收及两个独立审查均通过，完整验收后的阻塞缺陷修订为0轮。

实现提交：`b6f79eaabe9f8c34c31ed46a35d1c4ac9c251ba0`；独立核查证据提交：`cd984f7303ccb5efb2c001d68b32baa31fd73b40`。固定审查起点：`e2617ada7a182685fef00567dbf064fc096d46f4`；审查HEAD为cd984f7。最终验收及工单关闭记录随本报告一并提交，提交编号由交付消息给出。

## 交付路径与访问范围

| 交付 | 文件 |
| --- | --- |
| 正式版本化规则 | [config/user-split-1.0.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/config/user-split-1.0.0.json) |
| 受限唯一账号名单 | [accounts.jsonl](C:/Users/Kane/Documents/CodexProject/Thesis/data/splits/grain-A-1.1.15/user-split-1.0.0/accounts.jsonl) |
| 受限逐账号暴露记录 | [exposure.jsonl](C:/Users/Kane/Documents/CodexProject/Thesis/data/splits/grain-A-1.1.15/user-split-1.0.0/exposure.jsonl) |
| 受限输入事实快照 | [legacy-exposure-1.0.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/data/split-inputs/grain-A-1.1.15/legacy-exposure-1.0.0.json) |
| 公开统计及来源主记录 | [分组主记录](C:/Users/Kane/Documents/CodexProject/Thesis/records/splits/grain-A-1.1.15-user-split-1.0.0.json) |
| 正式接受清单及依赖摘要 | [acceptance.json](C:/Users/Kane/Documents/CodexProject/Thesis/records/splits/grain-A-1.1.15-user-split-1.0.0-acceptance.json) |
| 独立核查／新目录复现 | [核查与复现报告](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-independent-and-reproduction-user-split-1.0.0.md)、[独立核查JSON](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/user-split-1.0.0-independent-check.json) |
| 公共CLI逐行为TDD及回归 | [TDD记录](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/tdd-07.md)、[178项完整回归日志](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket07-full-tests.txt) |
| Standards／Spec独立审查 | [分轴审查汇总](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/code-review-07.md) |

账号名单、暴露记录和事实快照仅供准备／评价侧使用，保留在项目内并由Git排除；公开产物不包含原账号、逐账号标签或结果。公共盐不能保护身份。本轮未实现08的模型运行时隔离，也未生成真实任务或正式引用文件；4,809条引用只用于验收投影继承。

## 正式规则

盐沿用第一阶段唯一试算值：`Thesis-ticket07-grain-A-1.1.15-review-cleaning-1.0.0-split-v1`。每账号的完整摘要为SHA-256（UTF-8盐＋单个NUL字节＋原始user_id的UTF-8字节），身份不作trim、大小写或Unicode规范化。按完整摘要字节升序，同值按原ID的UTF-8字节升序。

开发名额为floor(N／5)。合格池中的16个旧探索账号先全部开发，再从其余账号按固定序补304个，剩余1,283个测试。没有另选盐／种子，没有根据目标或模型表现挑选划分。其他旧原料账号允许依此进入任一组，阅读未知继续记为unknown。同账号后续全部根任务、场景和重复引用均查同一账号映射，不重新划分，不增加独立账号数。

规则、输入及实现摘要绑定。同版本同输入复用并校验既有组件；改变依赖、引用输入或损坏组件会拒绝覆盖。稳定文件为UTF-8无BOM、显式LF、紧凑键排序JSON；06原有CRLF保持原字节，继续依其格式勘误解释。

## 验收结果

| 条件 | 实际结果 |
| --- | --- |
| 06合格池／开发／测试 | 1,603／320／1,283 |
| 旧探索全部开发／固定哈希补开发 | 16／304 |
| 两组交集／资格池覆盖 | 0／完整且唯一 |
| 独立排序核查 | 全部1,603个账号与独立SQL计算一致 |
| 新目录同输入复现 | 名单、暴露记录逐字节及SHA-256一致 |
| 行序不变性 | 反转53,576资格行、暴露集合及引用行，归属和稳定组件不变 |
| 同账号引用继承 | 4,809条审计引用全部一致，独立账号数仍为1,603 |
| 逐行为RED→GREEN | 14个公共CLI行为，原失败记录完整保留 |
| 完整回归 | 178项通过（原164＋新增14），69.758秒 |
| Standards | 硬性违例0、代码气味0、阻塞0 |
| Spec | 发现0、阻塞0；独立重跑14项CLI测试通过，并补验目标／表现字段不影响归属 |
| 原稿／上游保护 | 70项来源摘要不变，无依赖安装 |

运行环境为项目Thesis Conda（Python 3.13.16），所有项目代码、测试和核查均显式通过该环境执行；验收按获批接口第5／6节检查退出码、公共JSON及产物，不导入生产内部函数作测试边界。两个独立审查报告各自保存，没有合并排序或互相替代。

稳定组件SHA-256：

- 账号名单：`05fbfdfcb5829fe09c71279748d9707ac1e25c8af6d496113ed804c221c2cbb4`。
- 暴露记录：`3b3b69c5ce45e06909d75beae0d05ff257eed21353cdf5c7972c0f9cb27760ce`。

## 统计、暴露与解释边界

| 项目 | 开发320 | 测试1,283 |
| --- | ---: | ---: |
| 旧语料处理重叠 | 43 | 70 |
| 旧探索重叠 | 16 | 0 |
| 已证实旧逐账号结果进入代理上下文 | 2 | 0 |
| 代理逐账号结果阅读未知 | 318 | 1,283 |
| 人类实际阅读未知 | 320 | 1,283 |
| 仅一个正向历史商品的账号 | 277 | 1,151 |
| 历史商品覆盖 | 169 | 388 |
| 目标商品覆盖 | 132 | 320 |
| 单一目标商品最大账号数 | 27 | 94 |

已证实展示的2个当前账号是可追溯下界；其余1,601个代理阅读状态和全部1,603个人类阅读状态未知，不能改记为“未读”或“从未暴露”。程序处理、查看汇总和实际账号结果分别记录；测试组70个旧语料账号仍按获批政策使用，并披露阅读未知。未宣称全新盲测。

第一阶段[样本流失、历史及覆盖诊断](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-sample-diagnostics-stage1.md)、[旧暴露核查](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-legacy-exposure-audit.md)、[方案比较](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket07-split-review-draft-stage1.md)及确认记录在13448a7保存，未被后续实施改写。原料53,576来源账号筛至1,603合格账号，1,428个合格账号仅一个正向历史商品（89.08%）；总体历史／目标商品覆盖435／361，目标玉米／稻米占80.97%。身份不同不能证明自然人独立，共享商品和材料仍可引入相关性；场景和重复运行不能充当新增独立样本。

本次只验收07分组组件：`formal_package_status=not_built`、`model_input_status=not_released`、`sim_status=not_built`、`sample_sufficiency=not_determined`。D10所需账号数仍待工单12论证，本轮结束，不扩展到模型输入或SIM实验。

## 复核调用

```powershell
$env:TMP='C:\Users\Kane\Documents\CodexProject\Thesis\.tmp'
$env:TEMP=$env:TMP
$env:PYTHONUTF8='1'
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage user_split --cleaning-record records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json --split-config config/user-split-1.0.0.json --output-root .
```

该调用验证并复用现有版本，不覆盖06或07稳定组件。含运行时间和来源字节摘要的主记录不属于要求逐字节相同的稳定数据；独立核查与新目录／反序挑战的完整调用和实际目录保存在复现报告及运行日志中。
