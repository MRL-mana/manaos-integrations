# Qwan-image-2512モデルインストールスクリプト（PowerShell版）

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "Qwan-image-2512 インストールスクリプト" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Pythonの確認
Write-Host "[0] Python環境の確認..." -ForegroundColor Yellow
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    $pythonExe = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $pythonExe) {
    Write-Host "   ❌ Pythonが見つかりません" -ForegroundColor Red
    Write-Host "   Pythonをインストールしてください: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✅ Python: $pythonExe" -ForegroundColor Green
$pythonVersion = python --version 2>&1
Write-Host "   バージョン: $pythonVersion" -ForegroundColor Gray
Write-Host ""

# 依存関係の確認
Write-Host "[1] 依存関係の確認..." -ForegroundColor Yellow
$requiredModules = @("requests", "pathlib")
$missingModules = @()

foreach ($module in $requiredModules) {
    $check = python -c "import $module" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingModules += $module
    }
}

if ($missingModules.Count -gt 0) {
    Write-Host "   不足しているモジュール: $($missingModules -join ', ')" -ForegroundColor Yellow
    Write-Host "   インストール中..." -ForegroundColor Yellow
    foreach ($module in $missingModules) {
        pip install $module --quiet
    }
    Write-Host "   ✅ 依存関係をインストールしました" -ForegroundColor Green
} else {
    Write-Host "   ✅ すべての依存関係がインストール済みです" -ForegroundColor Green
}
Write-Host ""

# Pythonスクリプトを実行
Write-Host "[2] インストールスクリプトを実行中..." -ForegroundColor Yellow
Write-Host ""

python install_qwan_image_2512.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "インストールが完了しました！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "インストール中にエラーが発生しました" -ForegroundColor Red
    exit 1
}




