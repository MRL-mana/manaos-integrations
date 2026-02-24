param(
  [string]$EntryName = "ManaOS_DockerStack"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"

try {
  if (Test-Path $runKey) {
    Remove-ItemProperty -Path $runKey -Name $EntryName -ErrorAction Stop
    Write-Host "[OK] Run entry removed: $EntryName" -ForegroundColor Green
  } else {
    Write-Host "[SKIP] Run key not found" -ForegroundColor DarkGray
  }
} catch {
  Write-Host "[WARN] Run entry not found or failed to remove: $EntryName" -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor DarkGray
}
