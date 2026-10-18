# T0-A独立Spec审查：250de6b

BASE：`88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a`。候选：`250de6baf1aede000795d1748e0737d847ba7f6c`。固定命令：`git diff 88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a...250de6baf1aede000795d1748e0737d847ba7f6c`。提交：`1c5036c`授权归档、`250de6b`离线目录实现。

依据：t0-a-implementation-confirmation-20261018.md、authorization-t0-a-20261018.md及本聊天确认；继承023a6cc/88e8b80，不重审已接受实现。仅静态查阅源码、合同和records/config元数据；Python/测试/实际A/API执行0，没有读取开发/测试正文、身份键或私有评价目标；未读另一轴报告。

**结论：blocking=2，nonblocking=0。暂不接受本候选进入实际A。**

1. **[P1，未授权读取]** `t0_catalog.py:529–531`在scope与固定元数据路径校验前，对调用方提供的contract/human_confirmation/program_acceptance执行整文件读取摘要。开发路径检查到`434–473`才发生；公开模式`535–539`只约束sources，三个元数据ref没有fixture边界。因此封闭但未获批准的授权JSON可先打开项目内私有目标/测试正文，然后才被拒绝。合同§3.1要求“禁止打开私有evaluation/reference/gold/UQ…目标正文”，§7行为1要求“目标/测试正文访问陷阱不触发”。应在任何正文/摘要读取前验证各类ref的允许路径，并以公共CLI访问陷阱验证。

2. **[P1，表面合法但轨迹不可执行]** `t0_catalog.py:373–377`生成Issue.verifier为角色名；既有`recommendation_runner.py:654–678`要求值为`model`，故所有非空声明路径会在此终止为invalid_model_issue。另`364–365,383`把必要理由写成通用英文，最终修订仍不满足既有`587–600`固定的claim/kind/text规则，却继续声明再核验无Issue及final。合同§4.2要求“不改…业务验证”，§4.3要求“合法提前终止…保留实际到达的脚本阶段和原因，不虚构final成功”。应使synthetic回复符合原公共行为；有意注入的问题须在已声明修订中闭合，并通过必要run替代sender集成验证。

范围核对：新增/修改文件符合§6；零发送、独立资源域和null计数边界保留。真实覆盖、N/U、资源和复现仍待获准后的实际A，未据此认定程序缺陷。来源R1/R5 profile原生clause_id确为c1/c2（sim_scenarios.py:157–173），提取这些原ID并保留完整条款对象不构成替换真实条款。
