# デバイスAPI Gateway起動確認スクリプト

# Auto-admin check (optional - will continue if admin elevation fails)
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== デバイスAPI Gateway起動確認 ===" -ForegroundColor Cyan
Write-Host ""

function Get-Pixel7ApiEndpoint {
    $ip = if ($env:PIXEL7_API_HOST) {
        $env:PIXEL7_API_HOST
    } elseif ($env:PIXEL7_TAILSCALE_IP) {
        $env:PIXEL7_TAILSCALE_IP
    } elseif ($env:PIXEL7_IP) {
        $env:PIXEL7_IP
    } else {
        $cfg = Join-Path $PSScriptRoot 'adb_automation_config.json'
        if (Test-Path $cfg) {
            try {
                $o = Get-Content -Raw -Encoding UTF8 $cfg | ConvertFrom-Json
                if ($o.device_ip) { [string]$o.device_ip } else { '100.84.2.125' }
            } catch {
                '100.84.2.125'
            }
        } else {
            '100.84.2.125'
        }
    }

    $port = if ($env:PIXEL7_API_PORT) { $env:PIXEL7_API_PORT } else { '5122' }
    return "http://${ip}:${port}/health"
}

$devices = @(
    @{ Name = "X280"; Endpoint = "http://100.127.121.20:5120/health"; Script = "x280_api_gateway.py" }
    @{ Name = "Konoha Server"; Endpoint = "http://100.93.120.33:5106/health"; Script = "N/A" }
    @{ Name = "Pixel 7"; Endpoint = (Get-Pixel7ApiEndpoint); Script = "pixel7_api_gateway.py" }
)

$results = @()

foreach ($device in $devices) {
    Write-Host "[$($device.Name)] 確認中..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri $device.Endpoint -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ オンライン" -ForegroundColor Green
            $results += @{
                Name = $device.Name
                Status = "Online"
                Endpoint = $device.Endpoint
            }
        } else {
            Write-Host "  ⚠️  応答異常 (HTTP $($response.StatusCode))" -ForegroundColor Yellow
            $results += @{
                Name = $device.Name
                Status = "Error"
                Endpoint = $device.Endpoint
            }
        }
    } catch {
        Write-Host "  ❌ オフライン" -ForegroundColor Red
        Write-Host "    → API Gatewayが起動していない可能性があります" -ForegroundColor Gray
        if ($device.Script -ne "N/A") {
            Write-Host "    → 起動方法: 該当デバイスで $($device.Script) を実行" -ForegroundColor Gray
        }
        $results += @{
            Name = $device.Name
            Status = "Offline"
            Endpoint = $device.Endpoint
            Script = $device.Script
        }
    }
}

Write-Host ""
Write-Host "=== 確認結果サマリー ===" -ForegroundColor Cyan
$onlineCount = ($results | Where-Object { $_.Status -eq "Online" }).Count
$totalCount = $results.Count

Write-Host "オンライン: $onlineCount / $totalCount" -ForegroundColor $(if ($onlineCount -eq $totalCount) { "Green" } else { "Yellow" })

if ($onlineCount -lt $totalCount) {
    Write-Host ""
    Write-Host "オフラインデバイスの起動方法:" -ForegroundColor Yellow
    foreach ($result in $results) {
        if ($result.Status -eq "Offline") {
            if ($result.PSObject.Properties.Name -contains "Script" -and $result.Script -ne "N/A") {
                Write-Host "  - $($result.Name): $($result.Script)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host ""

