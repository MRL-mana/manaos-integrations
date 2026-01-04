# Google Drive認証セットアップ状況確認スクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "Google Drive認証セットアップ状況確認" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$credentialsPath = Join-Path $PSScriptRoot "credentials.json"
$tokenPath = Join-Path $PSScriptRoot "token.json"

# 認証情報ファイルの確認
Write-Host "[1] 認証情報ファイルの確認..." -ForegroundColor Yellow
if (Test-Path $credentialsPath) {
    Write-Host "   [OK] credentials.jsonが見つかりました" -ForegroundColor Green
    Write-Host "   パス: $credentialsPath" -ForegroundColor Gray
} else {
    Write-Host "   [NG] credentials.jsonが見つかりません" -ForegroundColor Red
    Write-Host ""
    Write-Host "Google Cloud Consoleで認証情報を作成してください:" -ForegroundColor Yellow
    Write-Host "   1. https://console.cloud.google.com/ にアクセス" -ForegroundColor Cyan
    Write-Host "   2. プロジェクトを作成" -ForegroundColor Cyan
    Write-Host "   3. Google Drive APIを有効化" -ForegroundColor Cyan
    Write-Host "   4. OAuth 2.0認証情報を作成（デスクトップアプリ）" -ForegroundColor Cyan
    Write-Host "   5. credentials.jsonをダウンロードして配置" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "詳細: GOOGLE_DRIVE_クイックセットアップ.md を参照" -ForegroundColor Yellow
}

# トークンファイルの確認
Write-Host ""
Write-Host "[2] トークンファイルの確認..." -ForegroundColor Yellow
if (Test-Path $tokenPath) {
    Write-Host "   [OK] token.jsonが見つかりました（認証済み）" -ForegroundColor Green
    Write-Host "   パス: $tokenPath" -ForegroundColor Gray
} else {
    Write-Host "   [NG] token.jsonが見つかりません（未認証）" -ForegroundColor Yellow
    Write-Host "   認証を実行してください:" -ForegroundColor Yellow
    Write-Host "   .\setup_google_drive.ps1" -ForegroundColor Cyan
}

# 依存関係の確認
Write-Host ""
Write-Host "[3] 依存関係の確認..." -ForegroundColor Yellow
$requiredPackages = @(
    "google-auth",
    "google-auth-oauthlib",
    "google-auth-httplib2",
    "google-api-python-client"
)

$missingPackages = @()
foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -eq 0) {
    Write-Host "   [OK] すべての依存関係がインストールされています" -ForegroundColor Green
} else {
    Write-Host "   [NG] 不足しているパッケージ: $($missingPackages -join ', ')" -ForegroundColor Red
    Write-Host "   インストール: pip install $($missingPackages -join ' ')" -ForegroundColor Cyan
}

# 動作確認
Write-Host ""
Write-Host "[4] Google Drive統合の動作確認..." -ForegroundColor Yellow
if ((Test-Path $credentialsPath) -and ($missingPackages.Count -eq 0)) {
    try {
        $pythonScript = @"
import sys
from pathlib import Path
sys.path.insert(0, r'$PSScriptRoot')

try:
    from google_drive_integration import GoogleDriveIntegration
    
    drive = GoogleDriveIntegration()
    if drive.is_available():
        print('[OK] Google Drive統合が利用可能です')
    else:
        print('[NG] Google Drive統合が利用できません（認証が必要）')
        print('   認証を実行: .\\setup_google_drive.ps1')
except Exception as e:
    print(f'[NG] エラー: {e}')
"@
        $pythonScript | python
    } catch {
        Write-Host "   [NG] 動作確認中にエラーが発生しました" -ForegroundColor Red
    }
} else {
    Write-Host "   [SKIP] 認証情報または依存関係が不足しています" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "確認完了" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $credentialsPath)) {
    Write-Host "次のステップ:" -ForegroundColor Yellow
    Write-Host "  1. Google Cloud Consoleで認証情報を作成" -ForegroundColor Cyan
    Write-Host "  2. credentials.jsonを配置" -ForegroundColor Cyan
    Write-Host "  3. .\setup_google_drive.ps1 を実行" -ForegroundColor Cyan
} elseif (-not (Test-Path $tokenPath)) {
    Write-Host "次のステップ:" -ForegroundColor Yellow
    Write-Host "  .\setup_google_drive.ps1 を実行して認証" -ForegroundColor Cyan
} else {
    Write-Host "次のステップ:" -ForegroundColor Yellow
    Write-Host "  統合APIサーバーで動作確認:" -ForegroundColor Cyan
    Write-Host "    python test_api_endpoints.py" -ForegroundColor Gray
}


















