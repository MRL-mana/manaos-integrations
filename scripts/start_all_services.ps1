# =============================================================================
# ManaOS: start_all_services.ps1
# services_ledger.yaml をもとに全サービスを Tier0 → Tier1 → Tier2 の順で起動。
# 実体は tools/manaosctl.py に委譲（SSOT: config/services_ledger.yaml）
#
# Usage:
#   powershell scripts\start_all_services.ps1               # Tier0+1 のみ
#   powershell scripts\start_all_services.ps1 -All          # Tier2 含む全サービス
#   powershell scripts\start_all_services.ps1 -DryRun       # ドライラン
# =============================================================================
param(
    [switch]$All,
    [switch]$DryRun
)

$base = "C:\Users\mana4\Desktop\manaos_integrations"
$py   = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"
Set-Location $base

Write-Host "ManaOS start_all — 起動開始" -ForegroundColor Cyan
Write-Host "  SSOT: config/services_ledger.yaml" -ForegroundColor DarkGray

$cmd = '& "$py" tools\manaosctl.py up'
if ($All)    { $cmd += " --all" }
if ($DryRun) { $cmd += " --dry-run" }

Invoke-Expression $cmd

if (-not $DryRun) {
    Write-Host "`n起動完了。5秒後に blast_radius チェックを実行..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    & $py tools\check_blast_radius.py --live 2>&1 | Select-Object -Last 20
}


