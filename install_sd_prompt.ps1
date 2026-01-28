param(
    [string]$InstallDir = "$env:USERPROFILE\\.manaos\\bin"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing sd-prompt..." -ForegroundColor Cyan

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcCmd = Join-Path $repoDir "sd-prompt.cmd"
$srcPs1 = Join-Path $repoDir "sd-prompt.ps1"

if (-not (Test-Path $srcCmd)) { throw "Not found: $srcCmd" }
if (-not (Test-Path $srcPs1)) { throw "Not found: $srcPs1" }

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Copy-Item -Force $srcCmd (Join-Path $InstallDir "sd-prompt.cmd")
Copy-Item -Force $srcPs1 (Join-Path $InstallDir "sd-prompt.ps1")

$current = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrEmpty($current)) { $current = "" }

$parts = $current -split ";" | Where-Object { $_ -and $_.Trim() -ne "" }
if ($parts -notcontains $InstallDir) {
    $new = ($parts + $InstallDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $new, "User")
    Write-Host "Added to User PATH: $InstallDir" -ForegroundColor Green
} else {
    Write-Host "User PATH already contains: $InstallDir" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "- Open a new terminal (recommended)" -ForegroundColor Cyan
Write-Host "- Or log out / log in" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test:" -ForegroundColor Cyan
Write-Host "  sd-prompt \"Beautiful sunset over the ocean\"" -ForegroundColor White
