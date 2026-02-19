param(
    [string]$TaskName = "ManaOS-CASTLE-EX-Layer2-Nightly",
    [string]$StartTime = "00:30"
)

$ErrorActionPreference = "Stop"

$scriptPath = "C:\Users\mana4\Desktop\manaos_integrations\run_layer2_lora_resume_nightly.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "script not found: $scriptPath"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath"

schtasks /Create /SC DAILY /TN $TaskName /TR $taskRun /ST $StartTime /F | Out-Null
schtasks /Query /TN $TaskName /V /FO LIST
