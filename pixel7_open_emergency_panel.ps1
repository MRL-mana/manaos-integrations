param(
    [string]$Serial = "",
    [string]$Url = "http://100.73.247.100:9502/emergency",
    [string]$BrowserPackage = "com.android.chrome"
)

$ErrorActionPreference = "SilentlyContinue"

$PREFERRED_TCP = "100.84.2.125:5555"

function Get-ActiveDevice([string]$preferred) {
    $lines = adb devices | Select-Object -Skip 1
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
    if ($devices -contains $PREFERRED_TCP) { return $PREFERRED_TCP }
    $tcp = $devices | Where-Object { $_ -like '*:*' } | Select-Object -First 1
    if ($tcp) { return $tcp }
    return $devices[0]
}

adb start-server | Out-Null

$device = Get-ActiveDevice $Serial
if (-not $device) {
    Write-Host "No adb device found. Connect Pixel (USB) or enable Wi-Fi ADB." -ForegroundColor Red
    exit 1
}

Write-Host "Using adb device: $device" -ForegroundColor Gray

# Wake screen (unlock remains manual if PIN/biometric is enabled)
adb -s $device shell input keyevent 224 | Out-Null
Start-Sleep -Milliseconds 400

if (-not $Url) {
    $Url = $env:MANAOS_EMERGENCY_URL
}
if (-not $Url) {
    $Url = "http://100.73.247.100:9502/emergency"
}

Write-Host "Opening emergency panel: $Url" -ForegroundColor Cyan

# Try explicit browser package first
adb -s $device shell "am start -a android.intent.action.VIEW -d '$Url' $BrowserPackage" | Out-Null
Start-Sleep -Milliseconds 600

# Fallback: default handler
adb -s $device shell "am start -a android.intent.action.VIEW -d '$Url'" | Out-Null

Write-Host "Done." -ForegroundColor Green
