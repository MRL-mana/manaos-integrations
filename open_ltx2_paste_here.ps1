# ltx2_workflows フォルダを開く（ここに Export JSON を貼り付けて ltx2_i2v_from_ui.json にリネーム）
$dest = Join-Path $PSScriptRoot "ltx2_workflows"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
explorer $dest
Write-Host "Opened: $dest"
Write-Host "Paste your Export (API) JSON here and rename to: ltx2_i2v_from_ui.json"
Write-Host "Then run: .\run_ltx2_all.ps1"
