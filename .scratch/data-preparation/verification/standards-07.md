# 工单07 Standards 独立审查

2026-10-14；首轮。固定起点 `e2617ada7a182685fef00567dbf064fc096d46f4` 已解析，审查 HEAD 为 `cd984f7303ccb5efb2c001d68b32baa31fd73b40`。

比较命令：`git diff e2617ada7a182685fef00567dbf064fc096d46f4...HEAD`；差异非空，59个文件。提交为13448a7、b6f79ea、cd984f7。本报告仅作Standards审查，不代替Spec轴或关闭工单。

依据：AGENTS.md及用户提供的工作准则；docs/agents/issue-tracker.md、triage-labels.md、domain.md；正式spec.md的执行约定及Testing Decisions；获批ticket07-interface-proposal-user-split-1.0.0.md及实施授权；mattpocock-skills的TDD、tests.md、mocking.md与12项代码气味基线。项目内有界检索未发现CODING_STANDARDS.md、CONTRIBUTING.md、GLOSSARY.md、GLOSSARY-MAP.md或相关ADR，未擅自创建。

**结论：硬性标准违例0；判断性代码气味0；本轴阻塞项0。** 无需修改建议。

- 生产差异限于prepare_data.py的stage／参数分派和一个内部分组组件；没有改动旧测试或无关数据阶段。诊断与独立审计脚本明确为辅助证据，没有增加面向使用者的数据准备入口。
- 测试通过子进程公共CLI检查退出码、状态和产物；没有导入内部函数、模拟内部协作者或以调用次数断言。固定夹具期望为已知字面结果，未用生产算法反算期望。14次RED／GREEN日志、两次失败尝试及完整回归日志保留，运行记录使用项目Thesis环境。
- 规则及事实保存晚于明确授权；data/和.tmp/继续被Git排除。差异中没有原稿、06或上游组件变更，70项来源保护报告保留。原始unittest日志的窄范围whitespace例外仅保留日志原字节，未排除代码检查。
- 按代码气味基线核查新增实现与审计辅助。来源绑定、账号投影及稳定序列化均直接对应已批准接口，没有发现需提出的猜测性抽象、无用扩展或职责混杂。独立核查保留独立计算是验收要求，不建议与生产算法合并。

证据范围：本轴静态审查及既存TDD／回归／独立核查记录；未重复运行模型、SIM或查看账号级推荐结果，未修改实现、规则、测试或数据。
