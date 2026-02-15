# Tool Server ホスト実行スクリプト（レミ先輩仕様：確実に動く）
# Windows環境では、コンテナではなくホストから実行する方が確実

Write-Host "Tool Server ホスト実行スクリプト（レミ先輩仕様）" -ForegroundColor Cyan
Write-Host ""

# 作業ディレクトリに移動
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# tool_serverディレクトリに移動
Set-Location tool_server

# 依存関係のインストール
Write-Host "依存関係をインストール中..." -ForegroundColor Yellow
pip install -r requirements.txt

# Tool Serverを起動
Write-Host ""
Write-Host "Tool Serverを起動します..." -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:9503" -ForegroundColor Gray
Write-Host "  OpenAPI Spec: http://127.0.0.1:9503/openapi.json" -ForegroundColor Gray
Write-Host ""

python main.py
