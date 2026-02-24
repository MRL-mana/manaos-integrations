param(
  [string]$OutDir = "",
  [string]$DefaultBaseUrl = "https://mana.tail370497.ts.net"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\")).Path

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $repoRoot "artifacts\\x280_remote_core_kit"
}

$OutDir = (Resolve-Path (Join-Path $OutDir ".." )).Path + "\\" + (Split-Path $OutDir -Leaf)

if (Test-Path $OutDir) {
  Remove-Item -Recurse -Force $OutDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$srcCheck = Join-Path $repoRoot "scripts\\windows\\check_manaos_remote_core.ps1"
if (!(Test-Path $srcCheck)) {
  throw "Missing: $srcCheck"
}

Copy-Item -Force $srcCheck (Join-Path $OutDir "check_manaos_remote_core.ps1")

$readme = @()
$readme += "X280 Remote Core Kit"
$readme += ""
$readme += "Purpose: Check if X280 can reach ManaOS Remote Core over Tailscale Serve."
$readme += ""
$readme += "1) Ensure Tailscale is connected on X280."
$readme += "2) Run RUN_CHECK.cmd (or run the ps1 directly)."
$readme += ""
$readme += "Default BaseUrl: $DefaultBaseUrl"
$readme += "You can change BaseUrl by editing RUN_CHECK.cmd or running:"
$readme += "  powershell -NoProfile -ExecutionPolicy Bypass -File .\\check_manaos_remote_core.ps1 -BaseUrl https://<name>.ts.net"
$readme += ""
$readme += "Expected: /health => 200 (REQUIRED). /docs may be 404 (optional)."
$readme += ""
$readme | Set-Content -Encoding UTF8 (Join-Path $OutDir "README.txt")

$cmd = @()
$cmd += "@echo off"
$cmd += "setlocal"
$cmd += "set BASEURL=$DefaultBaseUrl"
$cmd += 'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_manaos_remote_core.ps1" -BaseUrl %BASEURL%'
$cmd += "echo."
$cmd += "echo Done."
$cmd += "pause"
$cmd | Set-Content -Encoding ASCII (Join-Path $OutDir "RUN_CHECK.cmd")

# Optional: zip
$zipPath = "$OutDir.zip"
try {
  if (Test-Path $zipPath) { Remove-Item -Force $zipPath -ErrorAction SilentlyContinue }
  Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $zipPath -Force
  Write-Host "[OK] Kit folder: $OutDir" -ForegroundColor Green
  Write-Host "[OK] Kit zip   : $zipPath" -ForegroundColor Green
} catch {
  Write-Host "[OK] Kit folder: $OutDir" -ForegroundColor Green
  Write-Host "[WARN] Zip failed: $($_.Exception.Message)" -ForegroundColor Yellow
}
