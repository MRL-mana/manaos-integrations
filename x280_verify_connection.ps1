# X280 Connection Verification Script
# Run this on X280 to verify API Gateway is accessible

$ErrorActionPreference = "Continue"

Write-Host "=== X280 Connection Verification ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check if API Gateway is running
Write-Host "[1/4] Checking API Gateway process..." -ForegroundColor Yellow
$x280Port = if ($env:X280_API_PORT) { [int]$env:X280_API_PORT } else { 5120 }
$process = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*manaos_x280*" -or (Get-NetTCPConnection -LocalPort $x280Port -ErrorAction SilentlyContinue -OwningProcess $_.Id) }
if ($process) {
    Write-Host "[OK] API Gateway process found (PID: $($process.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARN] API Gateway process not found" -ForegroundColor Yellow
}

# 2. Check port
Write-Host "[2/4] Checking port $x280Port..." -ForegroundColor Yellow
try {
    $connections = Get-NetTCPConnection -LocalPort $x280Port -ErrorAction SilentlyContinue
    if ($connections) {
        Write-Host "[OK] Port $x280Port is listening" -ForegroundColor Green
        foreach ($conn in $connections) {
            Write-Host "  State: $($conn.State)" -ForegroundColor Gray
            Write-Host "  LocalAddress: $($conn.LocalAddress)" -ForegroundColor Gray
            Write-Host "  LocalPort: $($conn.LocalPort)" -ForegroundColor Gray
        }
    } else {
        Write-Host "[WARN] Port $x280Port is not listening" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] Could not check port (CIM unavailable)" -ForegroundColor Gray
    $netstat = netstat -ano | Select-String ":$x280Port"
    if ($netstat) {
        Write-Host "[OK] Port $x280Port found in netstat:" -ForegroundColor Green
        Write-Host $netstat -ForegroundColor Gray
    }
}

# 3. Check firewall rule
Write-Host "[3/4] Checking firewall rule..." -ForegroundColor Yellow
$firewallRule = netsh advfirewall firewall show rule name="ManaOS X280 API Gateway" 2>&1
if ($LASTEXITCODE -eq 0 -and -not ($firewallRule -match "指定された規則が見つかりません")) {
    Write-Host "[OK] Firewall rule exists" -ForegroundColor Green
    $firewallRule | Select-String -Pattern "有効|Enabled|プロファイル|Profile" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} else {
    Write-Host "[WARN] Firewall rule not found" -ForegroundColor Yellow
}

# 4. Test local connection
Write-Host "[4/4] Testing local connection..." -ForegroundColor Yellow
$x280ApiBaseUrl = if ($env:X280_API_URL) {
    $env:X280_API_URL.TrimEnd('/')
} else {
    "http://127.0.0.1:$x280Port"
}
try {
    $response = Invoke-RestMethod -Uri "$x280ApiBaseUrl/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] Local connection works!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Local connection failed: $_" -ForegroundColor Red
}

# 5. Check Tailscale IP
Write-Host ""
Write-Host "Checking Tailscale network..." -ForegroundColor Yellow
$tailscaleIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue).IPAddress
if ($tailscaleIP) {
    Write-Host "[OK] Tailscale IP: $tailscaleIP" -ForegroundColor Green
    if ($tailscaleIP -eq "100.127.121.20") {
        Write-Host "[OK] Tailscale IP matches expected IP" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Tailscale IP does not match expected IP (100.127.121.20)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Tailscale interface not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If local connection works but remote doesn't:" -ForegroundColor Yellow
Write-Host "1. Check firewall rule profiles (should include 'Private' or 'Domain')" -ForegroundColor White
Write-Host "2. Verify Tailscale is connected" -ForegroundColor White
Write-Host "3. Check Windows Defender Firewall with Advanced Security" -ForegroundColor White


















