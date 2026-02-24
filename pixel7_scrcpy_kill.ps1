Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

try {
  Stop-Process -Name scrcpy -Force -ErrorAction SilentlyContinue | Out-Null
} catch {
}

Write-Host 'OK' -ForegroundColor Green
exit 0
