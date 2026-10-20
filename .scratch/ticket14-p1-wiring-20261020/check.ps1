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
$prior = [double](Get-Content -LiteralPath $ledgerPath -Tail 1 | ConvertFrom-Json).cumulative_seconds
if($prior-1337.2683664001365 -ge 240){throw 'P1_wiring_closeout_required'}
$hashes = @{}
foreach($source in @('provider_fourrouter.py','model_adapter.py','provider_openai.py','recommendation_runner.py','experiment_runner.py','p1_runtime.py','fourrouter_probe.py','tests/test_p1_wiring.py')){if(Test-Path -LiteralPath $source){$hashes[$source]=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()}}
$watch = [Diagnostics.Stopwatch]::StartNew()
$result = & conda run --no-capture-output -p (Join-Path $projectRoot '.conda/envs/Thesis') python -B '.scratch/ticket12-budget-20261018/diagnostics/run_check.py' $Label @CheckArgs 2>&1
$code = $LASTEXITCODE
$watch.Stop()
$result|ForEach-Object{if([string]$_ -notmatch '^\{"accounting": "guard_start_to_child'){[string]$_}}
$last = Get-Content -LiteralPath $ledgerPath -Tail 1|ConvertFrom-Json
$extra = [Math]::Max([double]0,[double]($watch.Elapsed.TotalSeconds-($last.cumulative_seconds-$prior)))
$row = @{label=($Label+'_launcher');scope='ticket14-P1-wiring-offline';seconds=$extra;cumulative_seconds=([double]$last.cumulative_seconds+$extra);exit_code=$code;accounting='outer_conda_stopwatch_minus_existing_Job_guard';source_sha256=$hashes;provider_requests_sent=0}
[IO.File]::AppendAllText($ledgerPath,($row|ConvertTo-Json -Compress)+"`n",[Text.UTF8Encoding]::new($false))
foreach($source in $hashes.Keys){if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hashes[$source]){throw 'source_changed_during_check'}}
$row|ConvertTo-Json -Compress
exit $code
