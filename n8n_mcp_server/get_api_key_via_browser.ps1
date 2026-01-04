# n8nのAPIキーを取得するためのブラウザ自動化スクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n APIキー取得ガイド" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$n8nUrl = "http://100.93.120.33:5678"

Write-Host "[手順1] n8nのWeb UIにアクセス" -ForegroundColor Yellow
Write-Host "  ブラウザで以下のURLを開いてください:" -ForegroundColor White
Write-Host "  $n8nUrl" -ForegroundColor Cyan
Write-Host ""

Write-Host "[手順2] ログイン" -ForegroundColor Yellow
Write-Host "  n8nのアカウントでログインしてください" -ForegroundColor White
Write-Host ""

Write-Host "[手順3] APIキーを作成" -ForegroundColor Yellow
Write-Host "  1. 左上のメニュー（≡）をクリック" -ForegroundColor White
Write-Host "  2. Settings を選択" -ForegroundColor White
Write-Host "  3. API を選択" -ForegroundColor White
Write-Host "  4. Create API Key をクリック" -ForegroundColor White
Write-Host "  5. APIキー名を入力（例: MCP Server）" -ForegroundColor White
Write-Host "  6. Create をクリック" -ForegroundColor White
Write-Host "  7. 表示されたAPIキーをコピー" -ForegroundColor White
Write-Host ""

Write-Host "[手順4] APIキーを設定" -ForegroundColor Yellow
Write-Host "  コピーしたAPIキーを入力してください:" -ForegroundColor White
Write-Host ""

$apiKey = Read-Host "APIキー"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[NG] APIキーが入力されていません" -ForegroundColor Red
    exit 1
}

# 設定ファイルを読み込む
$mcpConfigPath = "$env:USERPROFILE\.cursor\mcp.json"

if (-not (Test-Path $mcpConfigPath)) {
    Write-Host "[NG] MCP設定ファイルが見つかりません: $mcpConfigPath" -ForegroundColor Red
    exit 1
}

$jsonContent = Get-Content $mcpConfigPath -Raw
$config = $jsonContent | ConvertFrom-Json

# APIキーを設定
if ($config.mcpServers.n8n) {
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    $config.mcpServers.n8n.env.N8N_API_KEY = $apiKey
    
    # JSONに変換して保存
    $json = $config | ConvertTo-Json -Depth 10
    $json | Set-Content $mcpConfigPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "[OK] APIキーを設定しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "次のステップ" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "1. Cursorを再起動してください" -ForegroundColor White
    Write-Host "2. CursorでMCPサーバーに接続できるか確認してください" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[NG] n8n MCPサーバーの設定が見つかりません" -ForegroundColor Red
    Write-Host "先に add_to_cursor_mcp.ps1 を実行してください。" -ForegroundColor Yellow
    exit 1
}
















