# A5定向TDD

shared_red：五条旧发送意图保留时，第八条新增请求被旧共享12上限拒绝；新精确A5扩展后GREEN。合成账证明11×8192后再8192拒绝、1500最终额度可用，累计17/132572；A5第13次拒绝，旧字节前缀不变。非A5仍用旧12/98304上限。

storage_red：原守护没有run_root/独立额度且不支持128MiB；补充后GREEN。真实临时文件写入测试以小额度分别触发共享/单run拒绝，旧文件不变，拒绝字节未计入已写。实际A5为128MiB根+64MiB run。

admission_directed共6项PASS：新4项（共享额、真实存储、历史marker/执行时间保留、真实1493预检和发送控制链）+旧共享12调用拒绝及原marker回归2项。A5非法13调用/91613输出/1689870毫秒配置、缺run守护在准入拒绝。旧claim/实际回执/执行账/attempt均拒绝复用，时间账含A1..A5。首次已满足的拒绝条件如实GREEN，不制造RED。

真实D1装配使用完整1493候选，先_preflight再原_role→prepare→reserve→invoke到PUBLIC transport哨兵；非零递增单调时钟包含I/O，冻结期限保持，2MiB正文内且candidate_batches=1493；实际Key/网络/评价读取为0，无真实claim。是fixture发送链测试，不能冒充真实S结果。最终1/1500/145秒保留。

只改A5授权、预算传递和存储/Job边界；画像、Schema、API协议、六角色及发布源码未修改。定向回归通过后固定候选独立双轴审查，不重跑上游/完整旧测试、不增加PUBLIC联网探针。
