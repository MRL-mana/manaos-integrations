# ManaOS LLMルーティングAPI起動スクリプト

Write-Host "=" * 60
Write-Host "ManaOS LLMルーティングAPI 起動"
Write-Host "=" * 60
Write-Host ""

# 環境変数の設定
$env:LLM_SERVER = "lm_studio"  # または "ollama"
$env:PORT = "9501"

Write-Host "[1] 環境変数を設定しました" -ForegroundColor Green
Write-Host "    LLM_SERVER: $env:LLM_SERVER"
Write-Host "    PORT: $env:PORT"
Write-Host ""

# 依存関係の確認
Write-Host "[2] 依存関係を確認中..." -ForegroundColor Yellow

try {
    python -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Flaskがインストールされていません。インストールします..." -ForegroundColor Yellow
        pip install flask flask-cors requests
    }
    Write-Host "   [OK] Flaskが利用可能です" -ForegroundColor Green
} catch {
    Write-Host "   [NG] Flaskの確認に失敗しました" -ForegroundColor Red
    Write-Host "   手動でインストールしてください: pip install flask flask-cors requests" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# APIサーバーを起動
Write-Host "[3] APIサーバーを起動します..." -ForegroundColor Yellow
Write-Host "    エンドポイント: http://localhost:$env:PORT" -ForegroundColor Cyan
Write-Host ""

python manaos_llm_routing_api.py



















