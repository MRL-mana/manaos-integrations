# Quick local verification (lightweight)
# - No heavy generation, no OpenWebUI credentials required
# - Checks health + integration test + OpenAPI paths for LTX-2/Infinity

param(
    [string]$RepoRoot = "",
    [string]$PythonExe = "py",
    [string]$PythonArgs = "-3.10"
)

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Ok($msg) { Write-Host $msg -ForegroundColor Green }
function Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Ng($msg) { Write-Host $msg -ForegroundColor Red }

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

Set-Location $RepoRoot

Info "=== ManaOS quick verify (local) ==="
Info "RepoRoot: $RepoRoot"
Info ("Time: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))

try {
    Info "[1/3] Health checks (Unified API/Tool Server/ComfyUI/OpenWebUI)"
    pwsh -NoProfile -ExecutionPolicy Bypass -File .\check_all_services_status.ps1 | Out-Host
    Ok "health checks done"
}
catch {
    Warn "health checks script failed: $($_.Exception.Message)"
}

$integrationExit = 0
try {
    Info "[2/3] Integration test (Tool Server + ComfyUI + optional OpenWebUI)"
    & $PythonExe $PythonArgs .\tests\integration\test_tool_server_integration.py
    $integrationExit = $LASTEXITCODE
    if ($integrationExit -eq 0) {
        Ok "integration test PASSED"
    }
    else {
        Ng "integration test FAILED (exit=$integrationExit)"
    }
}
catch {
    $integrationExit = 1
    Ng "integration test crashed: $($_.Exception.Message)"
}

try {
    Info "[3/3] Unified API OpenAPI paths (LTX-2/Infinity)"
    $base = if ($env:UNIFIED_API_URL) { $env:UNIFIED_API_URL.TrimEnd('/') } else { "http://127.0.0.1:9502" }
    $spec = Invoke-RestMethod "$base/openapi.json" -TimeoutSec 5
    $paths = @()
    if ($spec -and $spec.paths) {
        $paths = $spec.paths.PSObject.Properties.Name
    }
    $required = @(
        "/api/ltx2/generate",
        "/api/ltx2/queue",
        "/api/ltx2/history",
        "/api/ltx2-infinity/generate",
        "/api/ltx2-infinity/templates",
        "/api/ltx2-infinity/storage"
    )
    $missing = @($required | Where-Object { $_ -notin $paths })
    if ($missing.Count -eq 0) {
        Ok "OpenAPI contains LTX-2/Infinity paths"
    }
    else {
        Warn ("OpenAPI missing paths: " + ($missing -join ", "))
    }
}
catch {
    Warn "OpenAPI check failed: $($_.Exception.Message)"
}

Info "=== Summary ==="
if ($integrationExit -eq 0) {
    Ok "OK (integration test passed)"
    exit 0
}

Ng "NG (integration test failed)"
exit $integrationExit
