# Tool Server host start script (Windows)

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "Tool Server host start" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:PYTHONPATH) {
	$env:PYTHONPATH = "$scriptDir;$env:PYTHONPATH"
} else {
	$env:PYTHONPATH = $scriptDir
}
Set-Location $scriptDir
Set-Location "tool_server"

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting Tool Server..." -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:9503" -ForegroundColor Gray
Write-Host "  OpenAPI Spec: http://127.0.0.1:9503/openapi.json" -ForegroundColor Gray
Write-Host ""

python main.py
