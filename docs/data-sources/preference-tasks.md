# 偏好输入试制合同

本合同仅实现工单08已确认的D6文本画像与A通道。批准依据为[冻结审核稿](../../.scratch/data-preparation/ticket08-stage1-field-isolation-review-draft-20261015.md)及[确认记录](../../.scratch/data-preparation/ticket08-implementation-authorization-20261015.md)。06资格、07组别及其原始字节不变；不调用推荐模型，不训练互动模型，不构建SIM或正式联合实验包，充分性仍待判定。

唯一公共入口在Thesis环境中调用：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TMP=Join-Path $PWD '.tmp'
$env:TEMP=$env:TMP
& 'D:\Work\Anaconda\Scripts\conda.exe' run -p 'C:\Users\Kane\Documents\CodexProject\Thesis\.conda\envs\Thesis' --no-capture-output python prepare_data.py --stage preference_tasks --cleaning-record records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json --split-record records/splits/grain-A-1.1.15-user-split-1.0.0.json --task-config config/preference-task-1.0.1.json --output-root . --access-probe data/task-inputs/preference-task-1.0.1/access-probe-1.0.0.jsonl
```

配置只接受第8.2节八组字段。text_portrait_trial_v1与finite-text-1.0.0冻结白名单及转换逻辑，无任意字段开关、目标参数或长度阈值。商品只有parent_asin/title/crop；历史只有parent_asin/timestamp_ms/rating/text，历史标题关闭。动态元数据、私有目标及参考答案不进入模型组件。

HMAC密钥在data/task-inputs/preference-task-1.0.0/id-key.bin私有区生成一次，为32字节随机值。task_id为HMAC-SHA-256(key, version的UTF-8字节 + 单个NUL字节 + 原始账号UTF-8字节)的完整小写64位十六进制摘要。版本域不含目标或组别。复现复用密钥，密钥及原账号不进入Git或模型manifest；丢失密钥即无法重现相同身份，不能临时重建冒充复现。

有限文本按顺序严格UTF-8、CRLF/CR归一、标准库单次HTML文本处理、C0（保留TAB/LF）及DEL控制字符去除、固定URL／ASCII邮箱／北美电话／本事件自身原账号遮罩、行内空白归一、最多连续两个LF处理。br及自闭合br每个产生一个LF；段落等块元素起止产生LF。script/style内容与注释／属性不进入文本，一次实体解码，无网络解析或执行。仅商品标题去批准的Ships Free over $amount商业尾句，残留明确数值星级、评论数或货币格式报错；历史正文保留合法评分、当时价格、商品名。无语义过滤、目标相似度、摘要或截断；为空或只剩四类遮罩的必需文本导致整批失败。该有限处理不声称穷尽PII，也不承担授权。

模型组件为model/catalog.jsonl、model/tasks.jsonl及仅列这两个文件摘要的model/manifest.json。UTF-8无BOM、显式LF、紧凑键排序JSON；任务按不透明ID排序，S/C及商品按父ID UTF-8字节排序。H按毫秒、父ID字节及稳定完整review JSON排序。C为全目录减全部严格更早原始已见集合。背景从clean整账号排除全部dev/test，再逐任务严格小于T计算三个批准计数。

私有evaluation、task-audit及access-probe与模型组件分离。主记录绑定输入、生产器和各稳定组件摘要，来源路径及时间／环境仅在受信任记录中。私有追溯绑定原始组件摘要、源行引用、JSON pointer、原文及投影摘要、各阶段码点位置及编辑范围。原文本身沿原始组件回查，不复制给模型。无法构造时公开稳定原因及影响数量，细节仅写私有failure记录，不修改资格或部分发布成功。

同版本只有全部来源／配置／生产器／探测摘要及组件字节匹配才复用；损坏或变化返回output_conflict，禁止覆盖。先在项目.tmp构造及验证完整组件，再发布版本目录，最后独占创建主记录。失败没有成功主记录。不同探测或复现使用项目内新空output-root；时间等运行元数据不计稳定字节比较。

access-probe每行恰含session_task_id（64位小写HMAC摘要）、operation、arguments（JSON对象）。可信测试运行器绑定会话；它不是模型可选身份。operation仅model_request、read_resource、invoke_tool：model_request且arguments={}取得该会话实际请求；其余合法挑战均由同一分派器返回{"status":"access_denied"}，拒绝前不检查资源存在性。未知操作、重复键、非法JSON、非有限常量或空探测属于invalid_probe，失败不发布。

受信任加载器只按manifest列名和摘要读取catalog/tasks，再将当前H与C所需商品展开。ModelSession只接白名单对象，内部只有JSON序列化；不拥有文件、索引、网络、shell、评价加载器或模型执行入口。请求仅一个user消息，所有文本为JSON字符串，tools=[]；分派器默认拒绝额外资源、工具、切换角色及跨任务参数。含路径或命令的文字不会产生宿主动作；旧索引及私有哨兵不注册为资源。初版无缓存或旧对话继承。

探测覆盖真实构造／权限分派的API能力范围。它不证明NTFS对Kane拒读，也不证明未来供应商运行器、模型效果或模型token容量。未来调用推荐模型必须复用该构造与分派路径；接入工具、SIM、任意宿主I/O或旧结果必须另经确认和真实验收。

1.0.0首轮因失败明细写入路径未检查目录联接而拒绝验收，产物保留；唯一集中修订为对完整失败路径做同一检查，新增CLI行为19按RED→GREEN。修订版1.0.1复用原32字节密钥与全部已确认语义，新规则版本域使HMAC根ID变化，不改变账号资格或组别。独立验收和代码审查分别保留首轮及修订轮依据，不覆盖旧版。
