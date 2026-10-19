# G0 来源与元数据门

程序candidate85686efd88551c7201c4157e482d71be41927e82，双轴0阻塞后执行。新程序接受SHA b66974d64ce01fc8b8f0ca688ddd8969c27d23b279d26502babdf3cb99bc6ab8；G0派生授权SHA f310b3522675d4a85a5183f0af12e8958f5fbdf81d09228ff4ded42fa06b62d3。原T0账追加标签recovery_pilot_G0_001_snapshot，6.839783699950203秒；原累计1808.95254299995秒。未另建时间账。

独立snapshot退出0，T0_A_recovery_G0_bound_only。receipt保存在data/ticket12-t0/recovery-pilot-20261019/source-receipt.json，1,604,355字节，SHA4464a214b9daef5741fd73384b1c3ad8aab461e32f407cb88c1a4b9d0a2212da。完整宿主索引和原身份关联留本地，不入Git。

- 原320开发根HMAC与冻结source-index一致；真实32字节身份键正文读取1次，一次性read-claim保留；之后只消费receipt与键stat，不再读取正文。
- 元数据实际流式清点：2,403键、2,402标记完整、1中断、7,197缺失、80个完整30键根、81个有旧计划根，22,113条请求元数据。标记完整仍未接纳为旧正文验收。
- 固定四根顺序为最小完整根、其余完整根中旧累计W最大者、中断根、最小无旧计划开发根；四者不同，旧计划数分别30/30/3/0，旧W分别259,618,658 /264,335,590 /43,992,951 /0字节。原标识与选择证据见本地receipt。后续按根ID、视图标签、R/S/M规范顺序运行全部120键，不挑较小根或跳视图。
- 实际读取仅原catalog/coverage/source-index和roots/requests元数据；旧objects/dependencies/probes读取0。来源13件字节指纹匹配，程序15件指纹匹配，保护快照1,170件。
- Job读1,032,190,132B、写1,681,555B；守护读118,342,798B、写1,441B。为Windows IO transfer计数，包含缓存与审计；不是设备实际物理流量。Job峰值47,738,880B，加64MiB守护预留，共114,847,744B。

G1授权由G0授权仅增加receipt引用派生，授权绑定投影明确排除source_receipt，原G0文件保持不改；新G1文件另存authorization-recovery-pilot-20261019.json。全程保留T0_A_incomplete、工单12打开；G0通过不构成任何旧对象或完整A验收。
