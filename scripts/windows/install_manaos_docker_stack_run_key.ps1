param(
  [string]$EntryName = "ManaOS_DockerStack",
  [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\")).Path,
  [string]$ComposeFile = "",
  [switch]$RemoveOrphans
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
  $ComposeFile = Join-Path $WorkingDir "docker-compose.yml"
}

$Runner = Join-Path $WorkingDir "scripts\\windows\\run_manaos_docker_stack_service.ps1"
if (!(Test-Path $Runner)) {
  throw "Runner not found: $Runner"
}
if (!(Test-Path $ComposeFile)) {
  throw "Compose file not found: $ComposeFile"
}

$psExe = "$env:WINDIR\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
if (-not (Test-Path $psExe)) {
  $psExe = "powershell.exe"
}

$cmd = '"' + $psExe + '"' +
  ' -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden' +
  ' -File ' + ('"' + $Runner + '"') +
  ' -WorkingDir ' + ('"' + $WorkingDir + '"') +
  ' -ComposeFile ' + ('"' + $ComposeFile + '"')

if ($RemoveOrphans) {
  $cmd += ' -RemoveOrphans'
}

$runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
if (-not (Test-Path $runKey)) {
  New-Item -Path $runKey -Force | Out-Null
}

Set-ItemProperty -Path $runKey -Name $EntryName -Value $cmd -Type String

Write-Host "[OK] Run entry set: $EntryName" -ForegroundColor Green
Write-Host "Value: $cmd" -ForegroundColor DarkGray
