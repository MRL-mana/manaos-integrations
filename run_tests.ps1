<#
.SYNOPSIS
    ManaOS テスト実行スクリプト

.DESCRIPTION
    ManaOSのテストを簡単に実行するためのPowerShellスクリプトです。

.PARAMETER TestType
    実行するテストタイプ（all, unit, integration, e2e）

.PARAMETER Coverage
    カバレッジレポートを生成するか

.PARAMETER Parallel
    並列実行するか

.PARAMETER Verbose
    詳細出力を有効にするか

.EXAMPLE
    .\run_tests.ps1 -TestType all -Coverage -Verbose

.EXAMPLE
    .\run_tests.ps1 -TestType unit -Parallel

.EXAMPLE
    .\run_tests.ps1 -TestType e2e
#>

param(
    [Parameter()]
    [ValidateSet("all", "unit", "integration", "e2e", "smoke")]
    [string]$TestType = "all",
    
    [Parameter()]
    [switch]$Coverage,
    
    [Parameter()]
    [switch]$Parallel,
    
    [Parameter()]
    [switch]$Verbose,
    
    [Parameter()]
    [switch]$FailFast,
    
    [Parameter()]
    [switch]$LastFailed,
    
    [Parameter()]
    [string]$Markers = "",
    
    [Parameter()]
    [string]$Keyword = ""
)

$ErrorActionPreference = "Stop"

# ===========================
# カラー出力ヘルパー
# ===========================

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $colors = @{
        "Red" = [ConsoleColor]::Red
        "Green" = [ConsoleColor]::Green
        "Yellow" = [ConsoleColor]::Yellow
        "Blue" = [ConsoleColor]::Blue
        "Cyan" = [ConsoleColor]::Cyan
        "White" = [ConsoleColor]::White
    }
    
    Write-Host $Message -ForegroundColor $colors[$Color]
}

# ===========================
# 前提条件チェック
# ===========================

Write-ColorOutput "🔍 前提条件をチェック中..." "Cyan"

# Python チェック
try {
    $pythonVersion = python --version 2>&1
    Write-ColorOutput "✅ Python: $pythonVersion" "Green"
} catch {
    Write-ColorOutput "❌ Pythonが見つかりません" "Red"
    exit 1
}

# pytest チェック
try {
    $pytestVersion = python -m pytest --version 2>&1
    Write-ColorOutput "✅ pytest: $pytestVersion" "Green"
} catch {
    Write-ColorOutput "⚠️  pytestが見つかりません。インストール中..." "Yellow"
    pip install -r requirements-test.txt
}

# ===========================
# テスト設定
# ===========================

$pytestArgs = @()

# テストタイプに応じたパス設定
switch ($TestType) {
    "unit" {
        Write-ColorOutput "🧪 ユニットテストを実行します" "Cyan"
        $pytestArgs += "tests/unit/"
        $pytestArgs += "-m", "unit"
    }
    "integration" {
        Write-ColorOutput "🔗 統合テストを実行します" "Cyan"
        $pytestArgs += "tests/integration/"
        $pytestArgs += "-m", "integration"
    }
    "e2e" {
        Write-ColorOutput "🚀 E2Eテストを実行します" "Cyan"
        $pytestArgs += "tests/e2e/"
        $pytestArgs += "-m", "e2e"
    }
    "smoke" {
        Write-ColorOutput "💨 スモークテストを実行します" "Cyan"
        $pytestArgs += "-m", "smoke"
    }
    "all" {
        Write-ColorOutput "🎯 全テストを実行します" "Cyan"
        $pytestArgs += "tests/"
    }
}

# 詳細出力
if ($Verbose) {
    $pytestArgs += "-vv"
} else {
    $pytestArgs += "-v"
}

# カバレッジ
if ($Coverage) {
    Write-ColorOutput "📊 カバレッジレポートを生成します" "Cyan"
    $pytestArgs += "--cov=."
    $pytestArgs += "--cov-report=html"
    $pytestArgs += "--cov-report=term"
    $pytestArgs += "--cov-report=xml"
}

# 並列実行
if ($Parallel) {
    Write-ColorOutput "⚡ 並列実行を有効化します" "Cyan"
    $pytestArgs += "-n", "auto"
}

# 最初の失敗で停止
if ($FailFast) {
    Write-ColorOutput "🛑 最初の失敗で停止します" "Cyan"
    $pytestArgs += "-x"
}

# 前回失敗したテストのみ
if ($LastFailed) {
    Write-ColorOutput "🔄 前回失敗したテストのみ実行します" "Cyan"
    $pytestArgs += "--lf"
}

# カスタムマーカー
if ($Markers -ne "") {
    Write-ColorOutput "🏷️  マーカー: $Markers" "Cyan"
    $pytestArgs += "-m", $Markers
}

# キーワードフィルタ
if ($Keyword -ne "") {
    Write-ColorOutput "🔍 キーワード: $Keyword" "Cyan"
    $pytestArgs += "-k", $Keyword
}

# 共通オプション
$pytestArgs += "--tb=short"
$pytestArgs += "--strict-markers"

# ===========================
# E2Eテストの場合、サービスチェック
# ===========================

if ($TestType -eq "e2e" -or $TestType -eq "all") {
    Write-ColorOutput "🔍 サービスの稼働状況をチェック中..." "Cyan"
    
    $services = @(
        @{Name="Unified API"; Url="http://localhost:9502/health"},
        @{Name="MRL Memory"; Url="http://localhost:9507/health"},
        @{Name="Learning System"; Url="http://localhost:9508/health"}
    )
    
    $allServicesRunning = $true
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-ColorOutput "  ✅ $($service.Name)" "Green"
            } else {
                Write-ColorOutput "  ⚠️  $($service.Name) (Status: $($response.StatusCode))" "Yellow"
                $allServicesRunning = $false
            }
        } catch {
            Write-ColorOutput "  ❌ $($service.Name) (Not running)" "Red"
            $allServicesRunning = $false
        }
    }
    
    if (-not $allServicesRunning) {
        Write-ColorOutput "`n⚠️  警告: すべてのサービスが起動していません" "Yellow"
        Write-ColorOutput "E2Eテストの一部が失敗する可能性があります`n" "Yellow"
        
        $response = Read-Host "続行しますか？ (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-ColorOutput "テストをキャンセルしました" "Yellow"
            exit 0
        }
    }
}

# ===========================
# テスト実行
# ===========================

Write-ColorOutput "`n▶️  テスト実行開始..." "Cyan"
Write-ColorOutput "コマンド: pytest $($pytestArgs -join ' ')`n" "Blue"

$startTime = Get-Date

try {
    # pytestを実行
    python -m pytest @pytestArgs
    $exitCode = $LASTEXITCODE
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    Write-ColorOutput "`n⏱️  実行時間: $([math]::Round($duration, 2))秒" "Cyan"
    
    if ($exitCode -eq 0) {
        Write-ColorOutput "✅ すべてのテストが成功しました！" "Green"
    } elseif ($exitCode -eq 1) {
        Write-ColorOutput "❌ テストが失敗しました" "Red"
    } elseif ($exitCode -eq 2) {
        Write-ColorOutput "⚠️  テスト実行が中断されました" "Yellow"
    } elseif ($exitCode -eq 3) {
        Write-ColorOutput "⚠️  内部エラーが発生しました" "Yellow"
    } elseif ($exitCode -eq 4) {
        Write-ColorOutput "⚠️  pytest使用エラー" "Yellow"
    } elseif ($exitCode -eq 5) {
        Write-ColorOutput "⚠️  テストが見つかりませんでした" "Yellow"
    }
    
} catch {
    Write-ColorOutput "`n❌ エラーが発生しました: $_" "Red"
    exit 1
}

# ===========================
# カバレッジレポート
# ===========================

if ($Coverage -and $exitCode -eq 0) {
    Write-ColorOutput "`n📊 カバレッジレポート" "Cyan"
    
    if (Test-Path "htmlcov/index.html") {
        Write-ColorOutput "HTMLレポート: htmlcov/index.html" "Green"
        
        $openReport = Read-Host "カバレッジレポートをブラウザで開きますか？ (y/N)"
        if ($openReport -eq "y" -or $openReport -eq "Y") {
            Start-Process "htmlcov/index.html"
        }
    }
    
    if (Test-Path "coverage.xml") {
        Write-ColorOutput "XMLレポート: coverage.xml" "Green"
    }
}

# ===========================
# 終了
# ===========================

exit $exitCode
