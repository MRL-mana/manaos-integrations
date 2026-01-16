# Open WebUI Tailscale アクセス修正スクリプト
# ERR_CONNECTION_REFUSED エラーを修正します

$ErrorActionPreference = "Continue"

Write-Host "=== Open WebUI Tailscale Access Fix ===" -ForegroundColor Cyan
Write-Host ""

# 1. Open WebUIコンテナの状態確認
Write-Host "[1/5] Checking Open WebUI container..." -ForegroundColor Yellow
$container = docker ps -a --filter "name=open-webui" --format "{{.Names}} {{.Status}}" 2>$null
if ($container) {
    Write-Host "[OK] Container found: $container" -ForegroundColor Green
} else {
    Write-Host "[NG] Container not found" -ForegroundColor Red
    Write-Host "  Starting Open WebUI..." -ForegroundColor Yellow
    docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
    Start-Sleep -Seconds 5
}

# 2. ポート3001のリッスン確認
Write-Host ""
Write-Host "[2/5] Checking port 3001 binding..." -ForegroundColor Yellow
$portCheck = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
if ($portCheck) {
    $localAddress = ($portCheck | Select-Object -First 1).LocalAddress
    Write-Host "[INFO] Port 3001 is listening on: $localAddress" -ForegroundColor Gray
    if ($localAddress -eq "127.0.0.1" -or $localAddress -eq "::1") {
        Write-Host "[WARN] Port is bound to localhost only!" -ForegroundColor Yellow
        Write-Host "  This prevents Tailscale access. Fixing..." -ForegroundColor Yellow
    } elseif ($localAddress -eq "0.0.0.0" -or $localAddress -eq "::") {
        Write-Host "[OK] Port is bound to all interfaces" -ForegroundColor Green
    }
} else {
    Write-Host "[NG] Port 3001 is not listening" -ForegroundColor Red
}

# 3. Docker Compose設定の確認と修正
Write-Host ""
Write-Host "[3/5] Checking Docker Compose configuration..." -ForegroundColor Yellow
$composeFile = "docker-compose.always-ready-llm.yml"
if (Test-Path $composeFile) {
    $content = Get-Content $composeFile -Raw
    if ($content -match "ports:\s*\n\s*-\s*3001:8080") {
        Write-Host "[OK] Port mapping found: 3001:8080" -ForegroundColor Green
        # 明示的に0.0.0.0にバインドするように修正
        if ($content -notmatch "0\.0\.0\.0:3001:8080") {
            Write-Host "[INFO] Updating port binding to 0.0.0.0:3001:8080..." -ForegroundColor Yellow
            $content = $content -replace "(\s+ports:\s*\n\s*-\s*)3001:8080", '$10.0.0.0:3001:8080'
            Set-Content -Path $composeFile -Value $content -NoNewline
            Write-Host "[OK] Configuration updated" -ForegroundColor Green
            Write-Host "  Restarting container..." -ForegroundColor Yellow
            docker-compose -f $composeFile up -d openwebui
            Start-Sleep -Seconds 5
        }
    }
} else {
    Write-Host "[WARN] Docker Compose file not found: $composeFile" -ForegroundColor Yellow
}

# 4. ファイアウォールルールの追加
Write-Host ""
Write-Host "[4/5] Checking firewall rules..." -ForegroundColor Yellow
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
        Write-Host "[WARN] Failed to add firewall rule: $_" -ForegroundColor Yellow
        Write-Host "  You may need to run as Administrator" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Firewall rule already exists" -ForegroundColor Green
    if (-not $firewallRule.Enabled) {
        Write-Host "[INFO] Enabling firewall rule..." -ForegroundColor Yellow
        Enable-NetFirewallRule -DisplayName "Open WebUI Tailscale Access"
    }
}

# 5. Tailscale IP確認
Write-Host ""
Write-Host "[5/5] Checking Tailscale IP..." -ForegroundColor Yellow
$tailscaleIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue).IPAddress
if ($tailscaleIP) {
    Write-Host "[OK] Tailscale IP: $tailscaleIP" -ForegroundColor Green
} else {
    Write-Host "[NG] Tailscale interface not found" -ForegroundColor Red
    Write-Host "  Make sure Tailscale is installed and connected" -ForegroundColor Yellow
}

# 6. 接続テスト
Write-Host ""
Write-Host "=== Testing Connection ===" -ForegroundColor Cyan
Write-Host ""

# ローカル接続テスト
Write-Host "Testing localhost connection..." -ForegroundColor Yellow
try {
    $localResponse = Invoke-WebRequest -Uri "http://localhost:3001" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Localhost connection works" -ForegroundColor Green
} catch {
    Write-Host "[NG] Localhost connection failed: $_" -ForegroundColor Red
}

# Tailscale IP接続テスト（自分自身から）
if ($tailscaleIP) {
    Write-Host "Testing Tailscale IP connection ($tailscaleIP)..." -ForegroundColor Yellow
    try {
        $tailscaleResponse = Invoke-WebRequest -Uri "http://$tailscaleIP:3001" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "[OK] Tailscale IP connection works" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Tailscale IP connection failed: $_" -ForegroundColor Yellow
        Write-Host "  This is normal if testing from the same machine" -ForegroundColor Gray
    }
}

# 7. まとめ
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host ""

if ($tailscaleIP) {
    Write-Host "📌 Access URL from remote device:" -ForegroundColor Cyan
    Write-Host "   http://$tailscaleIP:3001" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Make sure Open WebUI container is running" -ForegroundColor White
    Write-Host "   2. Verify firewall rule is enabled" -ForegroundColor White
    Write-Host "   3. Test from remote device using the URL above" -ForegroundColor White
    Write-Host "   4. If still not working, restart Docker Desktop" -ForegroundColor White
} else {
    Write-Host "⚠️  Tailscale is not connected" -ForegroundColor Yellow
    Write-Host "   Connect Tailscale first, then try again" -ForegroundColor White
}

Write-Host ""
Write-Host "=== Fix Complete ===" -ForegroundColor Cyan
