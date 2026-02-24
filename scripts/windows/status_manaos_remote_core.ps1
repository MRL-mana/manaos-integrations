Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "=== ManaOS Remote Core Status ===" -ForegroundColor Cyan

# Unified API (local)
try {
  $h = Invoke-RestMethod "http://127.0.0.1:9502/health" -TimeoutSec 3
  Write-Host "[OK] Unified API local /health" -ForegroundColor Green
} catch {
  Write-Host "[NG] Unified API local /health" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor DarkGray
}

# Tailscale IP
$tailscaleIP = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue |
  Sort-Object -Property InterfaceMetric, SkipAsSource |
  Select-Object -First 1 -ExpandProperty IPAddress

if ($tailscaleIP) {
  Write-Host "[OK] Tailscale IP: $tailscaleIP" -ForegroundColor Green
} else {
  Write-Host "[WARN] Tailscale IP not found (not connected?)" -ForegroundColor Yellow
}

# Tailscale Serve
try {
  $serve = (& tailscale serve status | Out-String).Trim()
  if ($serve) {
    Write-Host "--- tailscale serve status ---" -ForegroundColor Gray
    $serve | Write-Host
  } else {
    Write-Host "[INFO] tailscale serve: (no output)" -ForegroundColor DarkGray
  }
} catch {
  Write-Host "[WARN] tailscale serve not available" -ForegroundColor Yellow
}

# Run key autostart
$runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
$entry = "ManaOS_DockerStack"
try {
  $v = (Get-ItemProperty -Path $runKey -Name $entry -ErrorAction Stop).$entry
  Write-Host "[OK] Run key autostart present: $entry" -ForegroundColor Green
  Write-Host $v -ForegroundColor DarkGray
} catch {
  Write-Host "[INFO] Run key autostart not set: $entry" -ForegroundColor DarkGray
}

# NSSM service (optional)
try {
  $svc = Get-Service -Name "ManaOSDockerStack" -ErrorAction SilentlyContinue
  if ($svc) {
    Write-Host "[OK] NSSM service exists: ManaOSDockerStack ($($svc.Status))" -ForegroundColor Green
  } else {
    Write-Host "[INFO] NSSM service not installed: ManaOSDockerStack" -ForegroundColor DarkGray
  }
} catch {
}
