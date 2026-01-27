param(
  [string]$ServiceName = "ManaOSUnifiedAPI",
  [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path,
  [string]$PythonExe = "",
  [string]$NssmExe = "nssm"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

$Runner = Join-Path $WorkingDir "run_unified_api_server_prod.py"
if (!(Test-Path $Runner)) {
  throw "Runner not found: $Runner"
}

Write-Host "Installing service: $ServiceName"
Write-Host "WorkingDir: $WorkingDir"
Write-Host "PythonExe: $PythonExe"
Write-Host "Runner: $Runner"

# Create service
& $NssmExe install $ServiceName $PythonExe $Runner
& $NssmExe set $ServiceName AppDirectory $WorkingDir
& $NssmExe set $ServiceName Start SERVICE_AUTO_START

# Logs
$LogDir = Join-Path $WorkingDir "logs\\service"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
& $NssmExe set $ServiceName AppStdout (Join-Path $LogDir "unified_api_stdout.log")
& $NssmExe set $ServiceName AppStderr (Join-Path $LogDir "unified_api_stderr.log")
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateOnline 1
& $NssmExe set $ServiceName AppRotateSeconds 86400

Write-Host "Done. Start with: nssm start $ServiceName"

