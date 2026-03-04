# ============================================================
# start_castle_ex_layer2.ps1
# CASTLE-EX Layer2 推論サーバー起動スクリプト
# ============================================================
# 使い方:
#   powershell -ExecutionPolicy Bypass -File .\start_castle_ex_layer2.ps1
#   # プリロードあり（起動直後から推論できる）:
#   powershell -ExecutionPolicy Bypass -File .\start_castle_ex_layer2.ps1 -Preload
# ============================================================
param(
    [switch]$Preload,
    [int]$Port = 9520,
    [string]$Host = "127.0.0.1",
    [string]$Python = "py",
    [string]$PythonVersion = "-3.10"
)

$Root   = "C:\Users\mana4\Desktop\manaos_integrations"
$Script = "$Root\castle_ex\castle_ex_layer2_inference_server.py"
$LogDir = "$Root\logs"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force $LogDir | Out-Null }

$env:LAYER2_SERVER_PORT = $Port
$env:LAYER2_SERVER_HOST = $Host
if ($Preload) { $env:LAYER2_PRELOAD = "1" }

Write-Host "================================================================"
Write-Host " CASTLE-EX Layer2 推論サーバー起動"
Write-Host "   Port     : $Port"
Write-Host "   Host     : $Host"
Write-Host "   Preload  : $($Preload.IsPresent)"
Write-Host "   Script   : $Script"
Write-Host "================================================================"

& $Python $PythonVersion $Script
