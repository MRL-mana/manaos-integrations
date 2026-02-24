Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Disabling Tailscale Serve (reset)" -ForegroundColor Yellow
& tailscale serve reset

Write-Host "--- serve status ---" -ForegroundColor Gray
try {
  & tailscale serve status
} catch {
  Write-Host "(no serve config)" -ForegroundColor DarkGray
}
