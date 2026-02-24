param(
    [string]$MacroCmd = "Home",
    [string]$ExtrasJson = "{}",
    [ValidateSet('HTTPOnly','HTTPFirst')]
    [string]$Mode = 'HTTPOnly',
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = 'Stop'

$httpCtl = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$macroSendAutoPath = Join-Path $PSScriptRoot 'pixel7_macro_send_auto.ps1'

if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }
if (-not (Test-Path $macroSendAutoPath)) { throw "not found: $macroSendAutoPath" }

Write-Host '=== Pixel7 MacroDroid Probe ===' -ForegroundColor Cyan

Write-Host "\n[1] macro commands" -ForegroundColor Gray
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action MacroCommands -TimeoutSec $TimeoutSec | Out-Host
} catch {
    Write-Host ("NG: MacroCommands failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
}

Write-Host "\n[2] send cmd (may change phone UI): $MacroCmd" -ForegroundColor Gray
try {
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $macroSendAutoPath -MacroCmd $MacroCmd -ExtrasJson $ExtrasJson -Mode $Mode -TimeoutSec $TimeoutSec 2>&1 | Out-String
    $out.TrimEnd() | Out-Host

    if ($out -match '"ok"\s*:\s*true' -or $out -match '\bOK\b') {
        Write-Host 'OK' -ForegroundColor Green
        exit 0
    }

    Write-Host 'WARN: response did not clearly indicate ok; check Pixel screen / MacroDroid log' -ForegroundColor Yellow
    exit 1
} catch {
    Write-Host ("NG: send failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 2
}
