param(
    [string]$BindAddress = "127.0.0.1",
    [int]$BackendPort = 9510,
    [int]$FrontendPort = 5173,
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = "",
    [int]$MaxHistoryLines = 1000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\rpg_full_health_chain.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\rpg_full_health_chain.history.jsonl"
}
if ($MaxHistoryLines -lt 1) {
    throw "MaxHistoryLines must be >= 1"
}

$recoverScript = Join-Path $scriptDir "recover_manaos_rpg_backend.ps1"
$statusFrontendScript = Join-Path $scriptDir "status_manaos_rpg_frontend.ps1"
$startFrontendScript = Join-Path $scriptDir "start_manaos_rpg_frontend.ps1"

foreach ($required in @($recoverScript, $statusFrontendScript, $startFrontendScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$StepValues,
        [int[]]$ExpectedExitCodes = @(0)
    )

    $commandValues = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $StepValues
    $output = @(& pwsh @commandValues 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = [int]$LASTEXITCODE
    $ok = ($ExpectedExitCodes -contains $exitCode)

    [pscustomobject]@{
        name = $Name
        script = $ScriptPath
        values = $StepValues
        exit_code = $exitCode
        ok = $ok
        output_tail = @($output | Select-Object -Last 20)
    }
}

$latestDir = Split-Path -Parent $LatestJsonFile
if ($latestDir -and -not (Test-Path $latestDir)) {
    New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
}
$historyDir = Split-Path -Parent $HistoryJsonl
if ($historyDir -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
}

$steps = New-Object System.Collections.Generic.List[object]
$steps.Add((Invoke-Step -Name 'backend_recover' -ScriptPath $recoverScript -StepValues @('-BindAddress', $BindAddress, '-Port', "$BackendPort", '-RequirePass')))
$steps.Add((Invoke-Step -Name 'frontend_status_before' -ScriptPath $statusFrontendScript -StepValues @('-BindAddress', $BindAddress, '-Port', "$FrontendPort", '-AsJson')))

$frontendPass = $false
try {
    $frontJson = (($steps[1].output_tail -join "`n") | ConvertFrom-Json)
    $frontendPass = [bool]$frontJson.pass
}
catch {
    $frontendPass = $false
}

if (-not $frontendPass) {
    $steps.Add((Invoke-Step -Name 'frontend_start' -ScriptPath $startFrontendScript -StepValues @('-BindAddress', $BindAddress, '-Port', "$FrontendPort") -ExpectedExitCodes @(0)))
}

$steps.Add((Invoke-Step -Name 'frontend_status_require_pass' -ScriptPath $statusFrontendScript -StepValues @('-BindAddress', $BindAddress, '-Port', "$FrontendPort", '-RequirePass')))

$failed = @($steps | Where-Object { -not $_.ok })
$ok = ($failed.Count -eq 0)
$okReason = if ($ok) { 'rpg_full_health_chain_passed' } else { 'rpg_full_health_chain_failed' }

$payload = [ordered]@{
    ts = [datetimeoffset]::Now.ToString('o')
    host = $BindAddress
    backend_port = $BackendPort
    frontend_port = $FrontendPort
    ok = $ok
    ok_reason = $okReason
    failed_step_count = $failed.Count
    failed_steps = @($failed | ForEach-Object { [string]$_.name })
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    steps = $steps.ToArray()
}

($payload | ConvertTo-Json -Depth 10) | Set-Content -Path $LatestJsonFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8

try {
    $historyLines = Get-Content -Path $HistoryJsonl
    if ($historyLines.Count -gt $MaxHistoryLines) {
        $historyLines | Select-Object -Last $MaxHistoryLines | Set-Content -Path $HistoryJsonl -Encoding UTF8
    }
}
catch {
}

Write-Host "=== RPG Full Health Chain ===" -ForegroundColor Cyan
Write-Host "ok: $ok" -ForegroundColor Gray
Write-Host "ok_reason: $okReason" -ForegroundColor Gray
Write-Host "failed_step_count: $($failed.Count)" -ForegroundColor Gray

if ($ok) {
    Write-Host "[OK] RPG full health chain completed" -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] RPG full health chain failed" -ForegroundColor Red
$failed | ForEach-Object {
    Write-Host ("[FAILED] {0} exit={1}" -f $_.name, $_.exit_code) -ForegroundColor Red
}
exit 1
