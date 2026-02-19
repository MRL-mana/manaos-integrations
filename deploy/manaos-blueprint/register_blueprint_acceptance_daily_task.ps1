param(
    [string]$TaskName = "ManaOS-Blueprint-Acceptance-Daily",
    [string]$StartTime = "07:30",
    [string]$BaseDomain = "mrl-mana.com"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pipelineScript = Join-Path $scriptDir "run_blueprint_full_pipeline.ps1"

if (-not (Test-Path $pipelineScript)) {
    throw "pipeline script not found: $pipelineScript"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"$pipelineScript\" -BaseDomain \"$BaseDomain\" -StartIfNeeded"

schtasks /Create /SC DAILY /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
schtasks /Query /TN $TaskName /V /FO LIST
