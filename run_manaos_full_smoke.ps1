$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$results = [ordered]@{}

function Get-CompactLabel {
    param(
        [string]$Text,
        [int]$MaxLength = 24
    )

    if ([string]::IsNullOrEmpty($Text)) {
        return ""
    }
    if ($Text.Length -le $MaxLength) {
        return $Text
    }
    if ($MaxLength -le 1) {
        return $Text.Substring(0, 1)
    }
    return $Text.Substring(0, $MaxLength - 1) + "…"
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    try {
        & $Action
        $results[$Name] = $true
        Write-Host "[OK] $Name" -ForegroundColor Green
    }
    catch {
        $results[$Name] = $false
        Write-Host "[NG] ${Name}: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Test-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5
    )

    try {
        $null = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Ensure-ComfyUIReady {
    param(
        [int]$WaitSec = 120
    )

    $healthUrl = "http://127.0.0.1:8188/system_stats"
    if (Test-HttpOk -Url $healthUrl -TimeoutSec 5) {
        Write-Host "[OK] ComfyUI already healthy on :8188" -ForegroundColor Green
        return
    }

    $starter = Join-Path $workspace "start_comfyui_local.ps1"
    if (-not (Test-Path $starter)) {
        throw "ComfyUI starter script not found: $starter"
    }

    Write-Host "[INFO] ComfyUI is not running; starting automatically..." -ForegroundColor Yellow
    powershell -NoProfile -ExecutionPolicy Bypass -File $starter -Background | Out-Host

    $deadline = (Get-Date).AddSeconds($WaitSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $healthUrl -TimeoutSec 5) {
            Write-Host "[OK] ComfyUI recovered on :8188" -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "ComfyUI failed to become healthy on :8188"
}

function Ensure-DockerBestEffort {
    param(
        [int]$WaitSec = 45
    )

    try {
        docker version *> $null
        return $true
    }
    catch {
    }

    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Write-Host "[INFO] Docker is not ready; starting Docker Desktop..." -ForegroundColor Yellow
        Start-Process -FilePath $dockerDesktop | Out-Null
    }
    else {
        Write-Host "[WARN] Docker Desktop not found; skip OpenWebUI auto-start" -ForegroundColor Yellow
        return $false
    }

    $deadline = (Get-Date).AddSeconds($WaitSec)
    while ((Get-Date) -lt $deadline) {
        try {
            docker version *> $null
            Write-Host "[OK] Docker became ready" -ForegroundColor Green
            return $true
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    Write-Host "[WARN] Docker did not become ready within ${WaitSec}s; skip OpenWebUI auto-start" -ForegroundColor Yellow
    return $false
}

function Start-OpenWebUIDeferredBootstrap {
    param(
        [int]$MaxWaitSec = 600
    )

    $composeFile = Join-Path $workspace "docker-compose.always-ready-llm.yml"
    if (-not (Test-Path $composeFile)) {
        Write-Host "[WARN] Deferred OpenWebUI bootstrap skipped (compose not found)" -ForegroundColor Yellow
        return
    }

    $logsDir = Join-Path $workspace "logs"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $logPath = Join-Path $logsDir ("openwebui_deferred_bootstrap_{0}.log" -f $stamp)

    $bootstrapCmd = @"


$ErrorActionPreference = 'Continue'
$deadline = (Get-Date).AddSeconds($MaxWaitSec)
while ((Get-Date) -lt $deadline) {
    try {
        docker version *> `$null
        docker compose -f '$composeFile' up -d openwebui *> `$null
        try {
            Invoke-RestMethod -Uri 'http://127.0.0.1:3001/' -Method Get -TimeoutSec 5 -ErrorAction Stop | Out-Null
            Write-Output "[OK] OpenWebUI deferred bootstrap completed"
            exit 0
        }
        catch {
        }
    }
    catch {
    }
    Start-Sleep -Seconds 5
}
Write-Output "[WARN] OpenWebUI deferred bootstrap timeout"
exit 1
"@

    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $bootstrapCmd
    ) -RedirectStandardOutput $logPath -RedirectStandardError $logPath -WindowStyle Minimized | Out-Null

    Write-Host "[INFO] Deferred OpenWebUI bootstrap started: $logPath" -ForegroundColor Gray
}

function Ensure-OpenWebUIBestEffort {
    param(
        [int]$WaitSec = 90
    )

    $healthUrl = "http://127.0.0.1:3001/"
    if (Test-HttpOk -Url $healthUrl -TimeoutSec 5) {
        Write-Host "[OK] OpenWebUI already reachable on :3001" -ForegroundColor Green
        return
    }

    if (-not (Ensure-DockerBestEffort -WaitSec 45)) {
        Start-OpenWebUIDeferredBootstrap -MaxWaitSec 600
        return
    }

    $composeFile = Join-Path $workspace "docker-compose.always-ready-llm.yml"
    if (-not (Test-Path $composeFile)) {
        Write-Host "[WARN] OpenWebUI compose file not found: $composeFile" -ForegroundColor Yellow
        return
    }

    Write-Host "[INFO] OpenWebUI is not running; attempting docker compose up..." -ForegroundColor Yellow
    try {
        $composeOut = docker compose -f $composeFile up -d openwebui 2>&1
        if ($composeOut) {
            $composeOut | Out-Host
        }
    }
    catch {
        Write-Host "[WARN] OpenWebUI auto-start failed: $($_.Exception.Message)" -ForegroundColor Yellow
        return
    }

    $deadline = (Get-Date).AddSeconds($WaitSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $healthUrl -TimeoutSec 5) {
            Write-Host "[OK] OpenWebUI recovered on :3001" -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 2
    }

    Write-Host "[WARN] OpenWebUI did not become reachable on :3001 (continuing)" -ForegroundColor Yellow
}

Invoke-Step -Name "ManaOS Core Health" -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ensure_optional_services.ps1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Optional services recovery failed (exit=$LASTEXITCODE)"
    }

    python .\check_services_health.py | Out-Host
}

Invoke-Step -Name "OpenAI Router Models" -Action {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/models" -Method Get -TimeoutSec 5
    if (-not $models.data) {
        throw "No models returned"
    }
    $modelIds = @($models.data | ForEach-Object { $_.id })
    if (-not ($modelIds -contains "auto-local")) {
        throw "Required model 'auto-local' is not available"
    }
    $models.data | Select-Object -First 5 id | Format-Table -AutoSize | Out-Host
}

Invoke-Step -Name "auto-local Chat" -Action {
    $chatLines = powershell -NoProfile -ExecutionPolicy Bypass -File .\test_auto_local_chat.ps1 -RequestTimeoutSec 360 -MaxRetries 4 -WarmupTimeoutSec 60 2>&1
    $chatLines | Out-Host

    $chatText = ($chatLines | Out-String)
    if ($chatText -notmatch "(?m)^status=OK\s*$") {
        throw "auto-local chat did not report status=OK"
    }
}

Invoke-Step -Name "Tool Server Integration" -Action {
    Ensure-ComfyUIReady -WaitSec 120
    Ensure-OpenWebUIBestEffort -WaitSec 90

    $toolLines = python .\tests\integration\test_tool_server_integration.py 2>&1
    $toolLines | Out-Host

    $toolText = ($toolLines | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "Tool Server integration test exited with code $LASTEXITCODE"
    }
    if ($toolText -match "(?m)^\[NG\]\s(?!openwebui\b)") {
        throw "Tool Server integration output contains required [NG] markers"
    }
    if ($toolText -match "(?m)^\[WARNING\]\s") {
        throw "Tool Server integration reports failed test cases"
    }
}

Write-Host "`n========================================="
Write-Host "ManaOS Full Smoke Summary"
Write-Host "========================================="
Write-Host "Status | Check"
Write-Host "-----------------------------------------"

$passed = 0
$total = $results.Count
foreach ($key in $results.Keys) {
    $label = Get-CompactLabel -Text $key -MaxLength 24
    if ($results[$key]) {
        $passed++
        Write-Host ("OK     | {0}" -f $label) -ForegroundColor Green
    }
    else {
        Write-Host ("NG     | {0}" -f $label) -ForegroundColor Red
    }
}

$rate = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }
Write-Host "-----------------------------------------"
Write-Host ("Result | {0}/{1} ({2}%)" -f $passed, $total, $rate)

if ($passed -ne $total) {
    exit 1
}
