# n8n MCPサーバーのモジュールパス問題を修正

Write-Host "=" * 60
Write-Host "n8n MCPサーバー モジュールパス修正スクリプト"
Write-Host "=" * 60
Write-Host ""

$configPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
$workspacePath = "C:\Users\mana4\Desktop\manaos_integrations"

Write-Host "[1] 設定ファイルを読み込み中..." -ForegroundColor Yellow
Write-Host ""

if (-not (Test-Path $configPath)) {
    Write-Host "  ❌ 設定ファイルが見つかりません: $configPath" -ForegroundColor Red
    exit 1
}

try {
    $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    
    Write-Host "  ✅ 設定ファイルを読み込みました" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "[2] n8n設定を確認中..." -ForegroundColor Yellow
    Write-Host ""
    
    if (-not $config.mcpServers.n8n) {
        Write-Host "  ❌ n8n設定が見つかりません" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  現在の設定:" -ForegroundColor Cyan
    Write-Host "    cwd: $($config.mcpServers.n8n.cwd)" -ForegroundColor Gray
    Write-Host "    command: $($config.mcpServers.n8n.command)" -ForegroundColor Gray
    Write-Host "    args: $($config.mcpServers.n8n.args -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "[3] PYTHONPATHを追加して修正中..." -ForegroundColor Yellow
    Write-Host ""
    
    # PYTHONPATHを環境変数に追加
    if (-not $config.mcpServers.n8n.env) {
        $config.mcpServers.n8n | Add-Member -MemberType NoteProperty -Name "env" -Value @{}
    }
    
    # PYTHONPATHを設定（ワークスペースパスを追加）
    $pythonPath = $config.mcpServers.n8n.env.PYTHONPATH
    if ($pythonPath) {
        if ($pythonPath -notlike "*$workspacePath*") {
            $config.mcpServers.n8n.env.PYTHONPATH = "$pythonPath;$workspacePath"
        }
    } else {
        $config.mcpServers.n8n.env.PYTHONPATH = $workspacePath
    }
    
    # cwdも確認（念のため）
    if ($config.mcpServers.n8n.cwd -ne $workspacePath) {
        Write-Host "  ⚠️  cwdを更新します: $($config.mcpServers.n8n.cwd) → $workspacePath" -ForegroundColor Yellow
        $config.mcpServers.n8n.cwd = $workspacePath
    }
    
    Write-Host "  更新後の設定:" -ForegroundColor Cyan
    Write-Host "    cwd: $($config.mcpServers.n8n.cwd)" -ForegroundColor Gray
    Write-Host "    PYTHONPATH: $($config.mcpServers.n8n.env.PYTHONPATH)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "[4] 設定ファイルを保存中..." -ForegroundColor Yellow
    Write-Host ""
    
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $configPath -Encoding UTF8
    
    Write-Host "  ✅ 設定ファイルを更新しました" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "[5] モジュールの存在確認..." -ForegroundColor Yellow
    Write-Host ""
    
    $modulePath = "$workspacePath\n8n_mcp_server"
    if (Test-Path $modulePath) {
        Write-Host "  ✅ モジュールディレクトリが存在します: $modulePath" -ForegroundColor Green
        if (Test-Path "$modulePath\__init__.py") {
            Write-Host "  ✅ __init__.py が存在します" -ForegroundColor Green
        }
        if (Test-Path "$modulePath\server.py") {
            Write-Host "  ✅ server.py が存在します" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ モジュールディレクトリが見つかりません: $modulePath" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "=" * 60
    Write-Host "修正完了"
    Write-Host "=" * 60
    Write-Host ""
    Write-Host "[次のステップ]" -ForegroundColor Cyan
    Write-Host "1. Cursorを再起動してください" -ForegroundColor White
    Write-Host "2. 「Tools & MCP」→「Installed MCP Servers」で確認" -ForegroundColor White
    Write-Host "3. n8nのエラーが解消されていればOK" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "  ❌ エラー: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  $($_.ScriptStackTrace)" -ForegroundColor Gray
    exit 1
}
















