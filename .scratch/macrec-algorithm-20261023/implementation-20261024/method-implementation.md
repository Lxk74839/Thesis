# 原方法、适配与本轮算法代码对应

来源仍固定MACRec作者提交cbd9ea036cf6cac05a2ee59592526982a626fc82与原论文v3；不改变已有来源锁。当前B0命名为MACRec农产品有界适配，I1为来源约束的改进候选。两者都不是原环境/原数据的零修改复现。

| 责任 | 原机制/共同适配 | 当前业务实现 | 推荐排序作用 |
| --- | --- | --- | --- |
| 需求解析 | Task Interpreter；明确请求与历史分开 | run_task的interpret调用，输入仅允许H、当前实验请求和目录字段 | 当前明确偏好由宿主从真实请求优先保留，不由历史伪造必要条件 |
| 推荐管理 | 每步Thought/Action/Observation，4步/trial、最多2trial | 选择User/Items/Search/Finish，观察回到下一步；B0验证完整D排列 | B0由管理者实际排列；I1可提交带引用revisions，程序重验后重新评分 |
| 用户画像 | Analyst History/Info实际往返 | 不超过6维，直接原文引用与父商品去重，正负倾向/矛盾统计 | I1使用c=abs(n+−n−)/(n+ + n− + tau)，明确请求c=1；无支持/矛盾未知回退b |
| 农产品画像 | Item Analyst Catalog；共同D/白名单title,crop | 所有D×有效维度完整匹配矩阵，m为五档或unknown，双侧源引用 | 有效m进入先验调整，缺行/重复/越界拒绝，不补造商品或批次属性 |
| 生命周期追溯 | 外网Searcher替换成受限证据接口 | EvidenceTools通过真实EvidenceSession分页list、read、assessment；生产q保留C/T/A与beta(.25,.5,.25) | 四态决定资格；只对已支持库存软属性使用生产q，模型不得改写q或资格 |
| 推荐依据核验 | Reflector读首trial后决定是否再求解 | 原始候选、当前分量/引用、定位问题进入反馈，第二trial可修订匹配/引用 | 更新后保留前后排名，A-feedback停在真实首trial前缀，未强迫无问题改名次 |

I1：`s=b+lambda*sum(w*c*o*q*(m-b))`，每个组件的原值、可观察性、分数和round12排序分保留。同分先b降序再商品ID字节升序。目录q=1只说明字段引用有效；SIM的q不证明现实质量。必要条件未支持不会被高分补偿。

辅助内容CB保留接受包char3分，新增固定word1/2-gram TF-IDF与BM25，按平均同名次RRF比较三个固定权重；同一开发320评价侧选择M50/100/200，未召回目标不补入。最终模型D和输入顺序与目标无关。R/S/M保持旧画像协议和真实方法名，不改称B0。

主对照、公平条件、核心消融及结果判读仍用确认规格。当前验证只证明公开夹具上的数值/控制行为；真实API为0，不构成推荐性能改进证据。完整worker、259单元生产计划、36业务/25控制影响测试及固定候选双轴PASS见acceptance-implementation.md；渠道参数和B0/I1收益仍待真实验证。
