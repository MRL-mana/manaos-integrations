# 安全なパッケージアップデートスクリプト
# UPGRADE_RECOMMENDATIONS.md に基づく推奨アップデートを実行

param(
    [ValidateSet("core", "langchain", "comfyui", "all")]
    [string]$Target = "core"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ManaOS パッケージアップデート（安全版）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: $Target" -ForegroundColor Yellow
Write-Host ""

$packages = @()

switch ($Target) {
    "core" {
        $packages = @("openai", "anthropic", "mcp", "aiohttp")
        Write-Host "コアパッケージ（LLM/MCP）をアップデートします" -ForegroundColor Green
    }
    "langchain" {
        $packages = @("langchain", "langchain-core", "langchain-openai")
        Write-Host "LangChain 関連をアップデートします" -ForegroundColor Green
    }
    "comfyui" {
        $packages = @("comfyui_frontend_package", "comfyui_workflow_templates")
        Write-Host "ComfyUI 関連をアップデートします" -ForegroundColor Green
    }
    "all" {
        $packages = @(
            "openai", "anthropic", "mcp", "aiohttp",
            "langchain", "langchain-core", "langchain-openai",
            "comfyui_frontend_package", "comfyui_workflow_templates"
        )
        Write-Host "全推奨パッケージをアップデートします" -ForegroundColor Green
    }
}

if ($packages.Count -eq 0) {
    Write-Host "アップデート対象がありません" -ForegroundColor Red
    exit 1
}

$packagesStr = $packages -join " "
Write-Host "実行: pip install --upgrade $packagesStr" -ForegroundColor Gray
Write-Host ""

try {
    pip install --upgrade $packages
    Write-Host ""
    Write-Host "アップデート完了" -ForegroundColor Green
} catch {
    Write-Host "エラー: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "メジャーアップ（transformers 5.x, MCP SDK 1.x）は手動で確認してください" -ForegroundColor Yellow
Write-Host "UPGRADE_RECOMMENDATIONS.md を参照" -ForegroundColor Gray
