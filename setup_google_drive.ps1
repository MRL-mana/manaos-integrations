# Google Drive認証セットアップスクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "Google Drive API 認証セットアップ" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$credentialsPath = Join-Path $PSScriptRoot "credentials.json"
$tokenPath = Join-Path $PSScriptRoot "token.json"

# 認証情報ファイルの確認
Write-Host "[1] 認証情報ファイルの確認..." -ForegroundColor Yellow
if (-not (Test-Path $credentialsPath)) {
    Write-Host "   [NG] credentials.jsonが見つかりません" -ForegroundColor Red
    Write-Host ""
    Write-Host "Google Cloud Consoleで認証情報を作成してください:" -ForegroundColor Yellow
    Write-Host "   1. https://console.cloud.google.com/ にアクセス" -ForegroundColor Cyan
    Write-Host "   2. プロジェクトを作成（または既存を選択）" -ForegroundColor Cyan
    Write-Host "   3. Google Drive APIを有効化" -ForegroundColor Cyan
    Write-Host "   4. OAuth 2.0認証情報を作成（デスクトップアプリ）" -ForegroundColor Cyan
    Write-Host "   5. credentials.jsonをダウンロード" -ForegroundColor Cyan
    Write-Host "   6. このディレクトリに配置: $credentialsPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "詳細は GOOGLE_DRIVE_SETUP.md を参照してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "   [OK] credentials.jsonが見つかりました" -ForegroundColor Green

# 依存関係の確認
Write-Host ""
Write-Host "[2] 依存関係の確認..." -ForegroundColor Yellow
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

if ($missingPackages.Count -gt 0) {
    Write-Host "   [WARN] 不足しているパッケージ: $($missingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "   インストールしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host "   インストール中..." -ForegroundColor Gray
        pip install $missingPackages
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   [NG] インストールに失敗しました" -ForegroundColor Red
            exit 1
        }
        Write-Host "   [OK] インストール完了" -ForegroundColor Green
    } else {
        Write-Host "   インストールをスキップしました" -ForegroundColor Yellow
    }
} else {
    Write-Host "   [OK] すべての依存関係がインストールされています" -ForegroundColor Green
}

# 認証の実行
Write-Host ""
Write-Host "[3] Google Drive認証を実行します..." -ForegroundColor Yellow
Write-Host "   ブラウザが開いて認証画面が表示されます" -ForegroundColor Gray
Write-Host "   Googleアカウントでログインして、アクセス許可を承認してください" -ForegroundColor Gray
Write-Host ""

try {
    $pythonScript = @"
import sys
from pathlib import Path
sys.path.insert(0, r'$PSScriptRoot')

from google_drive_integration import GoogleDriveIntegration

print('Google Drive認証を開始します...')
drive = GoogleDriveIntegration()

if drive.is_available():
    print('[OK] 認証が完了しました！')
    print(f'トークンファイル: {Path(r'$PSScriptRoot') / 'token.json'}')
else:
    print('[NG] 認証に失敗しました')
    sys.exit(1)
"@

    $pythonScript | python
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=" -NoNewline
        Write-Host ("=" * 59) -ForegroundColor Cyan
        Write-Host "[OK] Google Drive認証が完了しました！" -ForegroundColor Green
        Write-Host "=" -NoNewline
        Write-Host ("=" * 59) -ForegroundColor Cyan
        Write-Host ""
        Write-Host "次のステップ:" -ForegroundColor Cyan
        Write-Host "  統合APIサーバーを起動して動作確認:" -ForegroundColor Yellow
        Write-Host "    python unified_api_server.py" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  APIエンドポイントをテスト:" -ForegroundColor Yellow
        Write-Host "    python test_api_endpoints.py" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "[NG] 認証に失敗しました" -ForegroundColor Red
        Write-Host "GOOGLE_DRIVE_SETUP.mdを参照して、手動で認証を実行してください" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "[NG] エラー: $_" -ForegroundColor Red
    exit 1
}


















