# 工单08确认与实施授权

2026-10-15。用户明确确认修订后审核草案第11节C1—C9推荐组合，以及第6.2、8、9节输入schema、公共Interface和验收合同，并授权开始实施。

批准文档：[文本画像审核草案](C:/Users/Kane/Documents/CodexProject/Thesis/.scratch/data-preparation/ticket08-stage1-field-isolation-review-draft-20261015.md)。其冻结SHA-256为`21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a`。原草案保留历史“待确认”措辞，本记录使对应条款生效，不改写已确认草案。

## 生效规则

- `text_portrait_trial_v1`及`finite-text-1.0.0`；商品parent_asin/title/crop，合格较早历史parent_asin/timestamp_ms/rating/text；历史评论标题及其他商品属性/details关闭。
- 有限HTML、联系方式／外链和已知商业尾句处理，全文保留、私有来源追溯。合法历史评分、当时价格、商品名不作泄漏删词；处理器不接受私有目标或相似度。
- 不改变06资格、07分组、全局端点、严格历史与背景时间、完整原始已见集合及全部未见父商品候选；背景排除全部开发／测试账号，互动训练关闭。
- 私有HMAC身份；A方案为无宿主I/O、无工具、无索引的独立API数据通道，以真实请求构造及权限分派的合成探测验证。不是NTFS沙箱或模型供应商部署验收。
- 唯一公共入口仍为prepare_data.py；新增preference_tasks阶段及split-record/task-config/access-probe，复用cleaning-record/output-root。测试从CLI子进程观察状态、产物和真实探测响应，不导入生产内部函数。
- 文本、时间、候选或依赖无法满足时报告原因和具体影响，不删账号、历史或候选凑通过，不更换目标。

## 实施及验收

先保存草案及本确认记录，再逐行为RED→GREEN；所有项目命令使用Thesis Conda环境，不增加无关依赖。代码审查起点固定`90ecec3c9b7d2edb7a2c9f46aa8b8523dbb6a4c8`，完成Standards／Spec独立审查。

真实验收逐项核对1,494个商品、1,603个根任务、开发320／测试1,283和1,845条合格历史正文投影；独立核查时间、完整候选、背景计数、有限文本处理、目标变更不干预输入、实际访问拒绝及新目录稳定字节复现。交付版本化配置、分离组件、探测、独立验收／复现报告和提交编号。

用户约束：首轮完整验收后最多集中修订一轮真实阻塞缺陷；仍不通过则如实报告并结束，不扩大范围。TDD开发阶段的预期RED不等于首轮完整验收；首次完整验收的各轴结果及集中修订轮次须如实记录。

本轮止于08试制验收。不调用推荐模型、不进入SIM或正式联合实验；原稿、研究材料及既有目录／清洗／分组数据只读，充分性保持not_determined。
