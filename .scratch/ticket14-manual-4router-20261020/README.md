# 手动填写与离线检查

在`D:\Work\Codex\Project\Thesis\.secrets\4router.json`第2行的`api_key`空字符串内填写Key。不要把Key写到公开配置或命令行。整个`.secrets/`已被Git忽略，公开示例为`config/4router.credentials.example.json`。不覆盖已存在的凭据文件；不会把凭据内容/长度/摘要写入验收或资源账。

工作目录为`D:\Work\Codex\Project\Thesis`。以下项目命令均显式使用Thesis环境；沿用项目TEMP/TMP与缓存设置，无新依赖：

```powershell
$env:TEMP = "$PWD\.tmp"
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = "$PWD\.conda\pkgs"
conda run -p .\.conda\envs\Thesis python -B fourrouter_probe.py check
```

检查仅输出`api_key_filled`和`local_config_valid`。空Key可以是合法占位（false/true），填入后为true/true；格式无效或文件缺失返回退出码2。这里的valid仅表示本地结构和固定公开参数有效，不证明Key在服务端可用，也不代表实验配置完整。公开模型/地址直接读取原B的`config.draft.json`，分组、费率及预算保持null。

```powershell
conda run -p .\.conda\envs\Thesis python -B fourrouter_probe.py prepare
conda run -p .\.conda\envs\Thesis python -B fourrouter_probe.py probe
```

`prepare`只显示少量PUBLIC虚构输入、一个read_evidence函数和strict JSON Schema的离线请求提案，不读Key、用户、评论或标签。fixture测试已演练原生形状工具调用→固定PUBLIC工具结果→封闭JSON，最多两次外部替身回调，不创建真实推荐或评价。

`probe`是保留的后续启动入口，**目前没有真实sender**，会返回`contract_confirmation_required`，退出码2，实际发送0。没有`--send`或凭据自动放行方式。后续只需集中确认两项合同差异，再补受控sender：

1. 允许独立PUBLIC协议探针不以前置可靠计数为门槛，计数请求上限0；不对未经证实的计数接口探测、重试或修复。
2. 若其他未知信息暂不补充，需另行明确接受该探针未知费用（费用仍null，不能保证费用硬额），批准最多2次Responses生成、其他API=0、并发1、重试0、每次输出上限提案256 token。填写Key本身不算确认。

这两项不修改正式实验的可靠计数、费率和预算合同，也不授权开发或100用户18场景单轮实验。4Router的精确模型权限、工具/Schema支持、usage及请求ID仍未实测；遇到未知reasoning续传或额外输出，当前fixture处理停止，不擅自丢弃或扩展协议框架。
