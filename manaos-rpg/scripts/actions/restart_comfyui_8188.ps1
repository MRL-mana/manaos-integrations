$ErrorActionPreference = 'Stop'

param(
  [int]$Port = 8188
)

function Get-ListeningPid([int]$p) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction Stop | Select-Object -First 1
    if ($conn) { return [int]$conn.OwningProcess }
  } catch {
    return $null
  }
  return $null
}

$pid = Get-ListeningPid -p $Port
if ($pid) {
  Write-Host "Killing pid=$pid on port=$Port" -ForegroundColor Yellow
  Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
}

Write-Host "Starting ComfyUI (background)" -ForegroundColor Green
pwsh -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\..\..\start_comfyui_local.ps1" -Port $Port -Background
