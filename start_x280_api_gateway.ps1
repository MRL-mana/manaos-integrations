# X280 API Gateway起動スクリプト
# X280側で実行して、ManaOSからのコマンドを受け付けるAPIサーバーを起動

Write-Host "=== X280 API Gateway 起動 ===" -ForegroundColor Cyan

$x280Port = if ($env:X280_API_PORT) { [int]$env:X280_API_PORT } else { 5120 }
$x280ApiBaseUrl = if ($env:X280_API_URL) {
    $env:X280_API_URL.TrimEnd('/')
} else {
    "http://127.0.0.1:$x280Port"
}

# 1. Python環境確認
Write-Host "`n[1] Python環境確認中..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Pythonが見つかりません" -ForegroundColor Red
    exit 1
}

# 2. 必要なパッケージ確認
Write-Host "`n[2] 必要なパッケージ確認中..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "httpx", "pydantic")
$missingPackages = @()

foreach ($package in $packages) {
    $check = python -c "import $package" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "  [WARN] 以下のパッケージが不足しています: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "  インストールしますか？ (y/n)" -ForegroundColor Cyan
    $response = Read-Host
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "  インストール中..." -ForegroundColor Yellow
        pip install $missingPackages
    } else {
        Write-Host "  [ERROR] 必要なパッケージをインストールしてください" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [OK] すべてのパッケージがインストールされています" -ForegroundColor Green
}

# 3. ポート使用状況確認
Write-Host "`n[3] ポート$x280Port の使用状況確認中..." -ForegroundColor Yellow
$portCheck = netstat -an | Select-String ":$x280Port"
if ($portCheck) {
    Write-Host "  [WARN] ポート$x280Port は既に使用されています" -ForegroundColor Yellow
    Write-Host "  既存のプロセスを終了しますか？ (y/n)" -ForegroundColor Cyan
    $response = Read-Host
    if ($response -eq "y" -or $response -eq "Y") {
        $process = Get-NetTCPConnection -LocalPort $x280Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
        if ($process) {
            Stop-Process -Id $process -Force
            Start-Sleep -Seconds 2
            Write-Host "  [OK] 既存のプロセスを終了しました" -ForegroundColor Green
        }
    } else {
        Write-Host "  [ERROR] ポート$x280Port が使用中のため起動できません" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [OK] ポート$x280Port は利用可能です" -ForegroundColor Green
}

# 4. スクリプトのパス確認
Write-Host "`n[4] API Gatewayスクリプトのパス確認中..." -ForegroundColor Yellow
$scriptPath = Join-Path $PSScriptRoot "x280_api_gateway.py"
if (Test-Path $scriptPath) {
    Write-Host "  [OK] $scriptPath" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] API Gatewayスクリプトが見つかりません: $scriptPath" -ForegroundColor Red
    exit 1
}

# 5. 環境変数の設定
Write-Host "`n[5] 環境変数を設定中..." -ForegroundColor Yellow
$env:X280_API_PORT = "$x280Port"
$env:X280_HOST = "localhost"
Write-Host "  X280_API_PORT = $env:X280_API_PORT" -ForegroundColor Green
Write-Host "  X280_HOST = $env:X280_HOST" -ForegroundColor Green

# 6. API Gatewayを起動
Write-Host "`n[6] X280 API Gatewayを起動中..." -ForegroundColor Yellow
Write-Host "  ポート: $x280Port" -ForegroundColor Cyan
Write-Host "  アクセスURL: $x280ApiBaseUrl" -ForegroundColor Cyan
Write-Host "  ドキュメント: $x280ApiBaseUrl/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  停止するには Ctrl+C を押してください" -ForegroundColor Yellow
Write-Host ""

# API Gatewayを起動
python $scriptPath

