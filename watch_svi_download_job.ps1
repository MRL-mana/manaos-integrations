param(
    [string]$RemiUrl = "http://127.0.0.1:5050",
    [string]$UnifiedUrl = "http://127.0.0.1:9502",
    [string]$JobId = "",
    [string]$Token = "",
    [int]$PollIntervalSec = 30
)

$ErrorActionPreference = 'Stop'

if (-not $JobId) {
    Write-Host "[watch] Please provide -JobId" -ForegroundColor Red
    exit 1
}

if (-not $Token) {
    try {
        # Try to read from file; if that fails, just proceed (Token may be passed as parameter)
        $tokenFile = Join-Path (Get-Location) 'manaos_integrations' 'logs' 'remi_api_token.txt'
        if (Test-Path $tokenFile) {
            $Token = (Get-Content -Path $tokenFile | Select-Object -First 1).Trim()
        }
    } catch {}
}

if (-not $Token) {
    Write-Host "[watch] No token found. Please provide -Token parameter or ensure remi_api_token.txt exists" -ForegroundColor Red
    exit 1
}

Write-Host "[watch] job_id=$JobId poll_interval=${PollIntervalSec}s" -ForegroundColor Cyan

while ($true) {
    try {
        $uri = "$RemiUrl/api/quick/video/models/download/status?job_id=$([Uri]::EscapeDataString($JobId))"
        $st = Invoke-RestMethod -Uri $uri -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 10
        
        $line = "[$(Get-Date -Format 'HH:mm:ss')] state=$($st.state) role=$($st.role) pct=$($st.percent)%"
        Write-Host $line -ForegroundColor Cyan
        
        if ($st.state -in @('finished', 'failed', 'ok')) {
            Write-Host "[watch] Download $($st.state)" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "[watch] Status error: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds $PollIntervalSec
}

Write-Host "[watch] Checking unified capabilities..." -ForegroundColor Cyan
try {
    $cap = Invoke-RestMethod -Uri "$UnifiedUrl/api/svi/capabilities" -TimeoutSec 10
    $ma = $cap.model_assets
    $missingCount = if ($ma.missing -is [array]) { $ma.missing.Count } else { 0 }
    Write-Host "unified_ok=$($cap.ok) missing_count=$missingCount" -ForegroundColor Green
} catch {
    Write-Host "[watch] Unified check error: $($_.Exception.Message)" -ForegroundColor Yellow
}