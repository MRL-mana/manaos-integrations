# ManaOS統合サービス クイックセットアップスクリプト
# すべてのセットアップ手順を自動実行

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ManaOS統合サービス クイックセットアップ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$projectPath = "C:\Users\mana4\Desktop\manaos_integrations"
Set-Location $projectPath

# ステップ1: MCPサーバーの依存関係をインストール
Write-Host "[ステップ1] MCPサーバーの依存関係をインストール..." -ForegroundColor Yellow
try {
    pip install mcp requests --quiet
    Write-Host "   [OK] 依存関係のインストールが完了しました" -ForegroundColor Green
} catch {
    Write-Host "   [NG] 依存関係のインストールに失敗しました" -ForegroundColor Red
    Write-Host "   エラー: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ステップ2: Cursor MCP設定を追加
Write-Host "[ステップ2] Cursor MCP設定を追加..." -ForegroundColor Yellow
if (Test-Path ".\add_all_mcp_servers_to_cursor.ps1") {
    try {
        & ".\add_all_mcp_servers_to_cursor.ps1"
        Write-Host "   [OK] MCP設定の追加が完了しました" -ForegroundColor Green
    } catch {
        Write-Host "   [NG] MCP設定の追加に失敗しました" -ForegroundColor Red
        Write-Host "   エラー: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   [警告] add_all_mcp_servers_to_cursor.ps1 が見つかりません" -ForegroundColor Yellow
    Write-Host "   手動で設定してください: .cursor/mcp.json" -ForegroundColor Gray
}

Write-Host ""

# ステップ3: Dockerサービスを起動
Write-Host "[ステップ3] Dockerサービスを起動..." -ForegroundColor Yellow
Write-Host "   Docker Composeでサービスを起動しますか？ (Y/N)" -ForegroundColor Cyan
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    try {
        docker-compose -f docker-compose.manaos-services.yml up -d
        Write-Host "   [OK] Dockerサービスの起動が完了しました" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "   サービス状態を確認中..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        docker-compose -f docker-compose.manaos-services.yml ps
    } catch {
        Write-Host "   [NG] Dockerサービスの起動に失敗しました" -ForegroundColor Red
        Write-Host "   エラー: $_" -ForegroundColor Red
        Write-Host "   手動で起動してください: docker-compose -f docker-compose.manaos-services.yml up -d" -ForegroundColor Yellow
    }
} else {
    Write-Host "   [スキップ] Dockerサービスの起動をスキップしました" -ForegroundColor Yellow
    Write-Host "   後で手動で起動してください: docker-compose -f docker-compose.manaos-services.yml up -d" -ForegroundColor Gray
}

Write-Host ""

# ステップ4: テスト実行
Write-Host "[ステップ4] サービスをテスト..." -ForegroundColor Yellow
Write-Host "   テストを実行しますか？ (Y/N)" -ForegroundColor Cyan
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    if (Test-Path ".\test_all_services.ps1") {
        try {
            & ".\test_all_services.ps1"
        } catch {
            Write-Host "   [NG] テストの実行に失敗しました" -ForegroundColor Red
            Write-Host "   エラー: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "   [警告] test_all_services.ps1 が見つかりません" -ForegroundColor Yellow
    }
} else {
    Write-Host "   [スキップ] テストをスキップしました" -ForegroundColor Yellow
    Write-Host "   後で手動で実行してください: .\test_all_services.ps1" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "セットアップ完了！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Cyan
Write-Host "1. Cursorを再起動してください" -ForegroundColor White
Write-Host "2. MCPサーバーが利用可能か確認してください" -ForegroundColor White
Write-Host "3. 各APIサービスが起動していることを確認してください" -ForegroundColor White
Write-Host ""
Write-Host "[確認方法]" -ForegroundColor Cyan
Write-Host "docker-compose -f docker-compose.manaos-services.yml ps" -ForegroundColor Gray
Write-Host ".\test_all_services.ps1" -ForegroundColor Gray
Write-Host ""
