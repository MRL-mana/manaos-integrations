param(
    [string]$ConfigFile = "",
    [string]$ScriptPath = "",
    [switch]$Enable,
    [switch]$Dashboard
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\rl_anything_bootstrap_task.config.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.script_path) { $ScriptPath = [string]$cfg.script_path }
        if ($null -ne $cfg.enable -and [bool]$cfg.enable) { $Enable = $true }
        if ($null -ne $cfg.dashboard -and [bool]$cfg.dashboard) { $Dashboard = $true }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Join-Path $scriptDir "scripts\start_rl_anything.ps1"
}

if (-not (Test-Path $ScriptPath)) {
    throw "Script not found: $ScriptPath"
}

$runArgs = @(
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    $ScriptPath
)
if ($Enable.IsPresent) { $runArgs += '-Enable' }
if ($Dashboard.IsPresent) { $runArgs += '-Dashboard' }

& pwsh @runArgs
exit $LASTEXITCODE
