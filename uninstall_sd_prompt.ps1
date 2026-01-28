param(
    [string]$InstallDir = "$env:USERPROFILE\\.manaos\\bin"
)

$ErrorActionPreference = "Stop"

Write-Host "Uninstalling sd-prompt..." -ForegroundColor Cyan

try {
    Remove-Item -Force (Join-Path $InstallDir "sd-prompt.cmd") -ErrorAction SilentlyContinue
    Remove-Item -Force (Join-Path $InstallDir "sd-prompt.ps1") -ErrorAction SilentlyContinue
} catch {
    # 失敗しても続行
}

$current = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrEmpty($current)) { $current = "" }

$parts = $current -split ";" | Where-Object { $_ -and $_.Trim() -ne "" }
$parts = $parts | Where-Object { $_ -ne $InstallDir }

[Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "User")
Write-Host "Removed from User PATH: $InstallDir" -ForegroundColor Green

Write-Host "Done. Open a new terminal to apply changes." -ForegroundColor Cyan
