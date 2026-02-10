Param()
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

if (-not $env:CURSOR_WEBHOOK_SECRET) {
    Write-Host "Warning: CURSOR_WEBHOOK_SECRET not set — running insecurely" -ForegroundColor Yellow
}

Write-Host "Starting webhook (background)..."
$p = Start-Process -FilePath python -ArgumentList "manaos_integrations\cursor_webhook.py" -PassThru
Start-Sleep -Seconds 1

Write-Host "Sending signed request (1)"
& python "manaos_integrations\send_cursor_webhook.py"
Start-Sleep -Seconds 1

Write-Host "Sending signed request (2)"
& python "manaos_integrations\send_cursor_webhook.py"
Start-Sleep -Seconds 1

Write-Host "Stopping webhook"
try { Stop-Process -Id $p.Id -Force } catch {}

Pop-Location
Write-Host "Done"
