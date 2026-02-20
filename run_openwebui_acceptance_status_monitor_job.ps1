param(
    [switch]$SkipWebhook
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$notifyScript = Join-Path $scriptDir "notify_openwebui_acceptance_pass.ps1"
$lightCheckScript = Join-Path $scriptDir "check_openwebui_acceptance_status_light.ps1"

if (-not (Test-Path $notifyScript)) { throw "Missing script: $notifyScript" }
if (-not (Test-Path $lightCheckScript)) { throw "Missing script: $lightCheckScript" }

Write-Host "=== OpenWebUI Acceptance Status Monitor Job ===" -ForegroundColor Cyan
try {
    Write-Host "[1/2] Refresh latest status line" -ForegroundColor Cyan
    if ($SkipWebhook) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile
    }
    else {
        powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile -SendWebhook
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to refresh latest status (exit=$LASTEXITCODE)"
    }

    Write-Host "[2/2] Strict light status check" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $lightCheckScript -RequireStatusLine
    if ($LASTEXITCODE -ne 0) {
        throw "Light status check failed (exit=$LASTEXITCODE)"
    }

    Write-Host "[OK] OpenWebUI acceptance status monitor passed" -ForegroundColor Green
    exit 0
}
catch {
    $reason = $_.Exception.Message
    Write-Host "[NG] OpenWebUI acceptance status monitor failed: $reason" -ForegroundColor Red

    if (-not $SkipWebhook -and (Test-Path $notifyScript)) {
        try {
            $reasonForNotify = ([string]$reason -replace "[\r\n]+", " | ").Trim()
            if ($reasonForNotify.Length -gt 500) {
                $reasonForNotify = $reasonForNotify.Substring(0, 500)
            }
            powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile -SendWebhook -ForceVerdict FAIL -Reason "light_monitor_failed $reasonForNotify"
        }
        catch {
            Write-Host "[WARN] failure notification invocation failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    exit 1
}
