param(
    [string]$PixelSerial = "",
    [string]$PixelAdbTcp = "100.84.2.125:5555",
    [switch]$SkipAdbConnect,
    [switch]$SkipOpenWebUIStart,
    [switch]$SkipImport
)

$ErrorActionPreference = "Stop"

function Resolve-AdbExecutable {
    $candidates = @()
    $cmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        $candidates += $cmd.Source
    }

    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\adb.exe")
        $candidates += (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe")
    }
    $candidates += "C:\\Android\\platform-tools\\adb.exe"
    $candidates += "C:\\platform-tools\\adb.exe"
    $candidates += "C:\\adb\\adb.exe"

    try {
        Get-ChildItem "C:\\Users" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $candidates += (Join-Path $_.FullName "AppData\Local\Microsoft\WinGet\Links\adb.exe")
            $candidates += (Join-Path $_.FullName "AppData\Local\Android\Sdk\platform-tools\adb.exe")
            $winGetPackages = Join-Path $_.FullName "AppData\Local\Microsoft\WinGet\Packages"
            if (Test-Path $winGetPackages) {
                Get-ChildItem $winGetPackages -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                    $candidates += (Join-Path $_.FullName "platform-tools\adb.exe")
                }
            }
        }
    }
    catch {
    }

    foreach ($path in $candidates | Select-Object -Unique) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Get-ActiveDevice([string]$preferred) {
    if ($null -eq $script:AdbExe) { return $null }
    $lines = & $script:AdbExe devices | Select-Object -Skip 1
    $devices = @()
    foreach ($line in $lines) {
        if (-not $line) { continue }
        if ($line -match '^([^\s]+)\s+device\s*$') {
            $devices += $Matches[1]
        }
    }
    if ($devices.Count -eq 0) { return $null }
    if (-not [string]::IsNullOrWhiteSpace($preferred) -and ($devices -contains $preferred)) {
        return $preferred
    }
    return $devices[0]
}

Write-Host "=== Pixel7 Minimal Quick Setup ===" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$startScript = Join-Path $root "start_openwebui_tailscale.ps1"
$syncScript = Join-Path $root "pixel7_sync_openwebui_shortcut.ps1"
$minimalConfig = Join-Path $root "remi_android_shortcuts_minimal.json"

if (-not (Test-Path $syncScript)) { throw "Not found: $syncScript" }
if (-not (Test-Path $minimalConfig)) { throw "Not found: $minimalConfig" }

if (-not $SkipOpenWebUIStart) {
    if (-not (Test-Path $startScript)) { throw "Not found: $startScript" }
    Write-Host "[1/4] Start OpenWebUI + Tailscale" -ForegroundColor Yellow
    powershell -NoProfile -ExecutionPolicy Bypass -File $startScript -InvocationSource pixel7_minimal_quick
    if ($LASTEXITCODE -ne 0) {
        throw "OpenWebUI start failed (exit=$LASTEXITCODE). Ensure Docker Desktop is running, then retry."
    }
}
else {
    Write-Host "[1/4] Skip OpenWebUI start (-SkipOpenWebUIStart)" -ForegroundColor DarkYellow
}

Write-Host "[2/4] Check ADB device" -ForegroundColor Yellow
$script:AdbExe = Resolve-AdbExecutable
if ($null -eq $script:AdbExe) {
    Write-Host "ADB not found. Will update config locally only." -ForegroundColor Yellow
}
else {
    & $script:AdbExe start-server | Out-Null
}

$active = Get-ActiveDevice $PixelSerial
if ($null -eq $active -and $null -ne $script:AdbExe -and -not $SkipAdbConnect -and -not [string]::IsNullOrWhiteSpace($PixelAdbTcp)) {
    Write-Host "ADB not connected. Try Wi-Fi ADB connect: $PixelAdbTcp" -ForegroundColor DarkYellow
    try {
        $out = & $script:AdbExe connect $PixelAdbTcp 2>&1
        if ($out) { Write-Host $out }
    } catch {
        Write-Host "adb connect failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
    $active = Get-ActiveDevice $PixelSerial
}

if ($null -ne $active) {
    Write-Host "ADB device: $active" -ForegroundColor Green
}
else {
    Write-Host "No ADB device (sync will still update local JSON)." -ForegroundColor Yellow
    if ($null -ne $script:AdbExe) {
        try {
            $devices = & $script:AdbExe devices 2>&1
            if ($devices) { Write-Host $devices }
            if (($devices -join "`n") -match "\sunauthorized\s*") {
                Write-Host "ADB device is unauthorized. Unlock Pixel 7 and tap 'Allow USB debugging'." -ForegroundColor Yellow
            }
        } catch {
        }
    }
}

Write-Host "[3/4] Sync minimal shortcut config + push + open import" -ForegroundColor Yellow
if ($SkipImport) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncScript -ConfigPath $minimalConfig
}
else {
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncScript -ConfigPath $minimalConfig -OpenImport
}

Write-Host "[4/4] What to pin on Pixel home" -ForegroundColor Yellow
Write-Host "- 📊 Remi Status" -ForegroundColor Gray
Write-Host "- 🧹 Clear VRAM" -ForegroundColor Gray
Write-Host "- 🚨 Emergency Stop" -ForegroundColor Gray
Write-Host "- OpenWebUI (HTTPS)" -ForegroundColor Gray

Write-Host "Done." -ForegroundColor Green
