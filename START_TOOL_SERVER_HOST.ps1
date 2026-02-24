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

# Prefer workspace venv (Desktop\.venv) to keep deps isolated
$workspaceRoot = Split-Path -Parent $scriptDir
$venvPy = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
	& $venvPy -m pip install -r requirements.txt
} else {
	pip install -r requirements.txt
}

Write-Host ""
Write-Host "Starting Tool Server..." -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:9503" -ForegroundColor Gray
Write-Host "  OpenAPI Spec: http://127.0.0.1:9503/openapi.json" -ForegroundColor Gray
Write-Host ""

if (Test-Path $venvPy) {
	& $venvPy -u main.py
} else {
	python -u main.py
}
