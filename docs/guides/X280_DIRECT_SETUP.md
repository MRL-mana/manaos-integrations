# X280直接セットアップ手順

**X280側で直接実行してください**

---

## 🚀 X280側での直接セットアップ

### Step 1: X280側でスクリプトを直接作成

X280側のPowerShellで以下を実行：

```powershell
cd C:\manaos_x280

# スクリプトを直接作成
@'
# X280 API Gateway Start Script
# X280 side script (with auto-admin elevation)

# Auto-admin check (optional - will continue if admin elevation fails)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$adminCheckScript = Join-Path $scriptDir "x280_common_admin_check.ps1"
if (Test-Path $adminCheckScript) {
    . $adminCheckScript
}

Write-Host "=== X280 API Gateway Start ===" -ForegroundColor Cyan
Write-Host ""

# Change directory
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
Set-Location $scriptDir

# Check Python environment
Write-Host "[1/3] Checking Python environment..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] $pythonVersion" -ForegroundColor Green

# Check dependencies
Write-Host "[2/3] Checking dependencies..." -ForegroundColor Yellow
$requiredPackages = @("fastapi", "uvicorn", "httpx")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "[WARNING] Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "Install? (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        pip install $missingPackages
    }
} else {
    Write-Host "[OK] Required packages installed" -ForegroundColor Green
}

# Start API Gateway
Write-Host "[3/3] Starting X280 API Gateway..." -ForegroundColor Yellow
Write-Host ""

# Check if x280_api_gateway.py exists
$apiGatewayScript = Join-Path $scriptDir "x280_api_gateway.py"
if (-not (Test-Path $apiGatewayScript)) {
    Write-Host "[ERROR] x280_api_gateway.py not found: $apiGatewayScript" -ForegroundColor Red
    Write-Host "Please transfer the script to X280" -ForegroundColor Yellow
    exit 1
}

# Start API Gateway
python $apiGatewayScript

Write-Host ""
Write-Host "X280 API Gateway stopped" -ForegroundColor Cyan
'@ | Out-File -FilePath "x280_api_gateway_start.ps1" -Encoding UTF8
```

### Step 2: 実行

```powershell
.\x280_api_gateway_start.ps1
```

---

## 📋 簡単な方法（推奨）

X280側で以下を1行ずつ実行：

```powershell
cd C:\manaos_x280
notepad x280_api_gateway_start.ps1
```

Notepadで開いたら、新PC側の `x280_api_gateway_start.ps1` の内容をコピー＆ペーストして保存してください。

---

**X280側で上記の手順を実行してください！**

