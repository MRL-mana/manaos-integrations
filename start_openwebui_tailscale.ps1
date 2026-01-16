# Open WebUI Tailscale アクセス完全セットアップスクリプト
# 管理者権限で実行してください

$ErrorActionPreference = "Continue"

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  このスクリプトは管理者権限で実行する必要があります" -ForegroundColor Yellow
    Write-Host "   管理者としてPowerShellを開いて再実行してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Open WebUI Tailscale 完全セットアップ ===" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Desktopの確認と起動
Write-Host "[1/6] Checking Docker Desktop..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "[OK] Docker Desktop is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Docker Desktop is not running" -ForegroundColor Yellow
    Write-Host "  Attempting to start Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Write-Host "  Waiting for Docker Desktop to start (30 seconds)..." -ForegroundColor Yellow
    $timeout = 30
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        try {
            docker ps | Out-Null
            Write-Host "[OK] Docker Desktop started successfully" -ForegroundColor Green
            break
        } catch {
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
    }
    if ($elapsed -ge $timeout) {
        Write-Host ""
        Write-Host "[WARN] Docker Desktop may still be starting. Please wait and try again." -ForegroundColor Yellow
    }
}

# 2. Tailscale IP確認
Write-Host ""
Write-Host "[2/6] Checking Tailscale..." -ForegroundColor Yellow
$tailscaleIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue).IPAddress
if ($tailscaleIP) {
    Write-Host "[OK] Tailscale IP: $tailscaleIP" -ForegroundColor Green
} else {
    Write-Host "[NG] Tailscale interface not found" -ForegroundColor Red
    Write-Host "  Please make sure Tailscale is installed and connected" -ForegroundColor Yellow
    exit 1
}

# 3. Docker Compose設定の確認
Write-Host ""
Write-Host "[3/6] Checking Docker Compose configuration..." -ForegroundColor Yellow
$composeFile = "docker-compose.always-ready-llm.yml"
if (-not (Test-Path $composeFile)) {
    Write-Host "[NG] Docker Compose file not found: $composeFile" -ForegroundColor Red
    exit 1
}

$content = Get-Content $composeFile -Raw
if ($content -notmatch "0\.0\.0\.0:3001:8080") {
    Write-Host "[INFO] Updating port binding to 0.0.0.0:3001:8080..." -ForegroundColor Yellow
    $content = $content -replace "(\s+ports:\s*\n\s*-\s*)3001:8080", '$10.0.0.0:3001:8080'
    Set-Content -Path $composeFile -Value $content -NoNewline
    Write-Host "[OK] Configuration updated" -ForegroundColor Green
}

# 4. Open WebUIコンテナの起動
Write-Host ""
Write-Host "[4/6] Starting Open WebUI container..." -ForegroundColor Yellow
try {
    docker-compose -f $composeFile up -d openwebui 2>&1 | Out-Null
    Write-Host "[OK] Container started" -ForegroundColor Green
    Write-Host "  Waiting for container to be ready (10 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
} catch {
    Write-Host "[NG] Failed to start container: $_" -ForegroundColor Red
    exit 1
}

# 5. ファイアウォールルールの追加
Write-Host ""
Write-Host "[5/6] Configuring firewall..." -ForegroundColor Yellow
$firewallRule = Get-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" -ErrorAction SilentlyContinue
if (-not $firewallRule) {
    Write-Host "[INFO] Adding firewall rule for port 3001..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" `
            -Direction Inbound `
            -LocalPort 3001 `
            -Protocol TCP `
            -Action Allow `
            -Profile Private,Public `
            -ErrorAction Stop | Out-Null
        Write-Host "[OK] Firewall rule added" -ForegroundColor Green
    } catch {
        Write-Host "[NG] Failed to add firewall rule: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Firewall rule already exists" -ForegroundColor Green
    if (-not $firewallRule.Enabled) {
        Write-Host "[INFO] Enabling firewall rule..." -ForegroundColor Yellow
        Enable-NetFirewallRule -DisplayName "Open WebUI Tailscale Access"
    }
}

# 6. 接続テスト
Write-Host ""
Write-Host "[6/6] Testing connection..." -ForegroundColor Yellow

# ポート確認
$portCheck = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
if ($portCheck) {
    $localAddress = ($portCheck | Select-Object -First 1).LocalAddress
    Write-Host "[OK] Port 3001 is listening on: $localAddress" -ForegroundColor Green
    if ($localAddress -eq "0.0.0.0" -or $localAddress -eq "::") {
        Write-Host "[OK] Port is bound to all interfaces (Tailscale accessible)" -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] Port 3001 is not listening yet" -ForegroundColor Yellow
}

# HTTP接続テスト
Write-Host "  Testing HTTP connection..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3001" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[OK] HTTP connection works (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "[WARN] HTTP connection failed: $_" -ForegroundColor Yellow
    Write-Host "  Container may still be starting. Wait a few seconds and try again." -ForegroundColor Yellow
}

# まとめ
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 Access URL from remote device:" -ForegroundColor Cyan
Write-Host "   http://$tailscaleIP:3001" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "✅ Configuration:" -ForegroundColor Green
Write-Host "   - Docker Compose: 0.0.0.0:3001:8080" -ForegroundColor Gray
Write-Host "   - Firewall: Port 3001 allowed" -ForegroundColor Gray
Write-Host "   - Tailscale IP: $tailscaleIP" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Open http://$tailscaleIP:3001 in a browser from remote device" -ForegroundColor White
Write-Host "   2. If connection fails, wait 30 seconds and try again" -ForegroundColor White
Write-Host "   3. Check Docker Desktop is running" -ForegroundColor White
Write-Host ""
