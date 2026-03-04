param(
    [switch]$SkipFirewall
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptDir "start_tailscale_full_stack.ps1"
$logDir = Join-Path $scriptDir "logs"
$latestJson = Join-Path $logDir "tailscale_full_stack_keepalive.latest.json"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if (-not (Test-Path $startScript)) {
    throw "Required script not found: $startScript"
}

$cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $startScript)
if ($SkipFirewall.IsPresent) {
    $cmdArgs += '-SkipFirewall'
}

$startedAt = Get-Date
$ok = $true
$errorMessage = ''

try {
    & pwsh @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "start_tailscale_full_stack.ps1 failed (exit=$LASTEXITCODE)"
    }
}
catch {
    $ok = $false
    $errorMessage = $_.Exception.Message
}

$endedAt = Get-Date

$payload = [ordered]@{
    ts = (Get-Date -Format 's')
    started_at = $startedAt.ToString('s')
    ended_at = $endedAt.ToString('s')
    ok = $ok
    error = $errorMessage
    skip_firewall = [bool]$SkipFirewall.IsPresent
}

$payload | ConvertTo-Json -Depth 4 | Set-Content -Path $latestJson -Encoding UTF8

if ($ok) {
    Write-Host "[OK] Keepalive run succeeded" -ForegroundColor Green
    exit 0
}

Write-Host "[ERROR] Keepalive run failed: $errorMessage" -ForegroundColor Red
exit 1
