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
$env:CONDA_OFFLINE = 'true'
$packagePath = Join-Path $PSScriptRoot 'package.json'
$package = Get-Content -LiteralPath $packagePath | ConvertFrom-Json
if ($Label -notlike 'p1freeze_*') { throw 'wrong_fix_package_label' }
$ledgerPath = Join-Path $projectRoot 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
$checksPath = Join-Path $PSScriptRoot 'resource-checks.jsonl'
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Record-Remaining([string]$phase) {
    $rows = @(Get-Content -LiteralPath $ledgerPath | ForEach-Object { $_ | ConvertFrom-Json })
    $own = @($rows | Where-Object { $_.label -like 'p1freeze_*' })
    $seconds = [double]$rows[-1].cumulative_seconds
    $writes = [double]($own | Measure-Object -Property charged_upper_bytes -Sum).Sum +
        [double]($own | Measure-Object -Property job_write_transfer_bytes -Sum).Sum +
        [double]($own | Measure-Object -Property guard_write_transfer_bytes -Sum).Sum
    $remaining = [ordered]@{label=$Label; phase=$phase; package_seconds_left=$package.package_limit_seconds-($seconds-$package.inherited_offline_seconds); offline_seconds_left=$package.offline_limit_seconds-$seconds; write_bytes_left=$package.write_limit_bytes-$writes; charged_write_upper_bytes=$writes; provider_requests_sent=0}
    [IO.File]::AppendAllText($checksPath,(($remaining | ConvertTo-Json -Compress)+[Environment]::NewLine),$utf8)
    $remaining | ConvertTo-Json -Compress | Write-Host
    return $remaining
}
$before = Record-Remaining 'before'
if ($before.package_seconds_left -lt $package.test_admission_seconds+$package.closeout_reserve_seconds -or
    $before.offline_seconds_left -lt $package.test_admission_seconds+$package.closeout_reserve_seconds -or
    $before.write_bytes_left -lt $package.test_admission_write_bytes+$package.closeout_reserve_bytes) { throw 'test_cannot_fit_with_closeout' }
if ($Label -like 'p1freeze_live_*' -and ($before.package_seconds_left -lt $package.execution_admission_seconds+$package.closeout_reserve_seconds -or $before.offline_seconds_left -lt $package.execution_admission_seconds+$package.closeout_reserve_seconds -or $before.write_bytes_left -lt $package.execution_admission_write_bytes+$package.closeout_reserve_bytes)) { throw 'execution_cannot_fit_with_closeout' }
$prior = [double](Get-Content -LiteralPath $ledgerPath -Tail 1 | ConvertFrom-Json).cumulative_seconds
$hashes = @{}
foreach ($source in @('p1_runtime.py','p1_storage.py','experiment_runner.py','recommendation_runner.py','tests/test_p1_frozen_preflight.py','tests/test_p1_r_once.py','.scratch/ticket14-r-frozen-preflight-20261020/run_once.py','.scratch/ticket14-r-frozen-preflight-20261020/r.config.json')) { if (Test-Path -LiteralPath $source) { $hashes[$source]=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() } }
$watch = [Diagnostics.Stopwatch]::StartNew()
$result = & conda run --no-capture-output -p (Join-Path $projectRoot '.conda/envs/Thesis') python -B '.scratch/ticket12-budget-20261018/diagnostics/run_check.py' $Label @CheckArgs 2>&1
$code = $LASTEXITCODE
$watch.Stop()
$result | ForEach-Object { if ([string]$_ -notmatch '^\{"accounting": "guard_start_to_child') { [string]$_ } }
$last = Get-Content -LiteralPath $ledgerPath -Tail 1 | ConvertFrom-Json
if ($last.label -ne $Label) { throw 'guard_accounting_not_settled' }
$extra = [Math]::Max([double]0,[double]($watch.Elapsed.TotalSeconds-($last.cumulative_seconds-$prior)))
$row = @{label=($Label+'_launcher'); scope='ticket14-frozen-R-preflight-retry-once'; seconds=$extra; cumulative_seconds=([double]$last.cumulative_seconds+$extra); exit_code=$code; accounting='outer_conda_stopwatch_minus_existing_Job_guard'; source_sha256=$hashes; provider_requests_sent=0}
[IO.File]::AppendAllText($ledgerPath,(($row | ConvertTo-Json -Compress)+[Environment]::NewLine),$utf8)
$after = Record-Remaining 'after'
foreach ($source in $hashes.Keys) { if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hashes[$source]) { throw 'source_changed_during_check' } }
if ($after.package_seconds_left -lt $package.closeout_reserve_seconds -or $after.offline_seconds_left -lt $package.closeout_reserve_seconds -or $after.write_bytes_left -lt $package.closeout_reserve_bytes) { throw 'closeout_required_no_more_tests' }
exit $code
