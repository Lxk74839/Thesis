# 本轮TDD与定向验证

- usage_red：真实diagnose外部transport seam抛PUBLIC错误，因缺少usage键失败；usage_green：默认显式null及unknown/incomplete，断言异常原文不进入结果，1次fixture调用，无重试。
- quota_red：原入口缺少统一产物写入边界；新增write_artifact后，PUBLIC控制claim、stdout、P1结果和回执一起核算，超限写入创建前拒绝。首次复验发现测试字节常量算错（PUBLIC加换行共7字节，100份=700），修正测试后通过，未以它冒充实现缺陷。
- diag_final共4项通过：以上两项及直接相关既有单响应strict/已知usage/无正文、独占claim/回执/attempt拒绝。fixture并非旧真实响应回放。
- 新首请求真实安全输入预检：第一次脚本导入路径不完整、第二次断言错误地使用初始payload中的C键；均为新检查脚本缺陷，记录失败并修正。real_preflight_pass验证原组合器上下文1493个candidate_batches和1493个base_preferences、reasoning none，离线输出白名单metadata。无Key、claim、HTTP或S运行。

所有测试通过Thesis Conda及既有4GiB Windows Job；只运行上述本次增量，不重跑R/完整S/worker/上游套件。固定candidate16b8b53完成独立Standards和Spec，两轴均0项。没有凭手写fixture宣布真实响应成功。
