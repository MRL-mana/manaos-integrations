# Antigravity 起動スクリプト
# 必要なときだけ起動する「知識加工工場」

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "=== Antigravity 起動 ===" -ForegroundColor Cyan
Write-Host ""

# Antigravityの起動方法を確認
# 方法1: Webアプリの場合（URLを開く）
# 方法2: デスクトップアプリの場合（実行ファイルを起動）
# 方法3: コマンドラインの場合（コマンドを実行）

# 設定（環境変数または設定ファイルから取得）
$ANTIGRAVITY_URL = [Environment]::GetEnvironmentVariable("ANTIGRAVITY_URL", "User")
$ANTIGRAVITY_PATH = [Environment]::GetEnvironmentVariable("ANTIGRAVITY_PATH", "User")

# デフォルト値
if (-not $ANTIGRAVITY_URL) {
    # Webアプリの場合のデフォルトURL（実際のURLに置き換えてください）
    $ANTIGRAVITY_URL = "https://antigravity.ai"
}

if (-not $ANTIGRAVITY_PATH) {
    # デスクトップアプリの場合のデフォルトパス（実際のパスに置き換えてください）
    # $ANTIGRAVITY_PATH = "C:\Users\mana4\AppData\Local\Programs\antigravity\antigravity.exe"
}

Write-Host "[INFO] Antigravity起動方法を確認中..." -ForegroundColor Yellow

# 方法1: Webアプリとして起動（推奨）
if ($ANTIGRAVITY_URL) {
    Write-Host "[起動] Webアプリを開きます: $ANTIGRAVITY_URL" -ForegroundColor Green
    Start-Process $ANTIGRAVITY_URL
    Write-Host "[OK] Antigravityを起動しました（ブラウザ）" -ForegroundColor Green
    Write-Host ""
    Write-Host "次のステップ:" -ForegroundColor Cyan
    Write-Host "  1. Antigravityでプロンプトを選択（antigravity_prompts.md参照）" -ForegroundColor White
    Write-Host "  2. Obsidianからノートをコピーして貼り付け" -ForegroundColor White
    Write-Host "  3. 実行して結果を取得" -ForegroundColor White
    Write-Host "  4. 結果をObsidianに保存（manaos_obsidian_integration.py使用）" -ForegroundColor White
    Write-Host ""
    exit 0
}

# 方法2: デスクトップアプリとして起動
if ($ANTIGRAVITY_PATH -and (Test-Path $ANTIGRAVITY_PATH)) {
    Write-Host "[起動] デスクトップアプリを起動します: $ANTIGRAVITY_PATH" -ForegroundColor Green
    Start-Process $ANTIGRAVITY_PATH
    Write-Host "[OK] Antigravityを起動しました（デスクトップアプリ）" -ForegroundColor Green
    Write-Host ""
    Write-Host "次のステップ:" -ForegroundColor Cyan
    Write-Host "  1. Antigravityでプロンプトを選択（antigravity_prompts.md参照）" -ForegroundColor White
    Write-Host "  2. Obsidianからノートをコピーして貼り付け" -ForegroundColor White
    Write-Host "  3. 実行して結果を取得" -ForegroundColor White
    Write-Host "  4. 結果をObsidianに保存（manaos_obsidian_integration.py使用）" -ForegroundColor White
    Write-Host ""
    exit 0
}

# 方法3: コマンドラインから起動（オプション）
# Antigravityがコマンドライン対応している場合
$antigravityCmd = Get-Command antigravity -ErrorAction SilentlyContinue
if ($antigravityCmd) {
    Write-Host "[起動] コマンドラインから起動します" -ForegroundColor Green
    Start-Process "antigravity" -ArgumentList "start"
    Write-Host "[OK] Antigravityを起動しました（コマンドライン）" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# 設定されていない場合
Write-Host "[WARN] Antigravityの起動方法が設定されていません" -ForegroundColor Yellow
Write-Host ""
Write-Host "設定方法:" -ForegroundColor Cyan
Write-Host "  1. Webアプリの場合:" -ForegroundColor White
Write-Host "     [Environment]::SetEnvironmentVariable('ANTIGRAVITY_URL', 'https://antigravity.ai', 'User')" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. デスクトップアプリの場合:" -ForegroundColor White
Write-Host "     [Environment]::SetEnvironmentVariable('ANTIGRAVITY_PATH', 'C:\path\to\antigravity.exe', 'User')" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. コマンドラインの場合:" -ForegroundColor White
Write-Host "     antigravityコマンドがPATHに設定されている必要があります" -ForegroundColor Gray
Write-Host ""
Write-Host "現在の設定:" -ForegroundColor Cyan
Write-Host "  ANTIGRAVITY_URL: $ANTIGRAVITY_URL" -ForegroundColor Gray
Write-Host "  ANTIGRAVITY_PATH: $ANTIGRAVITY_PATH" -ForegroundColor Gray
Write-Host ""
Write-Host "手動起動方法:" -ForegroundColor Cyan
Write-Host "  1. ブラウザでAntigravityのURLを開く" -ForegroundColor White
Write-Host "  2. または、デスクトップアプリを直接起動" -ForegroundColor White
Write-Host ""




















