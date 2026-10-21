param([string]$Label='checkpoint',[double]$Admission=0,[switch]$Closeout)
$ErrorActionPreference='Stop'
$taskRoot='D:\Work\Codex\Project\Thesis'
Set-Location -LiteralPath $taskRoot
$env:TEMP=Join-Path $taskRoot '.tmp'; $env:TMP=$env:TEMP
$env:CONDA_PKGS_DIRS=Join-Path $taskRoot '.conda/pkgs'; $env:PIP_CACHE_DIR=Join-Path $taskRoot '.cache/pip'
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; $env:CONDA_OFFLINE='true'
$taskPackage=Get-Content "$PSScriptRoot/package.json" | ConvertFrom-Json
$taskLedger=Join-Path $taskRoot 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
$taskLast=Get-Content $taskLedger -Tail 1 | ConvertFrom-Json
$taskExcluded=0.0
if(Test-Path "$PSScriptRoot/execution-exclusions.jsonl") {
    $taskExcluded=[double](@(Get-Content "$PSScriptRoot/execution-exclusions.jsonl" | ForEach-Object {$_|ConvertFrom-Json}) | Measure-Object -Property seconds -Sum).Sum
}
$taskElapsed=$taskPackage.bootstrap_upper_seconds+([Diagnostics.Stopwatch]::GetTimestamp()-$taskPackage.start_tick)/$taskPackage.frequency-$taskExcluded
$taskDue=[Math]::Max(0,$taskPackage.inherited_offline_seconds+$taskElapsed-$taskLast.cumulative_seconds)
$taskCumulative=[double]$taskLast.cumulative_seconds+$taskDue
$taskRow=@{label=('sA6_'+$Label); seconds=$taskDue; cumulative_seconds=$taskCumulative; accounting='package_wall_minus_separately_recorded_execution_minus_already_charged_Job_time'; execution_excluded_seconds=$taskExcluded}
$taskRow|ConvertTo-Json -Compress|Add-Content $taskLedger -Encoding utf8
$taskRows=@(Get-Content $taskLedger|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.label -like 'sA6_*'})
$taskWrites=$taskPackage.native_write_upper_bytes+[double]($taskRows|Measure-Object -Property job_write_transfer_bytes -Sum).Sum+[double]($taskRows|Measure-Object -Property guard_write_transfer_bytes -Sum).Sum
foreach($taskDomain in @('.scratch/ticket14-s-120-20261021/A6')) {
    if(Test-Path "$taskDomain/execution-resources.jsonl") {
        $taskWrites += [double](@(Get-Content "$taskDomain/execution-resources.jsonl"|ForEach-Object {$_|ConvertFrom-Json})|Measure-Object -Property job_write_transfer_bytes -Sum).Sum
    }
}
$taskLocalLeft=$taskPackage.package_seconds-($taskCumulative-$taskPackage.inherited_offline_seconds)
$taskGlobalLeft=$taskPackage.offline_limit_seconds-$taskCumulative
$taskRemaining=@{label=$Label; local_left=$taskLocalLeft; global_left=$taskGlobalLeft; write_bytes_left=($taskPackage.write_limit_bytes-$taskWrites); write_upper_bytes=$taskWrites; offline_seconds=$taskCumulative; excluded_execution_seconds=$taskExcluded}
$taskRemaining|ConvertTo-Json -Compress|Add-Content "$PSScriptRoot/resource-checks.jsonl" -Encoding utf8
$taskRemaining|ConvertTo-Json -Compress|Write-Host
$taskReserve=if($Closeout){0}else{$taskPackage.reserve_seconds}
if([Math]::Min($taskLocalLeft,$taskGlobalLeft) -lt $taskReserve+$Admission -or $taskWrites -gt $taskPackage.write_limit_bytes-4194304) {throw 'remaining_budget_requires_stop'}

