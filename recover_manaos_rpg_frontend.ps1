param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 5173,
    [switch]$AsJson,
    [switch]$RequirePass
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$doctorScript = Join-Path $scriptDir "doctor_manaos_rpg_frontend_port.ps1"
$stopScript = Join-Path $scriptDir "stop_manaos_rpg_frontend.ps1"
$startScript = Join-Path $scriptDir "start_manaos_rpg_frontend.ps1"
$statusScript = Join-Path $scriptDir "status_manaos_rpg_frontend.ps1"

foreach ($required in @($doctorScript, $stopScript, $startScript, $statusScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$StepParameters,
        [int[]]$ExpectedExitCodes = @(0)
    )

    $commandParameters = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $StepParameters
    $output = @(& pwsh @commandParameters 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = [int]$LASTEXITCODE
    $ok = ($ExpectedExitCodes -contains $exitCode)

    [pscustomobject]@{
        name = $Name
        script = $ScriptPath
        parameters = $StepParameters
        exit_code = $exitCode
        ok = $ok
        output_tail = @($output | Select-Object -Last 20)
    }
}

$steps = New-Object System.Collections.Generic.List[object]
$steps.Add((Invoke-Step -Name 'doctor_before' -ScriptPath $doctorScript -StepParameters @('-BindAddress', $BindAddress, '-Port', "$Port", '-AsJson') -ExpectedExitCodes @(0)))

$doctorBeforeJson = $null
try {
    $doctorBeforeJson = (($steps[0].output_tail -join "`n") | ConvertFrom-Json)
}
catch {
}

$needsRecovery = $true
if ($null -ne $doctorBeforeJson -and (@('ok', 'healthy_listener_unclassified') -contains [string]$doctorBeforeJson.ok_reason)) {
    $needsRecovery = $false
}

if ($needsRecovery) {
    $steps.Add((Invoke-Step -Name 'stop' -ScriptPath $stopScript -StepParameters @('-Port', "$Port") -ExpectedExitCodes @(0)))
    Start-Sleep -Milliseconds 500
    $steps.Add((Invoke-Step -Name 'start' -ScriptPath $startScript -StepParameters @('-BindAddress', $BindAddress, '-Port', "$Port") -ExpectedExitCodes @(0)))
}

$steps.Add((Invoke-Step -Name 'doctor_after' -ScriptPath $doctorScript -StepParameters @('-BindAddress', $BindAddress, '-Port', "$Port", '-AsJson') -ExpectedExitCodes @(0)))
$steps.Add((Invoke-Step -Name 'status_require_pass' -ScriptPath $statusScript -StepParameters @('-BindAddress', $BindAddress, '-Port', "$Port", '-RequirePass') -ExpectedExitCodes @(0)))

$failed = @($steps | Where-Object { -not $_.ok })
$ok = ($failed.Count -eq 0)
$okReason = if ($ok) { 'recover_ok' } else { 'recover_failed' }

$payload = [ordered]@{
    ts = [datetimeoffset]::Now.ToString('o')
    host = $BindAddress
    port = $Port
    attempted_recovery = $needsRecovery
    ok = $ok
    ok_reason = $okReason
    failed_step_count = $failed.Count
    failed_steps = @($failed | ForEach-Object { [string]$_.name })
    steps = $steps.ToArray()
}

if ($AsJson) {
    $payload.require_pass = [bool]$RequirePass
    $payload.pass = $ok
    Write-Output ($payload | ConvertTo-Json -Depth 10)
    if ($RequirePass.IsPresent -and -not $ok) {
        exit 1
    }
    exit 0
}

Write-Host "=== ManaOS RPG Frontend Recover ===" -ForegroundColor Cyan
Write-Host "host: $BindAddress" -ForegroundColor Gray
Write-Host "port: $Port" -ForegroundColor Gray
Write-Host "attempted_recovery: $needsRecovery" -ForegroundColor Gray
Write-Host "ok: $ok" -ForegroundColor Gray
Write-Host "ok_reason: $okReason" -ForegroundColor Gray
Write-Host "failed_step_count: $($failed.Count)" -ForegroundColor Gray

if ($ok) {
    Write-Host "[OK] RPG frontend recover flow completed" -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] RPG frontend recover flow failed" -ForegroundColor Red
$failed | ForEach-Object {
    Write-Host ("[FAILED] {0} exit={1}" -f $_.name, $_.exit_code) -ForegroundColor Red
}
exit 1
