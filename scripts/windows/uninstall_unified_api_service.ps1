param(
  [string]$ServiceName = "ManaOSUnifiedAPI",
  [string]$NssmExe = "nssm"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Stopping service (if running): $ServiceName"
try { & $NssmExe stop $ServiceName } catch {}

Write-Host "Removing service: $ServiceName"
& $NssmExe remove $ServiceName confirm

Write-Host "Done."

