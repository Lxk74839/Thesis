# 工单07分组独立核查与复现报告

2026-10-14。实现提交 `b6f79eaabe9f8c34c31ed46a35d1c4ac9c251ba0`；审查固定起点仍为 `e2617ada7a182685fef00567dbf064fc096d46f4`。**本报告核实分组组件，联合包、模型输入、SIM与D10仍未发布／待判定。**

正式主记录：[grain-A-1.1.15-user-split-1.0.0.json](C:/Users/Kane/Documents/CodexProject/Thesis/records/splits/grain-A-1.1.15-user-split-1.0.0.json)。规则为[已确认方案A配置](C:/Users/Kane/Documents/CodexProject/Thesis/config/user-split-1.0.0.json)，未改盐、算法、资格池或旧数据复用政策。06全部字节继续使用其既有格式勘误解释。

## 独立核查

[核查程序](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/diagnostics/verify_user_split07.py)不导入生产分组模块。从06资格清单、原旧165／19／7538账号来源、旧134哈希清单及历史日志第2257行重建事实，并用SQLite中的完整哈希十六进制二进制排序和固定LIMIT 304独立计算期望分区，逐个比对全部1,603账号。原始账号和结果不输出到公开日志。

| 验收项 | 实际结果 |
| --- | --- |
| 合格资格池 | 1,603来源账号 |
| 开发／测试 | 320／1,283 |
| 旧探索强制开发 | 16，全部开发 |
| 额外按哈希补开发 | 304 |
| 两组交集 | 0 |
| 两组并集 | 完全等于06合格池，无新增、遗漏或替换 |
| 所有归属／完整哈希／名单顺序 | 与独立SQL结果一致 |
| 旧原料交集：开发／测试 | 43／70 |
| 已证实旧结果展示当前账号 | 至少2，全部开发 |
| 代理逐账号结果阅读未知 | 1,601 |
| 人类实际阅读未知 | 1,603 |
| 公开主记录及正式运行日志 | 未包含来源账号标识 |

暴露快照的四个来源集合与原文件逐集合相等：资格165、机制19、旧语料7,538、偏好134。日志前1—2257行字节前缀摘要与第一阶段相等，独立解包实际工具返回仍找到至少8个旧账号的完整推荐输出记录，其中2个属于当前合格池。其余未知不能被当作未读；本次核查也不证明人类逐条查看。

开发／测试的历史深度、目标商品覆盖、目标作物及最大商品计数与第一阶段方案A试算全部一致：历史商品169／388，目标商品132／320，只有1个正向历史商品的账号277／1,151。身份不同不证明自然人独立，共享商品／后续材料相关性与稀疏历史限制保持披露。

完整结果：[独立核查JSON](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/user-split-1.0.0-independent-check.json)、[核查运行日志](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/ticket07-independent-run.txt)。

## 新目录复现与行序挑战

均从同一公共CLI运行，解释器为Thesis Conda的Python 3.13.16，没有依赖安装或模型调用。

1. 相同原来源、规则、事实快照和实现，在全新项目内目录运行，账号名单与暴露文件逐字节相等、SHA-256相等。
2. 在独立输入副本中反转06资格清单的全部53,576行，并反转旧集合列表和已观察记录顺序。副本的清洗主记录、接受清单、勘误及暴露快照按新字节据实绑定，原06及上游不改写。
3. 为全部1,603账号各提供3个不含内容的根／场景／重复引用，共4,809行；再反转引用行序。正常输入与反序副本分别经公共CLI运行，账号名单、暴露记录以及引用投影都逐字节相等。
4. 全部4,809个引用逐个匹配独立期望账号组；独立账号数仍1,603，开发／测试仍320／1,283。该检查只验收引用投影，未构造或验收08／13真实任务内容。

挑战目录保存在核查JSON的 `challenge_workspace` 字段中，位于项目 `.tmp/`；含账号的文件均不入Git。CLI调用输出保存于 `ticket07-reproduce-run.txt`、`ticket07-reference-run.txt` 和 `ticket07-order-run.txt`，它们只含汇总与来源摘要。

稳定组件采用UTF-8无BOM、显式LF、紧凑键排序JSON：

| 组件 | SHA-256 |
| --- | --- |
| 账号名单 | `05fbfdfcb5829fe09c71279748d9707ac1e25c8af6d496113ed804c221c2cbb4` |
| 暴露记录 | `3b3b69c5ce45e06909d75beae0d05ff257eed21353cdf5c7972c0f9cb27760ce` |
| 4,809条审计引用投影 | `29a7cfba74cc1e0cb0816c526db9b37e14925c33d71916abb4404aedbfd414bd` |

主记录包含运行时间、来源字节摘要等字段；反序输入的主记录据实不同，不把不同来源摘要伪称字节相同。正式运行未传group-refs，正式版只交付账号及暴露两个稳定组件，不包含审计用引用样本。

## 输入保护与实际边界

执行前保护的70项原稿、既有研究材料、06及上游来源／组件摘要全部未变。实际依赖清单会随验收保存；07目标工单及获授权修改的prepare_data.py不冒充只读上游。账号名单、暴露文件和事实快照均经git check-ignore确认排除。

当前完整回归178项通过（原164＋新增14），69.758秒。14个新增公共行为有逐次RED／GREEN日志，参见[tdd-07.md](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/verification/tdd-07.md)。原始unittest日志含工具自身的尾部进度空格，按原字节保存并以窄范围Git属性声明为原始日志，未通过删除失败行或重写输出通过检查。

代码审查尚须独立完成Standards／Spec两个轴；本报告的核查通过不替代其结论。若后续发现真实阻塞项，仅允许一次集中修订再核验，仍失败则停止，不扩到08或SIM。

复核调用：

```powershell
$env:TMP='C:\Users\Kane\Documents\CodexProject\Thesis\.tmp'
$env:TEMP=$env:TMP
$env:PYTHONUTF8='1'
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python .scratch/data-preparation/diagnostics/verify_user_split07.py
```

该程序是独立审计辅助，只调用prepare_data.py执行数据功能，不是第二个面向使用者的准备入口。运行会创建新的项目内诊断副本，不改既有正式版本。
