# テストファイル整理スクリプト
# すべてのtest_*.pyファイルを適切なカテゴリに移動します

$ErrorActionPreference = "Stop"

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        ManaOS テストファイル整理ツール                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ディレクトリ作成
$testDirs = @("unit", "integration", "e2e", "performance", "fixtures")
foreach ($dir in $testDirs) {
    $path = "tests\$dir"
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "✅ $path ディレクトリを作成" -ForegroundColor Green
    }
}

Write-Host ""

# テストファイルの分類定義
$unitTests = @(
    "test_config_validator_usage",
    "test_error_handler_usage",
    "test_logger_usage",
    "test_timeout_config_usage",
    "test_japanese_ocr",
    "test_ocr",
    "test_vision_llm_simple",
    "test_excel_vision_simple",
    "test_prompt_generation"
)

$integrationTests = @(
    "test_all_apis",
    "test_all_integrations",
    "test_all_services",
    "test_integration",
    "test_integration_all",
    "test_integration_flow",
    "test_manaos_integration",
    "test_manaos_integration_complete",
    "test_llm_routing",
    "test_llm_routing_mcp",
    "test_mrl_memory_integration",
    "test_slack_integration",
    "test_brave_search",
    "test_github_integration",
    "test_oh_my_opencode_integration",
    "test_svi_integration"
)

$e2eTests = @(
    "test_all_features",
    "test_complete",
    "test_ultimate",
    "test_ultra_integrated",
    "test_final_checklist",
    "test_final_checklist_stable",
    "test_services_quick",
    "test_service_health_checks"
)

$performanceTests = @(
    "test_gpu_performance",
    "test_gpu_usage",
    "test_llm_fix"
)

# テストファイルを移動
function Move-TestFile {
    param(
        [string]$FileName,
        [string]$Category
    )
    
    $sourceFile = "$FileName.py"
    if (Test-Path $sourceFile) {
        Move-Item -Path $sourceFile -Destination "tests\$Category\$sourceFile" -Force
        Write-Host "  📦 $sourceFile → tests\$Category\" -ForegroundColor Gray
        return $true
    }
    return $false
}

$movedCount = 0
$totalCount = 0

Write-Host "Unit Tests の移動..." -ForegroundColor Yellow
foreach ($test in $unitTests) {
    $totalCount++
    if (Move-TestFile -FileName $test -Category "unit") {
        $movedCount++
    }
}

Write-Host ""
Write-Host "Integration Tests の移動..." -ForegroundColor Yellow
foreach ($test in $integrationTests) {
    $totalCount++
    if (Move-TestFile -FileName $test -Category "integration") {
        $movedCount++
    }
}

Write-Host ""
Write-Host "E2E Tests の移動..." -ForegroundColor Yellow
foreach ($test in $e2eTests) {
    $totalCount++
    if (Move-TestFile -FileName $test -Category "e2e") {
        $movedCount++
    }
}

Write-Host ""
Write-Host "Performance Tests の移動..." -ForegroundColor Yellow
foreach ($test in $performanceTests) {
    $totalCount++
    if (Move-TestFile -FileName $test -Category "performance") {
        $movedCount++
    }
}

Write-Host ""
Write-Host "残りのtest_*.pyファイルをintegrationに移動..." -ForegroundColor Yellow
$remainingTests = Get-ChildItem -Path "." -Filter "test_*.py" | Where-Object { -not $_.PSIsContainer }
foreach ($file in $remainingTests) {
    Move-Item -Path $file.FullName -Destination "tests\integration\$($file.Name)" -Force
    Write-Host "  📦 $($file.Name) → tests\integration\" -ForegroundColor Gray
    $movedCount++
    $totalCount++
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "移動完了: $movedCount / $totalCount ファイル" -ForegroundColor Green
Write-Host ""
Write-Host "ディレクトリ構造:" -ForegroundColor Yellow
Get-ChildItem "tests" -Recurse -Filter "*.py" | Group-Object Directory | ForEach-Object {
    $dirName = Split-Path $_.Name -Leaf
    Write-Host "  $dirName : $($_.Count) ファイル" -ForegroundColor Cyan
}
Write-Host ""
