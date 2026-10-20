$ErrorActionPreference = 'Stop'
$pfProjectRoot='D:\Work\Codex\Project\Thesis'
$pfBalancePackage=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package.json')|ConvertFrom-Json
$pfBalanceLedger=Join-Path $pfProjectRoot 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
function Check-Remaining([string]$Label,[string]$Phase,[switch]$Closeout) {
    $pfRows=@(Get-Content -LiteralPath $pfBalanceLedger|ForEach-Object {$_|ConvertFrom-Json})
    $pfOwn=@($pfRows|Where-Object {$_.label -like 'seng_*'})
    $pfSeconds=[double]$pfRows[-1].cumulative_seconds
    $pfWrites=[long]($pfOwn|Measure-Object charged_upper_bytes -Sum).Sum+[long]($pfOwn|Measure-Object job_write_transfer_bytes -Sum).Sum+[long]($pfOwn|Measure-Object guard_write_transfer_bytes -Sum).Sum
    $pfRemaining=[ordered]@{label=$Label;phase=$Phase;package_seconds_left=180-($pfSeconds-$pfBalancePackage.inherited_offline_seconds);offline_seconds_left=1800-$pfSeconds;write_bytes_left=134217728-$pfWrites;charged_write_upper_bytes=$pfWrites;accounting='native_operations_already_precharged_conservatively'}
    [IO.File]::AppendAllText((Join-Path $PSScriptRoot 'operation-balances.jsonl'),(($pfRemaining|ConvertTo-Json -Compress)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
    if ($pfRemaining.package_seconds_left -lt 0 -or $pfRemaining.offline_seconds_left -lt 0 -or $pfRemaining.write_bytes_left -lt 0) { throw 'resource_cap_stop' }
    if (-not $Closeout -and ($pfRemaining.package_seconds_left -lt 25 -or $pfRemaining.offline_seconds_left -lt 25 -or $pfRemaining.write_bytes_left -lt 8388608)) { throw 'closeout_only_no_new_work' }
    $pfRemaining|ConvertTo-Json -Compress
}
