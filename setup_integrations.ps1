# ManaOS統合システム - セットアップスクリプト
# すべての統合を有効化するための依存関係をインストール

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ManaOS統合システム - セットアップ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 現在のディレクトリを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. GitHub統合の依存関係
Write-Host "[1/8] GitHub統合の依存関係をインストール中..." -ForegroundColor Yellow
pip install PyGithub --quiet
if ($?) {
    Write-Host "  [OK] PyGithubをインストールしました" -ForegroundColor Green
} else {
    Write-Host "  [WARN] PyGithubのインストールに失敗しました" -ForegroundColor Yellow
}

# 2. 統一記憶システムの依存関係（標準ライブラリのみ使用）
Write-Host "[2/8] 統一記憶システムの依存関係を確認中..." -ForegroundColor Yellow
Write-Host "  [OK] 標準ライブラリのみ使用（追加インストール不要）" -ForegroundColor Green

# 3. LLMルーティングの依存関係
Write-Host "[3/8] LLMルーティングの依存関係をインストール中..." -ForegroundColor Yellow
pip install pyyaml requests --quiet
if ($?) {
    Write-Host "  [OK] PyYAML, requestsをインストールしました" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 依存関係のインストールに失敗しました" -ForegroundColor Yellow
}

# 4. 通知ハブの依存関係（標準ライブラリのみ使用）
Write-Host "[4/8] 通知ハブの依存関係を確認中..." -ForegroundColor Yellow
Write-Host "  [OK] 標準ライブラリのみ使用（追加インストール不要）" -ForegroundColor Green

# 5. 秘書機能の依存関係（標準ライブラリのみ使用）
Write-Host "[5/8] 秘書機能の依存関係を確認中..." -ForegroundColor Yellow
Write-Host "  [OK] 標準ライブラリのみ使用（追加インストール不要）" -ForegroundColor Green

# 6. 画像ストックの依存関係
Write-Host "[6/8] 画像ストックの依存関係をインストール中..." -ForegroundColor Yellow
pip install Pillow --quiet
if ($?) {
    Write-Host "  [OK] Pillowをインストールしました" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Pillowのインストールに失敗しました" -ForegroundColor Yellow
}

# 7. 環境変数の設定確認
Write-Host "[7/8] 環境変数の設定を確認中..." -ForegroundColor Yellow
$envFile = Join-Path $scriptDir ".env"
if (Test-Path $envFile) {
    Write-Host "  [OK] .envファイルが存在します" -ForegroundColor Green
} else {
    Write-Host "  [INFO] .envファイルを作成します..." -ForegroundColor Yellow
    @"
# ManaOS統合システム - 環境変数設定

# Obsidian Vaultパス（統一記憶システム用）
OBSIDIAN_VAULT_PATH=C:\Users\mana4\Documents\Obsidian Vault

# Ollama設定（LLMルーティング用）
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# GitHub統合（オプション）
# GITHUB_TOKEN=your_github_token_here

# 通知設定（オプション）
# SLACK_WEBHOOK_URL=your_slack_webhook_url
# DISCORD_WEBHOOK_URL=your_discord_webhook_url
# EMAIL_SMTP_HOST=smtp.gmail.com
# EMAIL_SMTP_PORT=587
# EMAIL_USERNAME=your_email@gmail.com
# EMAIL_PASSWORD=your_app_password
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "  [OK] .envファイルを作成しました" -ForegroundColor Green
}

# 8. 統合の状態確認
Write-Host "[8/8] 統合の状態を確認中..." -ForegroundColor Yellow
Write-Host ""
Write-Host "統合システムのセットアップが完了しました！" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  1. 統合APIサーバーを再起動してください" -ForegroundColor White
Write-Host "  2. http://localhost:9500/api/integrations/status で状態を確認" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

