param([Parameter(Mandatory=$true)][string]$Label, [Parameter(ValueFromRemainingArguments=$true)][string[]]$GuardArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\Work\Codex\Project\Thesis'
Set-Location -LiteralPath $projectRoot
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = Join-Path $projectRoot '.conda/pkgs'
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache/pip'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$resourcePath = Join-Path $projectRoot 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
$priorSeconds = (Get-Content -Tail 1 -LiteralPath $resourcePath | ConvertFrom-Json).cumulative_seconds
$launchWatch = [Diagnostics.Stopwatch]::StartNew()
$checkOutput = & conda run --no-capture-output -p (Join-Path $projectRoot '.conda/envs/Thesis') python -B '.scratch/ticket12-budget-20261018/diagnostics/run_check.py' $Label @GuardArgs 2>&1
$checkCode = $LASTEXITCODE
$launchWatch.Stop()
$checkOutput | ForEach-Object { if ([string]$_ -notmatch '^\{"accounting": "guard_start_to_child') { [string]$_ } }
$lastResource = Get-Content -Tail 1 -LiteralPath $resourcePath | ConvertFrom-Json
$launcherSeconds = [Math]::Max([double]0, [double]($launchWatch.Elapsed.TotalSeconds - ($lastResource.cumulative_seconds - $priorSeconds)))
$launchRow = @{label=($Label+'_launcher');scope='ticket14-A-offline-integration';seconds=$launcherSeconds;cumulative_seconds=($lastResource.cumulative_seconds+$launcherSeconds);exit_code=$checkCode;accounting='outer_conda_stopwatch_minus_guard_already_charged';provider_requests_sent=0}
[IO.File]::AppendAllText($resourcePath,($launchRow | ConvertTo-Json -Compress)+"`n",[Text.UTF8Encoding]::new($false))
$launchRow | ConvertTo-Json -Compress
exit $checkCode
