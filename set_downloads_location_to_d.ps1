# Set Windows "Downloads" known folder location to D:\UserData\Downloads (HKCU).
# This avoids needing to replace C:\Users\mana4\Downloads with a junction when it is locked.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\set_downloads_location_to_d.ps1
#

$ErrorActionPreference = "Stop"

$dest = "D:\UserData\Downloads"
if (-not (Test-Path -LiteralPath $dest)) {
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
}

$downloadsGuid = "{374DE290-123F-4565-9164-39C4925E467B}"

$userShell = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
$shell = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Set Downloads location to D:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Destination: $dest"
Write-Host ""

function Upsert-ExpandString($path, $name, $value) {
    try {
        $exists = Get-ItemProperty -Path $path -Name $name -ErrorAction SilentlyContinue
        if ($null -ne $exists) {
            Set-ItemProperty -Path $path -Name $name -Value $value -ErrorAction Stop
        } else {
            New-ItemProperty -Path $path -Name $name -Value $value -PropertyType ExpandString -Force | Out-Null
        }
    } catch {
        # fallback as plain string
        New-ItemProperty -Path $path -Name $name -Value $value -PropertyType String -Force | Out-Null
    }
}

function Upsert-String($path, $name, $value) {
    try {
        $exists = Get-ItemProperty -Path $path -Name $name -ErrorAction SilentlyContinue
        if ($null -ne $exists) {
            Set-ItemProperty -Path $path -Name $name -Value $value -ErrorAction Stop
        } else {
            New-ItemProperty -Path $path -Name $name -Value $value -PropertyType String -Force | Out-Null
        }
    } catch {
        New-ItemProperty -Path $path -Name $name -Value $value -PropertyType String -Force | Out-Null
    }
}

Write-Host "[INFO] Updating registry keys..." -ForegroundColor Yellow
Upsert-ExpandString $userShell $downloadsGuid $dest
Upsert-ExpandString $userShell "Downloads" $dest
Upsert-String $shell $downloadsGuid $dest
Upsert-String $shell "Downloads" $dest

Write-Host "[INFO] Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process explorer.exe

Write-Host ""
Write-Host "[OK] Done. New downloads should go to D:\\UserData\\Downloads" -ForegroundColor Green
Write-Host "Note: Some apps/browsers may have their own download setting." -ForegroundColor Yellow
