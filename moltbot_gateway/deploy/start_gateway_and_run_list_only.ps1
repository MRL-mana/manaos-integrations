# 母艦で一発: Gateway を起動して list_only runner を実行（このはは使わない）
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\start_gateway_and_run_list_only.ps1

$ErrorActionPreference = "Stop"
$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq "deploy") { Set-Location ..\.. }
$repoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $repoRoot "manaos_moltbot_runner.py"))) {
    Write-Host "Error: run from repo root (or deploy/) so manaos_moltbot_runner.py is found."
    exit 1
}

$env:MOLTBOT_GATEWAY_DATA_DIR = "moltbot_gateway_data"
$env:MOLTBOT_GATEWAY_SECRET = "local_secret"
$env:MOLTBOT_GATEWAY_URL = "http://127.0.0.1:8088"

Write-Host "Gateway を起動中 (127.0.0.1:8088)... (gateway_production.env があれば本物接続)"
$job = Start-Job -ScriptBlock {
    Set-Location $using:repoRoot
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1" 2>&1
}
Start-Sleep -Seconds 4

Write-Host "list_only runner を実行..."
python manaos_moltbot_runner.py list_only
$runResult = $LASTEXITCODE

Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -Force -ErrorAction SilentlyContinue

if ($runResult -eq 0) { Write-Host "OK. moltbot_audit に監査が増えています。" } else { Write-Host "runner が異常終了しました。" }
exit $runResult
