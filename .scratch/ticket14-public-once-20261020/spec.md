# 一次独立PUBLIC协议探针

Status: claimed

2026-10-20最新用户直接确认：免发送前精确计数，count=0、其他API=0；接受未知费用，cost=null，无人民币硬上限；最多2次Responses生成、并发1、重试0、禁止重定向及模型回退。每次max_output_tokens=256、reasoning.effort=none、单次30秒，整次联网阶段60秒。仅用既有PUBLIC虚构输入；第一轮取得有效函数调用后才发工具结果与严格JSON请求。任何错误、超时、未知发送状态或协议不符立即停止，不补发。

本轮BASE：64ebc5155683a2ba3116e4c54a029f068d9f5a02。继承A与手动入口验收；正式100用户18场景单轮目标不变，本次不运行其数据或评价。

## 最小接口与验收

- 现有check已在Thesis环境执行，仅报告api_key_filled=true、local_config_valid=true；不输出实际凭据或异常原文。后续不再为测试读取实际凭据。
- prepare_probe及既有协议校验复用，只补reasoning.effort=none；独立fixture始终保留fixture来源。
- run_live_probe(*, public_path, credential_path, receipt_path, sender, clock)：PUBLIC专用两轮流程；sender与clock为外部HTTP/时间测试边界。一次性脱敏JSONL回执先以独占创建封存，调用前记尝试；已存在即拒绝再次启动。原生usage、HTTP状态、响应模型及两类ID按实际记录，未知null；不存正文、Key或Authorization。
- send_response(endpoint, request, api_key, timeout, *, process_run)：仅POST固定Responses地址；密钥只走内存/子进程stdin，不入参数、环境或日志。每次独立子进程由父进程硬超时终止；HTTP本身用标准库HTTPSConnection，无重定向、重试或回退。process_run为外部进程测试边界。HTTP连接工厂仅作PUBLIC假网络测试边界。
- CLI probe在本条确认下启用上述一次性入口；不增加自动运行、其他模型/供应商或配置框架。CLI仅打印脱敏摘要。回执存在后不删除、不补跑；失败也消耗这次启动许可。
- 输出仅小型脱敏文件；最大读取响应64KiB，未知输出/原生结构停止或标null，禁止把原文错误写日志。sender成功与否独立于共享协议校验，不能把fixture重标真实。

逐公共行为TDD，只跑新增及直接受影响测试。固定精确candidate后独立Standards/Spec审查同一BASE...candidate；仅修阻塞项，完成后执行一次。验收必须区分协议成功、HTTP/协议失败和发送状态未知。

## 资源继承

原离线账累计1218.6089785001368/1800秒；T0不动，不扩额。沿用手动入口阶段300秒自限，前包已记81.1218187秒。本次原生读写/Git/收尾追加30秒、4MiB保守上界，非实测；守护、Conda启动、审查另计，预留联网最多60秒和收尾。仍用原4GiB Job限制、Thesis环境和项目临时/缓存目录；无依赖安装。独立PUBLIC联网授权只来自本条确认，不修改旧B合同或正式实验预算。
