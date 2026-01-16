# LM Studio インストールガイドスクリプト

Write-Host "=" * 60
Write-Host "LM Studio インストールガイド"
Write-Host "=" * 60
Write-Host ""

# ダウンロードファイルを検索
Write-Host "[1] ダウンロードファイルを検索中..." -ForegroundColor Yellow
$downloadPaths = @(
    "$env:USERPROFILE\Downloads\LM Studio*.exe",
    "$env:USERPROFILE\Downloads\lm-studio*.exe",
    "$env:USERPROFILE\Desktop\LM Studio*.exe",
    "$env:USERPROFILE\Desktop\lm-studio*.exe"
)

$installerFile = $null
foreach ($pattern in $downloadPaths) {
    $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
    if ($files) {
        $installerFile = $files[0]
        Write-Host "   [✅] インストーラーが見つかりました: $($installerFile.FullName)" -ForegroundColor Green
        break
    }
}

if (-not $installerFile) {
    Write-Host "   [❌] インストーラーが見つかりませんでした" -ForegroundColor Red
    Write-Host ""
    Write-Host "手動でインストールしてください:" -ForegroundColor Cyan
    Write-Host "  1. ダウンロードした .exe ファイルをダブルクリック" -ForegroundColor White
    Write-Host "  2. インストールウィザードに従って進む" -ForegroundColor White
    Write-Host "  3. インストール完了後、このスクリプトを再実行" -ForegroundColor White
    exit 1
}

# インストール済みか確認
Write-Host ""
Write-Host "[2] インストール状況を確認中..." -ForegroundColor Yellow
$installedPaths = @(
    "$env:LOCALAPPDATA\Programs\LM Studio",
    "C:\Program Files\LM Studio"
)

$isInstalled = $false
foreach ($path in $installedPaths) {
    if (Test-Path $path) {
        $exePath = Join-Path $path "LM Studio.exe"
        if (Test-Path $exePath) {
            Write-Host "   [✅] LM Studioは既にインストールされています" -ForegroundColor Green
            Write-Host "   パス: $exePath" -ForegroundColor Gray
            $isInstalled = $true
            break
        }
    }
}

if ($isInstalled) {
    Write-Host ""
    Write-Host "[3] LM Studioを起動しますか？" -ForegroundColor Cyan
    $response = Read-Host "起動しますか？ (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        $exePath = $null
        foreach ($path in $installedPaths) {
            $testPath = Join-Path $path "LM Studio.exe"
            if (Test-Path $testPath) {
                $exePath = $testPath
                break
            }
        }
        if ($exePath) {
            Write-Host "   LM Studioを起動中..." -ForegroundColor Yellow
            Start-Process -FilePath $exePath
            Write-Host "   [✅] LM Studioを起動しました" -ForegroundColor Green
            Write-Host ""
            Write-Host "次のステップ:" -ForegroundColor Cyan
            Write-Host "  1. モデルをダウンロード（Searchタブ）" -ForegroundColor White
            Write-Host "  2. Serverタブでモデルを選択" -ForegroundColor White
            Write-Host "  3. Start Serverをクリック" -ForegroundColor White
        }
    }
} else {
    Write-Host "   [情報] LM Studioはまだインストールされていません" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[3] インストールを開始しますか？" -ForegroundColor Cyan
    Write-Host "   インストーラー: $($installerFile.FullName)" -ForegroundColor Gray
    $response = Read-Host "インストールを開始しますか？ (Y/N)"
    
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host ""
        Write-Host "   [実行中] インストーラーを起動しています..." -ForegroundColor Yellow
        Start-Process -FilePath $installerFile.FullName -Wait
        Write-Host ""
        Write-Host "   [✅] インストールが完了しました（または進行中）" -ForegroundColor Green
        Write-Host ""
        Write-Host "次のステップ:" -ForegroundColor Cyan
        Write-Host "  1. LM Studioを起動" -ForegroundColor White
        Write-Host "  2. モデルをダウンロード（Searchタブ）" -ForegroundColor White
        Write-Host "  3. Serverタブでモデルを選択" -ForegroundColor White
        Write-Host "  4. Start Serverをクリック" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "手動でインストールしてください:" -ForegroundColor Cyan
        Write-Host "  1. $($installerFile.FullName) をダブルクリック" -ForegroundColor White
        Write-Host "  2. インストールウィザードに従って進む" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=" * 60
Write-Host "インストール確認:" -ForegroundColor Cyan
Write-Host "  .\check_running_status.ps1" -ForegroundColor Gray
Write-Host "=" * 60
Write-Host ""



















