param(
    [string]$Question = "",
    [int]$WarmupSeconds = 1
)

$ErrorActionPreference = 'Stop'

if ($WarmupSeconds -lt 0) { $WarmupSeconds = 0 }
if ($WarmupSeconds -gt 10) { $WarmupSeconds = 10 }

if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = Read-Host 'Pixel7カメラに質問（例: これ何？ どこが壊れてる？ 何て書いてある？）'
}
if ([string]::IsNullOrWhiteSpace($Question)) {
    Write-Host 'Question is empty.' -ForegroundColor Yellow
    exit 2
}

Write-Host 'Opening camera...' -ForegroundColor Cyan
try {
    & "$PSScriptRoot\pixel7_open_camera.ps1" | Out-Null
} catch {
    # カメラが開けなくても、現状画面に対する質問として続行する
    Write-Host ('Camera open failed: {0}' -f $_.Exception.Message) -ForegroundColor Yellow
}

if ($WarmupSeconds -gt 0) {
    Start-Sleep -Seconds $WarmupSeconds
}

Write-Host 'Asking vision model about camera preview (via screenshot)...' -ForegroundColor Cyan
& "$PSScriptRoot\pixel7_ask_screen.ps1" -Question $Question
