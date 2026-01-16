# Tesseract OCR インストールスクリプト（Windows用）
# このスクリプトはTesseract OCRを自動的にダウンロードしてインストールします

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tesseract OCR インストールスクリプト" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# インストール先を確認
$installPath = "C:\Program Files\Tesseract-OCR"
$tesseractExe = "$installPath\tesseract.exe"

# 既にインストールされているか確認
if (Test-Path $tesseractExe) {
    Write-Host "✓ Tesseract OCRは既にインストールされています: $tesseractExe" -ForegroundColor Green
    Write-Host ""
    Write-Host "PATHに追加するには、以下のコマンドを実行してください:" -ForegroundColor Yellow
    Write-Host '  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\Tesseract-OCR", "User")' -ForegroundColor Yellow
    exit 0
}

Write-Host "Tesseract OCRが見つかりません。" -ForegroundColor Yellow
Write-Host ""
Write-Host "インストール方法:" -ForegroundColor Cyan
Write-Host "1. 以下のURLからインストーラーをダウンロードしてください:" -ForegroundColor White
Write-Host "   https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Green
Write-Host ""
Write-Host "2. 推奨バージョン:" -ForegroundColor White
Write-Host "   tesseract-ocr-w64-setup-5.x.x.exe (最新版)" -ForegroundColor Green
Write-Host ""
Write-Host "3. インストール時の注意:" -ForegroundColor White
Write-Host "   - インストール先: C:\Program Files\Tesseract-OCR" -ForegroundColor Yellow
Write-Host "   - PATHに追加するオプションを有効にする" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. インストール後、PowerShellを再起動してください" -ForegroundColor White
Write-Host ""
Write-Host "または、Chocolateyを使用してインストール:" -ForegroundColor Cyan
Write-Host "   choco install tesseract" -ForegroundColor Green
Write-Host ""

# Chocolateyが利用可能か確認
$chocoAvailable = Get-Command choco -ErrorAction SilentlyContinue
if ($chocoAvailable) {
    Write-Host "Chocolateyが利用可能です。自動インストールを実行しますか？ (Y/N)" -ForegroundColor Cyan
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host "Tesseract OCRをインストール中..." -ForegroundColor Yellow
        choco install tesseract -y
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Tesseract OCRのインストールが完了しました！" -ForegroundColor Green
            Write-Host "PowerShellを再起動してください。" -ForegroundColor Yellow
        } else {
            Write-Host "インストールに失敗しました。" -ForegroundColor Red
        }
    }
} else {
    Write-Host "Chocolateyがインストールされていません。" -ForegroundColor Yellow
    Write-Host "Chocolateyをインストールするには:" -ForegroundColor Cyan
    Write-Host "   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" -ForegroundColor Green
}
