# 工单 07 第一阶段：旧探索账号与暴露证据附录

日期：2026-10-14。状态：只读诊断，供分组审核草案引用；不构成正式分组配置或正式样本充分性判断。项目基线为 `e2617ada7a182685fef00567dbf064fc096d46f4`。

本附录采用已安装 `mattpocock-skills:research` 的一手来源核查方式，核对旧清单、生成代码、协议、审计产物及一份明确相关的历史会话日志。程序均显式在项目内的 `Thesis` Conda 环境执行；没有运行历史推荐器、模型或 SIM 实验，没有更改原稿、上游产物、工单和正式规格。本次身份及历史输出核查仅由程序读取、匹配和计数；向本次 agent 上下文返回的是汇总、文件结构与证据字段，不返回原账号标识、逐账号目标、推荐结果或表现。

## 1. 账号集合与当前合格账号交集

当前集合取 [06 账号资格清单](C:/Users/Kane/Documents/CodexProject/Thesis/data/cleaning/grain-A-1.1.15/review-cleaning-1.0.0/account-eligibility.jsonl) 中 `status == "qualified"` 的原始 `user_id` 去重集合，共 1,603 个。所有交集均按账号标识精确相等计算，不按目标商品、任务编号或场景数计数。

| 历史集合 | 历史账号数 | 与当前 1,603 账号交集 | 数据层及可支持的结论 |
|---|---:|---:|---|
| 初期小评论集合 | 313 | 23 | 原料账号，证明曾进入旧评论处理；不能据此认定逐账号推荐结果已查看 |
| 旧扩展评论集合 | 7,538 | 113 | 原料及背景统计账号，证明旧处理范围；其中并非人人有旧偏好任务 |
| 旧扩展跨商品资格探索清单 | 165 | 16 | 资格、时间和目标探索层；有 `target_item` 等私有字段，但存在文件不等于每条内容曾被阅读 |
| 旧偏好基线任务 | 134 | 13 | 确定性偏好基线的账号；交集含旧 dev 2、旧 test 11 |
| 旧机制原型任务 | 19 | 4 | 真实来源账号配模拟请求、批次和证据；不是 19 个虚构用户 |
| 旧 134 与旧 19 的并集 | 138 | 14 | 两旧任务集合不是互斥的；历史交集 15，当前交集 3 |
| 旧 165 与旧 19 的并集 | 165 | 16 | 旧 19 全部包含于 165；相对两旧任务并集，多覆盖 2 个当前合格探索账号 |

一手入口：初期原料为 [feasibility/reviews_grain.jsonl](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/reviews_grain.jsonl)，扩展原料为 [feasibility/expanded/reviews_grain.jsonl](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/expanded/reviews_grain.jsonl)。资格探索清单为 [feasibility/expanded/temporal_eligible_users.json](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/expanded/temporal_eligible_users.json)，165 行列表，字段包括 `user_id`、`target_item`、`target_time`、`history_distinct_other_items`、`strict_unseen_last_item`、`positive_target_with_positive_history` 和 `positive_target_with_positive_text_history`。生成字段及资格判断见 [expand_reviews.py:108](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/expand_reviews.py:108)。

另一个同名文件 [feasibility/temporal_eligible_users.json](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/temporal_eligible_users.json) 只有 19 行，字段为 `user_id`、`history_count`、`target_item`、`target_time`，属于初期留后资格材料；不能与扩展目录下的 165 行清单混淆。机制任务身份应直接取 [prototype_tasks.json](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/prototype_tasks.json) 的 `user_id`，不把两个“19”当成无需验证的同一集合。本次验证机制任务的 19 个账号全部存在于初期真实评论来源。

## 2. 可复核的身份映射

旧偏好 [split_manifest.jsonl](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/repair_20261002/protocol/split_manifest.jsonl) 有 134 行，字段为 `split`、`task_id`、`user_hash`，没有原始账号标识。精确旧映射为：

```text
salt = "Plan_Thesis-parent-grain-v1-20261002"
user_hash = SHA256(UTF8(salt + "|" + source_user_id)).hexdigest()
```

原始来源标识直接按字符串使用，不擅自 trim、改大小写或 Unicode 归一化。旧划分按十六进制字符串升序取前 27 个为 dev、其余 107 个为 test；见 [build_tasks.py:25](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/repair_20261002/protocol/build_tasks.py:25) 及 [protocol.md:11](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/repair_20261002/protocol/protocol.md:11)。本次程序重核：165 清单中 `positive_target_with_positive_text_history == true` 的 134 个原始账号，按该算法计算的哈希集合与旧分区清单完全相等，且没有重复哈希。

机制任务由 `prototype_tasks.json.task_id → user_id` 直接连接；[prototype_runner.py](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/feasibility/prototype_runner.py) 从原始 `reviews_grain.jsonl` 按来源 `user_id` 聚合历史并产生任务。SIM 标识用于请求、时间和材料，不改变真实评论账号的来源身份。

旧偏好目标可由 `evaluation_labels.jsonl.task_id → target_item` 与旧分区连接，再接原账号。仅程序核对与当前重叠的 13 个账号后，旧目标与当前 06 目标相同 1、不同 12、未知 0。扩充目录或目标变化不撤销账号的旧实验身份，也不能使其成为“新账号”。本核对没有输出目标标识、目标文本或评分。

## 3. 暴露状态分层与证据强度

“程序读取”“agent 收到汇总”“agent 收到逐账号结果”“人类实际阅读”是不同事实。下面的已证实阅读指内容曾进入历史 agent 可见工具返回，不推断人类眼动或实际打开状态。

| 层次 | 本次能够证实的事实 | 证据强度及保留边界 |
|---|---|---|
| 程序处理 | 旧 7,538 账号进入旧评论处理；134 账号形成基线任务和结果；19 账号形成机制任务 | 代码、清单、验证产物可交叉核对；不等于逐账号结果被阅读 |
| 查看汇总 | 旧协议、README 与 2026-10-09 复查报告公开记录 dev/test 汇总与区间，并在历史会话中读取 | 可证明汇总已进入 agent 上下文或交付文档；不能由此推断每账号结果均已查看 |
| 逐账号任务诊断 | 历史工具返回包括任务历史深度、候选数及时间检查等 `task_audit` 记录 | 这些是逐任务诊断，不能与推荐排名、命中或 NDCG 明细混同 |
| 实际逐账号推荐结果 | 2026-10-01 历史工具返回可解析出至少 8 个机制账号的逐任务推荐输出；其中至少 2 个属于当前 1,603，且这 2 个均在旧 134 及旧 165 中 | 有会话实际工具返回为证据，是可证实下界；不声称其余账号没有被阅读 |
| 首例机制结果及个案输入 | 2026-09-29 曾展示首个机制样例结果；2026-10-09 曾展示首条机制输入及旧偏好分区首条 | 这些已定位样例对应当前不合格账号；不能把它们套用为全部 19 或 134 账号已读 |
| 旧偏好逐账号模型排名及表现 | 已有文件和程序复算可以证实结果被生成、处理；本次限定主会话证据未证实当前重叠账号的具体偏好排名或逐用户指标被实际展示 | 每账号实际阅读状态为 unknown，不能记作未读，也不能因文件存在全部记作已读 |
| 人类实际查看 | 没有可验证的完整逐账号人类访问记录 | unknown；报告生成、程序运行或 agent 收到结果均不能自动替代人类阅读证据 |

旧协议本身已披露“既有数据分布、资格和原型结果已被查看”，且不称预注册或盲测外部验证，见 [protocol.md:3](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/repair_20261002/protocol/protocol.md:3)。该集合层披露支持保守复用政策，不足以还原每账号阅读清单。2026-10-09 报告中的“直接读取完整排名及逐用户指标”同时有 [audit_current.py](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/review_20261009/audit_current.py) 的自动复算路径，不能仅凭这句话推断人工或 agent 逐行看完结果。

### 3.1 逐账号结果展示的精确出处

限定会话为 Codex 中的“论文思路”，会话 ID `01a0c1d6-59c8-7c31-8cf8-cf428333a080`。仅检查其相关历史记录，不扫描秘密配置；没有穷尽全部子 agent 日志、外部编辑器或人的离线访问。

- [日志第 2254 行](C:/Users/Kane/.codex/sessions/2026/09/21/rollout-2026-09-21T10-40-45-01a0c1d6-59c8-7c31-8cf8-cf428333a080.jsonl:2254)：2026-10-01 04:40:35 UTC，即北京时间 12:40:35，工具调用以 `Get-Content` 读取 `review_20261001/experiment_audit_results.json`。
- [实际工具返回第 2257 行](C:/Users/Kane/.codex/sessions/2026/09/21/rollout-2026-09-21T10-40-45-01a0c1d6-59c8-7c31-8cf8-cf428333a080.jsonl:2257)：在真实返回正文中，至少 8 个完整记录同时具有 `task_id`、`full_top`、`title_only_top`、`review_only_top` 等字段。输出字段来源见 [audit_experiments_readonly.py:115](C:/Users/Kane/Documents/CodexPlan/Plan_Thesis/review_20261001/audit_experiments_readonly.py:115)。它们是确定性原型的账号级推荐结果，不能称作语言模型实验结果。
- 按 `task_id → prototype_tasks.user_id → 当前 qualified 集合` 程序求交得到 2；两者均属于旧 134 和旧 165。此计数不使用模型表现挑选用户，也没有把逐场景结果当作独立样本。
- [日志第 1351 行](C:/Users/Kane/.codex/sessions/2026/09/21/rollout-2026-09-21T10-40-45-01a0c1d6-59c8-7c31-8cf8-cf428333a080.jsonl:1351) 和 [第 1368 行](C:/Users/Kane/.codex/sessions/2026/09/21/rollout-2026-09-21T10-40-45-01a0c1d6-59c8-7c31-8cf8-cf428333a080.jsonl:1368) 还可证实首个机制样例结果曾展示；该账号不属于当前 qualified 集合。

上述是“至少”的证据。日志截断、其他会话、子 agent、外部工具和人类访问记录没有完整覆盖，因而不得把没有找到展示证据写成“确认从未查看”。当前旧探索交集 16 个账号中，至少 2 个已证实 agent 曾收到账号级推荐结果，其余账号的该阅读维度仍为 unknown。

## 4. 对分组审核的事实约束及待确认项

采用旧任务并集作为风险口径会涉及当前 14 个账号；采用旧 165 资格探索口径会涉及 16 个，覆盖两名已证实展示结果的账号及旧任务并集。采用旧全评论处理范围会涉及 113 个，但其中许多只有原料或背景处理证据，不能统一标注为“模型结果已经查看”。应由主报告给出这些口径的分组人数与取舍，由用户确认旧数据复用政策。

仍需确认：旧 165 探索集合的复用／排除政策；unknown 阅读状态如何进入开发或测试；用户是否记得其他个案查看、交互式浏览或离线结果阅读。补充记忆若没有可追溯文件，应保留其为用户陈述的来源类型。所有同账号后续根任务与场景必须继承同组，目标变化、任务重建及场景复制均不产生新独立样本。本附录不批准正式划分，也不宣称其余账号为全新盲测。

## 5. 来源快照摘要

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| 旧扩展 `temporal_eligible_users.json` | 51,882 | `fa56e6b3c35746854f41eb38e07e299070e4acfe3f872268c217bbb2563351be` |
| 旧 `prototype_tasks.json` | 136,519 | `6498668cdcb29709b5a3eb279534b4c33914f41571f8004c359c21b2b52f8de5` |
| 旧 `split_manifest.jsonl` | 16,589 | `320f710476a551bf226fff3fa5758aa1988eaa9cc72bb4fc105e908337ef5c32` |
| 旧 `experiment_audit_results.json` | 10,898 | `44f4c6473249d77d747bdc8379e657381cc6bbd09996ec90aefa4970f98a099c` |
| 当前 06 `account-eligibility.jsonl` | 23,806,848 | `5d39be3d9d1c7f02d9c6660a2e8e4d8b71795b7661d6f2347223e115008e6837` |
| 指定旧会话日志，本次读取快照 | 237,602,433 | `db5b9718a6eda2e843faa7f32fcd5566ee96b5a4e266d0208a11caa6eae58479` |

会话可能继续追加；第 1—2257 行原始字节前缀的 SHA256 为 `436cb895013f6aeac8a98d00b13c51fd5e1666d8a02e7be707241d888741d566`，可独立复核上述展示证据，不因后续追加而混淆快照。摘要用于标识本地来源内容，不证明人类访问历史或远端真实性。

## 6. 不输出账号结果的最小复核方法

以下标准库代码只读取日志第 2257 行、旧任务身份字段与当前资格集合。递归解包工具返回中的 JSON 及文字内 JSON，只收集同时具有三种推荐输出字段的完整任务记录。它不会打印任务编号、用户标识、目标、商品、分数或结果；预期只输出历史已展示账号下界 8、当前交集 2。代码作为本附录中的复核说明，没有新增公共入口、正式配置或历史模型运行。

运行环境须显式为 `conda run --no-capture-output -p C:/Users/Kane/Documents/CodexProject/Thesis/.conda/envs/Thesis python <保存于项目内的复核脚本>`。

```python
import itertools
import json
from pathlib import Path

old = Path("C:/Users/Kane/Documents/CodexPlan/Plan_Thesis")
current = Path("C:/Users/Kane/Documents/CodexProject/Thesis")
log = Path("C:/Users/Kane/.codex/sessions/2026/09/21/"
           "rollout-2026-09-21T10-40-45-"
           "01a0c1d6-59c8-7c31-8cf8-cf428333a080.jsonl")
task_users = {x["task_id"]: x["user_id"] for x in json.loads(
    (old / "feasibility/prototype_tasks.json").read_text(encoding="utf-8"))}
with (current / "data/cleaning/grain-A-1.1.15/"
      "review-cleaning-1.0.0/account-eligibility.jsonl").open(
          encoding="utf-8") as stream:
    qualified = {x["user_id"] for line in stream
                 if (x := json.loads(line))["status"] == "qualified"}
with log.open(encoding="utf-8") as stream:
    output = json.loads(next(itertools.islice(stream, 2256, 2257)))[
        "payload"]["output"]
decoder = json.JSONDecoder()
seen = set()

def scan(value, depth=0):
    if depth > 15:
        return
    if isinstance(value, dict):
        if value.get("task_id") in task_users and all(
                k in value for k in ("full_top", "title_only_top", "review_only_top")):
            seen.add(task_users[value["task_id"]])
        for child in value.values():
            scan(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            scan(child, depth + 1)
    elif isinstance(value, str) and any(
            k in value for k in ("task_id", "content", "full_top")):
        try:
            decoded = json.loads(value)
        except ValueError:
            position = 0
            while position < len(value):
                positions = [p for p in (value.find("{", position),
                                         value.find("[", position)) if p >= 0]
                if not positions:
                    break
                start = min(positions)
                try:
                    decoded, position = decoder.raw_decode(value, start)
                except ValueError:
                    position = start + 1
                else:
                    scan(decoded, depth + 1)
        else:
            if decoded != value:
                scan(decoded, depth + 1)

scan(output)
print(json.dumps({"shown_accounts_lower_bound": len(seen),
                  "current_qualified_overlap": len(seen & qualified)}))
```

自检：已区分原料处理、汇总展示、逐任务诊断、逐账号推荐结果及人类阅读；已对不能追溯的阅读状态保留 unknown；旧清单身份和当前交集仅在程序内匹配；只新增本附录，未写正式分组配置、名单或上游结果。
