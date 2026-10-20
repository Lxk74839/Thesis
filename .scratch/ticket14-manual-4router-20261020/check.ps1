param([Parameter(Mandatory=$true)][string]$Label, [Parameter(ValueFromRemainingArguments=$true)][string[]]$CheckArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\Work\Codex\Project\Thesis'
Set-Location -LiteralPath $projectRoot
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = Join-Path $projectRoot '.conda/pkgs'
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache/pip'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$ledgerPath = Join-Path $projectRoot 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
$prior = (Get-Content -Tail 1 -LiteralPath $ledgerPath | ConvertFrom-Json).cumulative_seconds
if ($prior - 1137.4871598001369 -ge 240) {throw 'manual_preparation_closeout_required'}
$before = @{}
foreach ($source in @('fourrouter_probe.py','tests/test_fourrouter_probe.py')) {if(Test-Path -LiteralPath $source){$before[$source]=(Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()}}
$watch = [Diagnostics.Stopwatch]::StartNew()
$result = & conda run --no-capture-output -p (Join-Path $projectRoot '.conda/envs/Thesis') python -B '.scratch/ticket12-budget-20261018/diagnostics/run_check.py' $Label @CheckArgs 2>&1
$checkCode = $LASTEXITCODE
$watch.Stop()
$result | ForEach-Object {if([string]$_ -notmatch '^\{"accounting": "guard_start_to_child'){[string]$_}}
$last = Get-Content -Tail 1 -LiteralPath $ledgerPath | ConvertFrom-Json
$extra = [Math]::Max([double]0,[double]($watch.Elapsed.TotalSeconds-($last.cumulative_seconds-$prior)))
$row = @{label=($Label+'_launcher');scope='ticket14-manual-preparation-only';seconds=$extra;cumulative_seconds=($last.cumulative_seconds+$extra);exit_code=$checkCode;accounting='outer_conda_stopwatch_minus_existing_Job_guard';source_sha256=$before;provider_requests_sent=0}
[IO.File]::AppendAllText($ledgerPath,($row | ConvertTo-Json -Compress)+"`n",[Text.UTF8Encoding]::new($false))
foreach($source in $before.Keys){if((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant() -ne $before[$source]){throw 'manual_source_changed_during_check'}}
$row | ConvertTo-Json -Compress
exit $checkCode
