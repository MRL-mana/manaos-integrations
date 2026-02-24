param(
  [int]$LocalPort = 9502,
  [switch]$Background
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bgFlag = if ($Background) { "--bg" } else { "" }

Write-Host "Enabling Tailscale Serve for localhost:$LocalPort" -ForegroundColor Cyan
if ($bgFlag) {
  & tailscale serve --bg $LocalPort
} else {
  & tailscale serve $LocalPort
}

Write-Host "--- serve status ---" -ForegroundColor Gray
& tailscale serve status
