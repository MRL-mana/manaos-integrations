# Tesseract OCR 日本語データインストールスクリプト
# 管理者権限で実行してください

$tessdataPath = "C:\Program Files\Tesseract-OCR\tessdata"
$tempFile = "$env:TEMP\jpn.traineddata"
$targetFile = "$tessdataPath\jpn.traineddata"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tesseract OCR 日本語データインストール" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] このスクリプトは管理者権限で実行してください" -ForegroundColor Red
    Write-Host "PowerShellを管理者として実行してから、このスクリプトを実行してください" -ForegroundColor Yellow
    pause
    exit 1
}

# 一時ファイルが存在するか確認
if (-not (Test-Path $tempFile)) {
    Write-Host "[INFO] 日本語データをダウンロード中..." -ForegroundColor Yellow
    $url = "https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata"
    try {
        Invoke-WebRequest -Uri $url -OutFile $tempFile -UseBasicParsing
        Write-Host "[OK] ダウンロード完了: $tempFile" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] ダウンロード失敗: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[INFO] 一時ファイルが見つかりました: $tempFile" -ForegroundColor Yellow
}

# tessdataフォルダの存在確認
if (-not (Test-Path $tessdataPath)) {
    Write-Host "[ERROR] Tesseract OCRのtessdataフォルダが見つかりません: $tessdataPath" -ForegroundColor Red
    Write-Host "Tesseract OCRが正しくインストールされているか確認してください" -ForegroundColor Yellow
    exit 1
}

# ファイルをコピー
Write-Host "[INFO] 日本語データをインストール中..." -ForegroundColor Yellow
try {
    Copy-Item -Path $tempFile -Destination $targetFile -Force
    Write-Host "[OK] インストール完了: $targetFile" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] インストール失敗: $_" -ForegroundColor Red
    exit 1
}

# 確認
Write-Host ""
Write-Host "[INFO] インストール確認中..." -ForegroundColor Yellow
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
Write-Host ""

if (Test-Path $targetFile) {
    Write-Host "[OK] 日本語データのインストールが完了しました！" -ForegroundColor Green
    Write-Host "これで 'jpn+eng' 言語でOCRが使用できます" -ForegroundColor Green
} else {
    Write-Host "[ERROR] インストールの確認に失敗しました" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
pause
