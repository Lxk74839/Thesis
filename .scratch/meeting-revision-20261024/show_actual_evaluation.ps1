$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'D:\Work\Codex\Project\Thesis'
$env:TEMP = 'D:\Work\Codex\Project\Thesis\.tmp'
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = 'D:\Work\Codex\Project\Thesis\.conda\pkgs'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Host.UI.RawUI.WindowTitle = 'Thesis Offline Evaluation 20261024'
$Host.UI.RawUI.ForegroundColor = 'White'
$Host.UI.RawUI.BackgroundColor = 'Black'
try {
    $raw = $Host.UI.RawUI
    $buffer = $raw.BufferSize
    $buffer.Width = [Math]::Max(130, $buffer.Width)
    $buffer.Height = [Math]::Max(1000, $buffer.Height)
    $raw.BufferSize = $buffer
    $window = $raw.WindowSize
    $window.Width = [Math]::Min(120, $raw.MaxPhysicalWindowSize.Width)
    $window.Height = [Math]::Min(36, $raw.MaxPhysicalWindowSize.Height)
    $raw.WindowSize = $window
} catch { Write-Host 'Console host uses its existing window dimensions.' }

$meetingOutput = 'D:\Work\Codex\Project\Thesis\reports\组会修订材料_字段详解与多智能体设计_20261024\03_终端截图与真实结果\离线重放'
Write-Host 'Running actual offline replay in the Thesis Conda environment...'
& 'D:\Work\Anaconda\Scripts\conda.exe' run --no-capture-output -p 'D:\Work\Codex\Project\Thesis\.conda\envs\Thesis' python -B 'D:\Work\Codex\Project\Thesis\reports\组会完整材料_商品评论与生命周期_20261024\02_代码与离线运行\replay.py' --all-scenes --results-dir $meetingOutput
if ($LASTEXITCODE -ne 0) { throw "Offline replay failed: $LASTEXITCODE" }
$result = Get-Content -LiteralPath (Join-Path $meetingOutput 'replay-result.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$clock = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$lines = @(
    'THESIS | ACTUAL OFFLINE EVALUATION RESULTS',
    "Completed: $clock (Japan time)",
    '',
    'Source: original Compact experiment, 100 frozen users.',
    'Reused saved REAL model profiles; host ranking was re-executed.',
    'Scope: 18 scenes; preference metrics aggregate 16 V scenes.',
    'Per-user scene mean, then equal-user mean; failed tasks count as zero.',
    '',
    ('{0,-8}{1,12}{2,14}{3,12}{4,10}{5,10}' -f 'METHOD','HR@10','NDCG@10','SUCCESS','FAILED','USERS'),
    ('-' * 66)
)
foreach ($metric in $result.metrics) {
    $lines += ('{0,-8}{1,12:F6}{2,14:F6}{3,12}{4,10}{5,10}' -f $metric.'方法', [double]$metric.'HR@10', [double]$metric.'NDCG@10', $metric.'成功任务数', $metric.'失败任务数', $metric.'独立用户数')
}
$lines += @(
    '',
    ('ALL TASKS: {0} | MATCHED ORIGINAL: {1}/{0}' -f $result.tasks,$result.matched_original_tasks),
    ('STATUS: ok={0}; failed_model={1}' -f $result.statuses.ok,$result.statuses.failed_model),
    ('Local replay seconds: {0:F2}' -f [double]$result.elapsed_seconds),
    ('NEW MODEL API CALLS: {0}' -f $result.new_model_api_calls),
    '',
    'R = rule profile; S = single model profile; M = sequential six-role profile.',
    'No evidence that M is better overall than R or S.',
    'NEW MACRec B0/I1: main comparison NOT COMPLETED; HR/NDCG = N/A.',
    '',
    'This is a real terminal showing a cache-based offline replay.',
    'This is not a fresh model-inference experiment or Fabric deployment.'
)
$lines | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $meetingOutput) '终端指标实际输出.txt') -Encoding UTF8
Clear-Host
foreach ($line in $lines) { Write-Host $line }
