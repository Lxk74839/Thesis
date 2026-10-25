param([switch]$V00Only)
$ErrorActionPreference='Stop'
$condaExe='D:\Work\Anaconda\Scripts\conda.exe'
$thesisEnvironment='D:\Work\Codex\Project\Thesis\.conda\envs\Thesis'
if(-not(Test-Path -LiteralPath $condaExe)){throw '请在运行说明中选择通用Conda环境命令。'}
if(-not(Test-Path -LiteralPath $thesisEnvironment)){throw '未找到Thesis专属环境，请按environment.yml创建。'}
$env:TEMP=Join-Path $PSScriptRoot '.tmp'
$env:TMP=$env:TEMP
$env:CONDA_PKGS_DIRS=Join-Path $PSScriptRoot '.conda-pkgs'
$env:PYTHONUTF8='1'
[void](New-Item -ItemType Directory -Path $env:TEMP -Force)
& $condaExe run --no-capture-output -p $thesisEnvironment python -B (Join-Path $PSScriptRoot 'build_wide_csv.py')
if($LASTEXITCODE -ne 0){throw 'CSV生成失败，未执行重放。'}
$replayArgs=@('run','--no-capture-output','-p',$thesisEnvironment,'python','-B',(Join-Path $PSScriptRoot 'replay.py'))
if(-not $V00Only){$replayArgs+='--all-scenes'}
& $condaExe @replayArgs
if($LASTEXITCODE -ne 0){throw '重放核对失败，请查看实际输出。'}