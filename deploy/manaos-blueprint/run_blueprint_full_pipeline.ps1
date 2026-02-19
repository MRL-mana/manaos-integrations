param(
    [string]$BaseDomain,
    [string]$AdminEmail = "mana-blueprint-admin@example.local",
    [string]$AdminPassword = "ManaOS!2026",
    [switch]$StartIfNeeded,
    [switch]$BootstrapSignup
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrapScript = Join-Path $scriptDir "bootstrap_openwebui_tools.py"
$acceptanceScript = Join-Path $scriptDir "run_blueprint_acceptance.ps1"
$envPath = Join-Path $scriptDir ".env"

if (-not (Test-Path $bootstrapScript)) {
    throw "bootstrap script not found: $bootstrapScript"
}
if (-not (Test-Path $acceptanceScript)) {
    throw "acceptance script not found: $acceptanceScript"
}

if (-not $BaseDomain -and (Test-Path $envPath)) {
    $line = Get-Content $envPath | Where-Object { $_ -match '^BASE_DOMAIN=' } | Select-Object -First 1
    if ($line) {
        $BaseDomain = ($line -split '=', 2)[1].Trim()
    }
}

if (-not $BaseDomain) {
    $BaseDomain = "mrl-mana.com"
}

$logDir = Join-Path $scriptDir "..\..\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "blueprint_pipeline_$stamp.log"

Step "Blueprint full pipeline"
Write-Host "BaseDomain: $BaseDomain" -ForegroundColor Gray
Write-Host "Log: $logPath" -ForegroundColor Gray

$bootstrapArgs = @(
    $bootstrapScript,
    "--base-domain", $BaseDomain,
    "--email", $AdminEmail,
    "--password", $AdminPassword
)

if ($BootstrapSignup) {
    $bootstrapArgs += "--signup"
}

Step "Bootstrap Open WebUI tool"
python @bootstrapArgs 2>&1 | Tee-Object -FilePath $logPath -Append | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "bootstrap failed (exit=$LASTEXITCODE)"
}

Step "Run blueprint acceptance"
$acceptanceArgs = @{
    BaseDomain = $BaseDomain
    AdminEmail = $AdminEmail
    AdminPassword = $AdminPassword
}

if ($StartIfNeeded) {
    $acceptanceArgs["StartIfNeeded"] = $true
}

& $acceptanceScript @acceptanceArgs 2>&1 | Tee-Object -FilePath $logPath -Append | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "acceptance failed (exit=$LASTEXITCODE)"
}

Step "Pipeline result"
Write-Host "[OK] Blueprint full pipeline PASSED" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
