# Export (API) で保存した JSON を ltx2_workflows にコピーする
# 使い方: .\copy_ltx2_export.ps1 "C:\Users\mana4\Downloads\LTX-2_T2V_Distilled_wLora.json"
#         （ダウンロード先など、実際に保存したファイルのパスを指定）
$src = $args[0]
if (-not $src -or -not (Test-Path $src)) {
    Write-Host "Usage: .\copy_ltx2_export.ps1 ""path\to\exported.json"""
    Write-Host "Example: .\copy_ltx2_export.ps1 ""C:\Users\mana4\Downloads\api.json"""
    exit 1
}
$dest = Join-Path $PSScriptRoot "ltx2_workflows\ltx2_i2v_from_ui.json"
$dir = Split-Path $dest -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
Copy-Item -Path $src -Destination $dest -Force
Write-Host "Copied to: $dest"
Write-Host "Run: .\run_ltx2_all.ps1"
