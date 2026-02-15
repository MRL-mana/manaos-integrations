# Check All API Gateways Status
# This script checks the health of all device API Gateways

Write-Host "=== API Gateway Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Device API Gateway endpoints
$devices = @(
    @{
        Name = "ManaOS"
        Endpoint = "http://127.0.0.1:5106/health"
        Type = "Local"
    },
    @{
        Name = "X280"
        Endpoint = "http://100.127.121.20:5120/health"
        Type = "Remote"
    },
    @{
        Name = "Konoha Server"
        Endpoint = "http://100.93.120.33:5106/health"
        Type = "Remote"
    },
    @{
        Name = "Pixel 7"
        Endpoint = "http://100.127.121.20:5122/health"
        Type = "Remote"
    }
)

$results = @()

foreach ($device in $devices) {
    Write-Host "[Checking] $($device.Name)..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri $device.Endpoint -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $status = "OK"
        $statusColor = "Green"
        $details = $response.Content | ConvertFrom-Json | ConvertTo-Json -Compress
    } catch {
        $status = "OFFLINE"
        $statusColor = "Red"
        $details = $_.Exception.Message
    }
    
    $results += @{
        Name = $device.Name
        Status = $status
        Endpoint = $device.Endpoint
        Details = $details
    }
    
    Write-Host "  Status: " -NoNewline
    Write-Host $status -ForegroundColor $statusColor
    Write-Host "  Endpoint: $($device.Endpoint)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host ""

$onlineCount = ($results | Where-Object { $_.Status -eq "OK" }).Count
$offlineCount = ($results | Where-Object { $_.Status -eq "OFFLINE" }).Count

Write-Host "Online: $onlineCount" -ForegroundColor Green
Write-Host "Offline: $offlineCount" -ForegroundColor $(if ($offlineCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

# Detailed results
Write-Host "=== Detailed Results ===" -ForegroundColor Cyan
Write-Host ""

foreach ($result in $results) {
    Write-Host "$($result.Name):" -ForegroundColor White
    Write-Host "  Status: $($result.Status)" -ForegroundColor $(if ($result.Status -eq "OK") { "Green" } else { "Red" })
    Write-Host "  Endpoint: $($result.Endpoint)" -ForegroundColor Gray
    if ($result.Status -eq "OK") {
        Write-Host "  Details: $($result.Details)" -ForegroundColor Gray
    } else {
        Write-Host "  Error: $($result.Details)" -ForegroundColor Red
    }
    Write-Host ""
}

