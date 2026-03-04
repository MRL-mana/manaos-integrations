param(
    [switch]$SkipFirewall
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$rpgScript = Join-Path $scriptDir "start_manaos_rpg_tailscale.ps1"
$imageScript = Join-Path $scriptDir "start_image_services_tailscale.ps1"
$checkScript = Join-Path $scriptDir "check_tailscale_publish_status.ps1"

foreach ($required in @($rpgScript, $imageScript, $checkScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$Path,
        [string[]]$Args = @()
    )

    Write-Host "--- $Name ---" -ForegroundColor Cyan
    $cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Path) + $Args
    & pwsh @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed (exit=$LASTEXITCODE)"
    }
}

Write-Host "=== ManaOS Tailscale Full Stack Start ===" -ForegroundColor Cyan

$commonArgs = @()
if ($SkipFirewall.IsPresent) {
    $commonArgs += '-SkipFirewall'
}

Invoke-Step -Name 'RPG Start' -Path $rpgScript -Args $commonArgs
Invoke-Step -Name 'Image Services Start' -Path $imageScript -Args $commonArgs
Invoke-Step -Name 'Publish Status Check' -Path $checkScript

Write-Host "[OK] Full stack is ready via Tailscale" -ForegroundColor Green
exit 0
