# LTX-2 環境診断: 接続・ノード一覧・互換ワークフローを一括実行
# 使い方: .\run_ltx2_diagnose.ps1
#        .\run_ltx2_diagnose.ps1 -ComfyUrl "http://192.168.1.10:8188"
param(
    [string]$ComfyUrl = "http://127.0.0.1:8188"
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$env:COMFYUI_URL = $ComfyUrl

Write-Host "=== LTX-2 診断 (ComfyUI: $ComfyUrl) ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. I2V 必須ノードの有無チェック" -ForegroundColor Yellow
python ltx2_workflow_compat_check.py
$compatExit = $LASTEXITCODE
Write-Host ""

Write-Host "2. 利用可能な LTX/動画関連ノード一覧" -ForegroundColor Yellow
python ltx2_list_available_nodes.py
Write-Host ""

$examplePath = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows"
Write-Host "3. 互換ワークフローの検出 (example_workflows)" -ForegroundColor Yellow
if (Test-Path $examplePath) {
    python ltx2_find_compatible_workflow.py $examplePath
} else {
    python ltx2_find_compatible_workflow.py
}
Write-Host ""

Write-Host "=== 診断完了 ===" -ForegroundColor Cyan
if ($compatExit -ne 0) {
    Write-Host "不足ノードがあります。LTX2_NODE_MISMATCH.md を参照してください。" -ForegroundColor Magenta
}
exit $compatExit
