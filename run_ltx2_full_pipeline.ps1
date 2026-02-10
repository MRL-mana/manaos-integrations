# LTX-2 I2V: ワークフロー変換 -> パッチ -> 生成送信 を一括実行
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$example = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\LTX-2_I2V_Distilled_wLora.json"
$expanded = Join-Path $root "ltx2_workflows\ltx2_i2v_expanded.json"
$ready = Join-Path $root "ltx2_workflows\ltx2_i2v_ready.json"

if (-not (Test-Path $example)) {
    Write-Host "Example workflow not found: $example"
    exit 1
}
New-Item -ItemType Directory -Force -Path (Join-Path $root "ltx2_workflows") | Out-Null

Write-Host "[1/3] Converting workflow (with subgraph expansion)..."
python "$root\ltx2_workflow_to_api.py" $example $expanded
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Patching node names..."
python "$root\ltx2_patch_workflow.py" $expanded $ready
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$prompt = if ($args.Count -gt 0) { $args[0] } else { "a calm sea, sunset" }
Write-Host "[3/3] Submitting to ComfyUI (prompt: $prompt)..."
python "$root\run_ltx2_generate.py" --workflow $ready --no-wait --prompt $prompt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Check ComfyUI queue/history for output."
