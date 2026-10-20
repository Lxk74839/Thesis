# 诊断与定向TDD

复现命令：check.ps1 sdeadline_001_red -m unittest tests.test_p1_s_deadline。读取旧失败审计第一条真实请求结构和已验收完整1493装配；只在ModelAdapter外部transport放哨兵，业务对象不改PUBLIC来源，所有本轮离线结论标fixture。时钟137000.25毫秒起步，每次读取增加5毫秒并叠加真实monotonic流逝，覆盖序列化和budget journal I/O。无凭据、标签、网络或实际claim。

RED为同一S_engineering_reservation_or_deadline，哨兵0次。red-diagnostic.json：deadline182254，冻结预留结束182169.2523000175，超出约84.75毫秒。保存后不覆盖。

按顺序验证三种假设：1）reserve后journal及处理耗时令重新计算的deadline外移；预测只统一冻结窗口即到哨兵。2）prepared身份不符；预测保持prepared/请求不变仍拒绝。3）根期限或phase不符；预测仅缩短到冻结窗口仍拒绝。只改变deadline来源后哨兵1次，原先所有其他适配器校验保持，确认1，排除本案例2/3。没有任意容差或窗口延长。

冻结窗口读取reserve receipt的usage_before/held/phase，与整根工作/最终期限取min；运行器再与当前时刻+30000取min并向下取整。适配器复用同一冻结窗口函数，继续拒绝过期、越界、phase/预留/nonce错误。诊断只含ID、时间、条件布尔。

定向验证：原1493请求RED→GREEN；过期/越界/预留不匹配/重复消费拒绝；无usage原S完整fixture发布且计量unknown；新S独立授权的真实1493装配、预检、prepare→reserve→invoke→transport哨兵通过（实际POST编码大小校验，真实HTTP=0），旧新授权不能交叉使用。sdeadline_004七项通过，sdeadline_005交叉授权拒绝通过。无usage fixture沿用原固定公开内容；所有这些是离线fixture验收，不能算真实S。

授权变化只增加确切S-DEADLINE-RETRY-20261020并绑定D1/V00/S及对应run_id；旧尝试claim和输出目录仍阻止复用旧许可。新控制入口调用已验收原执行/回执逻辑，独立目录；execution_guard逐字节复用既有Job守护，360秒另域记录。
