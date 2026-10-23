[CmdletBinding()]
param(
    [ValidateSet('Status', 'Start', 'Resume', 'Stop', 'Worker', 'BeginDevelopment', 'EndDevelopment')]
    [string]$Action = 'Status',
    [string]$SessionDir,
    [switch]$ConfirmLive
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $SessionDir) {
    $SessionDir = Join-Path $projectRoot 'data\recommendation-runtime-audit\macrec-agri-dev-task16'
}
$SessionDir = [IO.Path]::GetFullPath($SessionDir)
$condaPath = 'D:\Work\Anaconda\Scripts\conda.exe'
$environmentPath = Join-Path $projectRoot '.conda\envs\Thesis'
$controller = Join-Path $projectRoot 'task16_control.py'
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
$env:CONDA_PKGS_DIRS = Join-Path $projectRoot '.conda\pkgs'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath $projectRoot

function Invoke-Control([string]$ControlAction) {
    $controlArgs = @('run', '--no-capture-output', '-p', $environmentPath,
        'python', '-B', $controller, $ControlAction, '--session', $SessionDir)
    $lines = & $condaPath @controlArgs
    $returnCode = $LASTEXITCODE
    $payload = $lines -join [Environment]::NewLine
    if ($returnCode -ne 0) { Write-Output $payload; exit $returnCode }
    return ($payload | ConvertFrom-Json)
}

if ($Action -in @('Start', 'Resume')) {
    $state = Invoke-Control 'status'
    if (-not $state.ready_for_execution) {
        @{status='rejected';reason='task16_live_not_ready';session=$SessionDir} |
            ConvertTo-Json -Compress
        exit 2
    }
    if ($state.worker_active -or $state.status -eq 'complete') {
        $state | ConvertTo-Json -Depth 12 -Compress
        exit 0
    }
    if ($state.mode -eq 'live' -and -not $ConfirmLive -and
            -not (Test-Path -LiteralPath (Join-Path $SessionDir 'authorization.json'))) {
        @{status='rejected';reason='task16_confirm_live_required'} | ConvertTo-Json -Compress
        exit 2
    }
    $logDirectory = Join-Path $SessionDir 'logs'
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $launchArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Action Worker -SessionDir "{1}"' -f
        $PSCommandPath, $SessionDir
    if ($ConfirmLive) { $launchArgs += ' -ConfirmLive' }
    $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $launchArgs -WindowStyle Hidden -PassThru `
        -WorkingDirectory $projectRoot
    @{status='launched';supervisor_pid=$process.Id;session=$SessionDir;
        original_deadline=$state.deadline_utc} | ConvertTo-Json -Compress
    exit 0
}

if ($Action -eq 'Worker') {
    $logDirectory = Join-Path $SessionDir 'logs'
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $launchId = [Guid]::NewGuid().ToString('N')
    $workerArgs = @('run', '--no-capture-output', '-p', $environmentPath,
        'python', '-B', $controller, 'start', '--session', $SessionDir)
    if ($ConfirmLive) { $workerArgs += '--confirm-live' }
    & $condaPath @workerArgs 1> (Join-Path $logDirectory "$launchId.stdout") `
        2> (Join-Path $logDirectory "$launchId.stderr")
    exit $LASTEXITCODE
}

$controlAction = switch ($Action) {
    'BeginDevelopment' { 'development-begin' }
    'EndDevelopment' { 'development-end' }
    default { $Action.ToLowerInvariant() }
}
Invoke-Control $controlAction | ConvertTo-Json -Depth 12 -Compress
