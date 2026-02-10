# validation_script.ps1
# VSCode設定の自動検証スクリプト

Write-Host "=== ManaOS VSCode設定検証スクリプト ===" -ForegroundColor Cyan
Write-Host "実行時刻: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor Gray

$totalChecks = 0
$passedChecks = 0
$failedChecks = 0
$warningChecks = 0

# 1. 必須ファイルの存在確認
Write-Host "[1] 必須ファイルの確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$requiredFiles = @(
    ".vscode\extensions.json",
    ".vscode\settings.json.workspace",
    ".vscode\tasks.json",
    ".vscode\launch.json",
    ".vscode\python.code-snippets"
)

foreach ($file in $requiredFiles) {
    $totalChecks++
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
        $passedChecks++
    } else {
        Write-Host "  ❌ $file (存在しない)" -ForegroundColor Red
        $failedChecks++
    }
}

# 2. ドキュメントの存在確認
Write-Host "`n[2] ドキュメントの確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$docs = @(
    "README.md",
    "QUICKREF.md",
    "VSCODE_SETUP_GUIDE.md",
    "VSCODE_VS_CURSOR.md",
    "VSCODE_CHECKLIST.md",
    "VSCODE_TEST_CHECKLIST.md",
    "SNIPPETS_GUIDE.md",
    "STARTUP_GUIDE.md",
    "SYSTEM3_GUIDE.md",
    "EMERGENCY_STOP_GUIDE.md",
    "FAQ.md",
    "CONTRIBUTING.md",
    "PERFORMANCE_MONITORING.md"
)

foreach ($doc in $docs) {
    $totalChecks++
    if (Test-Path $doc) {
        $fileSize = (Get-Item $doc).Length
        Write-Host "  ✅ $doc ($fileSize bytes)" -ForegroundColor Green
        $passedChecks++
    } else {
        Write-Host "  ❌ $doc (存在しない)" -ForegroundColor Red
        $failedChecks++
    }
}

# 3. Python環境の確認
Write-Host "`n[3] Python環境の確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalChecks++
if (Test-Path "..\.venv\Scripts\python.exe") {
    $pythonVersion = & ..\.venv\Scripts\python.exe --version 2>&1
    Write-Host "  ✅ Python venv存在: $pythonVersion" -ForegroundColor Green
    $passedChecks++
} else {
    Write-Host "  ❌ Python venv が見つからない" -ForegroundColor Red
    $failedChecks++
}

# 3-1. 重要なPythonモジュールの確認
$totalChecks++
try {
    & ..\ 重要なPythonモジュールの確認
$totalChecks++
try {
    & .venv\Scripts\python.exe -c "import fastapi; import uvicorn; import requests" 2>$null
    Write-Host "  ✅ 必須Pythonパッケージ: インストール済み" -ForegroundColor Green
    $passedChecks++
} catch {
    Write-Host "  ⚠️  必須Pythonパッケージ: 一部不足の可能性" -ForegroundColor Yellow
    $warningChecks++
}

# 4. ManaOSサービススクリプトの確認
Write-Host "`n[4] ManaOSサービススクリプトの確認" -ForegroundColor Yellow
Writestart_vscode_cursor_services.py",
    "check_services_health.py",
    "autonomous_operations.py",
    "start_vscode_cursor_services.py",
    "manaos_integrations\check_services_health.py",
    "manaos_integrations\autonomous_operations.py",
    "manaos_integrations\emergency_stop.py"
)

foreach ($script in $serviceScripts) {
    $totalChecks++
    if (Test-Path $script) {
        Write-Host "  ✅ $script" -ForegroundColor Green
        $passedChecks++
    } else {
        Write-Host "  ❌ $script (存在しない)" -ForegroundColor Red
        $failedChecks++
    }
}

# 5. サービスの起動確認（ポートリスニング）
Write-Host "`n[5] サービス起動状態の確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$services = @(
    @{Port=9500; Name="Unified API"},
    @{Port=5111; Name="LLM Routing"},
    @{Port=5104; Name="Learning System"},
    @{Port=5103; Name="MRL Memory"}
)

foreach ($service in $services) {
    $totalChecks++
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  ✅ Port $($service.Port) ($($service.Name)): $($response.status)" -ForegroundColor Green
        $passedChecks++
    } catch {
        Write-Host "  ⚠️  Port $($service.Port) ($($service.Name)): 応答なし（未起動またはエラー）" -ForegroundColor Yellow
        $warningChecks++
    }
}

# 6. JSONファイルの構文確認
Write-Host "`n[6] JSON設定ファイルの構文確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$jsonFiles = @(
    ".vscode\extensions.json",
    ".vscode\tasks.json",
    ".vscode\launch.json",
    ".vscode\python.code-snippets"
)

foreach ($jsonFile in $jsonFiles) {
    $totalChecks++
    if (Test-Path $jsonFile) {
        try {
            $content = Get-Content $jsonFile -Raw | ConvertFrom-Json -ErrorAction Stop
            Write-Host "  ✅ $jsonFile : 有効なJSON" -ForegroundColor Green
            $passedChecks++
        } catch {
            Write-Host "  ❌ $jsonFile : JSON構文エラー" -ForegroundColor Red
            Write-Host "     エラー: $($_.Exception.Message)" -ForegroundColor Red
            $failedChecks++
        }
    }
}

# 7. タスク定義の確認
Write-Host "`n[7] VSCodeタスク定義の確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalChecks++
try {
    $tasksJson = Get-Content ".vscode\tasks.json" -Raw | ConvertFrom-Json
    $taskCount = $tasksJson.tasks.Count
    Write-Host "  ✅ タスク定義数: $taskCount 個" -ForegroundColor Green
    
    foreach ($task in $tasksJson.tasks) {
        Write-Host "     - $($task.label)" -ForegroundColor Gray
    }
    $passedChecks++
} catch {
    Write-Host "  ❌ タスク定義の読み込みエラー" -ForegroundColor Red
    $failedChecks++
}

# 8. デバッグ構成の確認
Write-Host "`n[8] VSCodeデバッグ構成の確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalChecks++
try {
    $launchJson = Get-Content ".vscode\launch.json" -Raw | ConvertFrom-Json
    $configCount = $launchJson.configurations.Count
    Write-Host "  ✅ デバッグ構成数: $configCount 個" -ForegroundColor Green
    
    foreach ($config in $launchJson.configurations) {
        Write-Host "     - $($config.name)" -ForegroundColor Gray
    }
    $passedChecks++
} catch {
    Write-Host "  ❌ デバッグ構成の読み込みエラー" -ForegroundColor Red
    $failedChecks++
}

# 9. スニペットの確認
Write-Host "`n[9] コードスニペットの確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalChecks++
if (Test-Path ".vscode\python.code-snippets") {
    try {
        $snippetsJson = Get-Content ".vscode\python.code-snippets" -Raw | ConvertFrom-Json
        $snippetCount = ($snippetsJson | Get-Member -MemberType NoteProperty).Count
        Write-Host "  ✅ スニペット数: $snippetCount 個" -ForegroundColor Green
        
        foreach ($snippet in ($snippetsJson | Get-Member -MemberType NoteProperty)) {
            $prefix = $snippetsJson.($snippet.Name).prefix
            Write-Host "     - $($snippet.Name) ($prefix)" -ForegroundColor Gray
        }
        $passedChecks++
    } catch {
        Write-Host "  ❌ スニペットの読み込みエラー" -ForegroundColor Red
        $failedChecks++
    }
} else {
    Write-Host "  ⚠️  python.code-snippets not found" -ForegroundColor Yellow
    $warningChecks++
}

# 10. GitHubリポジトリの確認
Write-Host "`n[10] Gitリポジトリの確認" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalChecks++
if (Test-Path ".git") {
    try {
        $gitStatus = git status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Gitリポジトリ: 初期化済み" -ForegroundColor Green
            $branchInfo = git branch --show-current 2>&1
            Write-Host "     現在のブランチ: $branchInfo" -ForegroundColor Gray
            $passedChecks++
        } else {
            Write-Host "  ⚠️  Gitリポジトリ: エラー" -ForegroundColor Yellow
            $warningChecks++
        }
    } catch {
        Write-Host "  ⚠️  Git未インストールまたはパス未設定" -ForegroundColor Yellow
        $warningChecks++
    }
} else {
    Write-Host "  ⚠️  .git ディレクトリが見つからない" -ForegroundColor Yellow
    $warningChecks++
}

# 結果サマリー
Write-Host "`n" -NoNewline
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "             検証結果サマリー              " -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$successRate = [math]::Round(($passedChecks / $totalChecks) * 100, 1)

Write-Host "`n  総チェック数: $totalChecks" -ForegroundColor White
Write-Host "  ✅ 成功: $passedChecks" -ForegroundColor Green
Write-Host "  ⚠️  警告: $warningChecks" -ForegroundColor Yellow
Write-Host "  ❌ 失敗: $failedChecks" -ForegroundColor Red
Write-Host "`n  成功率: $successRate%" -ForegroundColor $(if ($successRate -ge 90) { "Green" } elseif ($successRate -ge 70) { "Yellow" } else { "Red" })

if ($failedChecks -eq 0) {
    Write-Host "`n  🎉 すべての必須チェックに合格しました！" -ForegroundColor Green
} elseif ($failedChecks -le 2) {
    Write-Host "`n  ⚠️  いくつかの問題がありますが、基本的に動作します" -ForegroundColor Yellow
} else {
    Write-Host "`n  ❌ 重大な問題があります。セットアップを確認してください" -ForegroundColor Red
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# 推奨アクション
if ($failedChecks -gt 0 -or $warningChecks -gt 0) {
    Write-Host "📋 推奨アクション:" -ForegroundColor Yellow
    
    if ($failedChecks -gt 0) {
        Write-Host "  1. VSCODE_SETUP_GUIDE.md を参照してセットアップを完了してください" -ForegroundColor White
        Write-Host "  2. 不足しているファイルを確認してください" -ForegroundColor White
    }
    
    if ($warningChecks -gt 0) {
        Write-Host "  3. サービスが起動していない場合: Ctrl+Shift+B でサービスを起動" -ForegroundColor White
        Write-Host "  4. STARTUP_GUIDE.md を参照して起動手順を確認" -ForegroundColor White
    }
    
    Write-Host ""
}

# ログファイルに保存
$logFile = "manaos_integrations\validation_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$logContent = @"
ManaOS VSCode設定検証ログ
実行時刻: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
検証結果サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

総チェック数: $totalChecks
成功: $passedChecks
警告: $warningChecks
失敗: $failedChecks
成功率: $successRate%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"@

$logContent | Out-File -FilePath $logFile -Encoding UTF8
Write-Host "📄 検証ログを保存しました: $logFile" -ForegroundColor Gray
