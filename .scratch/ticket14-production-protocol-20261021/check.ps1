param([Parameter(Mandatory=$true)][string]$Label,[Parameter(ValueFromRemainingArguments=$true)][string[]]$CheckArgs)
$ErrorActionPreference='Stop'
& "$PSScriptRoot/budget.ps1" ($Label+'_before') 10
if($LASTEXITCODE -and $LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& conda run --no-capture-output -p .\.conda\envs\Thesis python -B "$PSScriptRoot/offline_check.py" ('prodproto_'+$Label) @CheckArgs
$taskCode=$LASTEXITCODE
& "$PSScriptRoot/budget.ps1" ($Label+'_after')
exit $taskCode
