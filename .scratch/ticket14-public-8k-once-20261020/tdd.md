# 8KiB增量TDD

BASE：83a5b38a8b057efdbecd2051f5d0f3e3b77f7d34。只改探针及其必要测试；复用A与上一PUBLIC协议验收。

| 公共边界 | 真实RED→GREEN |
| --- | --- |
| run_live_probe：超长工具回传导致第二轮正文超限，派发前停止 | 002仍派发两次→003仅一次 |
| send_response：8193字节及转义后超限的Unicode不启动子进程 | 004仍调用进程→005拒绝 |
| http_response：8192可发送，8193在建立连接前拒绝 | 006超限仍200→007拒绝；8192子断言首次即通过 |

008只运行tests.test_fourrouter_live_probe：新增3项、直接受影响8项，共11项通过（unittest 0.173秒）。成功往返的正文计量断言首次通过，未制造RED。未重跑A、上游或无关10项手动入口测试。

所有网络/进程替身及临时凭据均为PUBLIC；实际Key未用于测试。审计钩子拒绝真实数据、凭据与socket。子进程拒绝其他地址的既有测试不发HTTP。项目Python显式使用Thesis Conda及原4GiB Job守护；原账追加router8k_标签，无新依赖。
