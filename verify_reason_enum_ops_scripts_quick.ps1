param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Invoke-QuickStep {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$Args
    )

    if (-not (Test-Path $ScriptPath)) {
        return [pscustomobject]@{ name = $Name; ok = $false; exit_code = -1; output_tail = @("missing: $ScriptPath") }
    }

    $cmdArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$ScriptPath) + $Args
    $output = @(& pwsh @cmdArgs 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = [int]$LASTEXITCODE
    [pscustomobject]@{
        name = $Name
        ok = ($exitCode -eq 0)
        exit_code = $exitCode
        output_tail = @($output | Select-Object -Last 10)
    }
}

$steps = @(
    (Invoke-QuickStep -Name 'doctor_tasks' -ScriptPath (Join-Path $scriptDir 'doctor_reason_enum_ops_tasks.ps1') -Args @()),
    (Invoke-QuickStep -Name 'export_snapshot_json' -ScriptPath (Join-Path $scriptDir 'export_reason_enum_ops_snapshot.ps1') -Args @('-AsJson')),
    (Invoke-QuickStep -Name 'status_snapshot_task_json' -ScriptPath (Join-Path $scriptDir 'status_reason_enum_ops_snapshot_task.ps1') -Args @('-AsJson')),
    (Invoke-QuickStep -Name 'status_lifecycle_json' -ScriptPath (Join-Path $scriptDir 'status_reason_enum_ops_snapshot_task_lifecycle.ps1') -Args @('-AsJson')),
    (Invoke-QuickStep -Name 'install_snapshot_task_printonly' -ScriptPath (Join-Path $scriptDir 'install_reason_enum_ops_snapshot_task.ps1') -Args @('-PrintOnly'))
)

$failed = @($steps | Where-Object { -not $_.ok })
$ok = ($failed.Count -eq 0)

Write-Host "=== Reason Enum Ops Quick Verify ===" -ForegroundColor Cyan
Write-Host "ok: $ok" -ForegroundColor Gray
Write-Host "failed_step_count: $($failed.Count)" -ForegroundColor Gray

$steps | ForEach-Object {
    $status = if ($_.ok) { 'OK' } else { 'FAIL' }
    $color = if ($_.ok) { 'Green' } else { 'Red' }
    Write-Host ("[{0}] {1} exit={2}" -f $status, $_.name, $_.exit_code) -ForegroundColor $color
}

if (-not $ok) {
    Write-Host "--- failed output tail ---" -ForegroundColor Yellow
    $failed | ForEach-Object {
        Write-Host (">>> " + $_.name) -ForegroundColor Yellow
        $_.output_tail | ForEach-Object { Write-Host $_ }
    }
    exit 1
}

exit 0
