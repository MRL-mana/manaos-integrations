param(
    [switch]$SkipNotify
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pipelineScript = Join-Path $scriptDir "run_openwebui_acceptance_pipeline_full_auto.ps1"
$strictCheckScript = Join-Path $scriptDir "check_latest_openwebui_acceptance.ps1"
$notifyScript = Join-Path $scriptDir "notify_openwebui_acceptance_pass.ps1"
$optionalEnsureScript = Join-Path $scriptDir "ensure_optional_services.ps1"
$optionalDiagPath = Join-Path $scriptDir "logs\optional_services_diag_latest.json"

if (-not (Test-Path $pipelineScript)) { throw "Missing script: $pipelineScript" }
if (-not (Test-Path $strictCheckScript)) { throw "Missing script: $strictCheckScript" }
if ((-not $SkipNotify) -and (-not (Test-Path $notifyScript))) { throw "Missing script: $notifyScript" }
if (-not (Test-Path $optionalEnsureScript)) { throw "Missing script: $optionalEnsureScript" }

Write-Host "=== OpenWebUI Acceptance Daily Job ===" -ForegroundColor Cyan
try {
    Write-Host "[0/3] Ensure optional services" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $optionalEnsureScript
    if ($LASTEXITCODE -ne 0) {
        $diagDetails = ""
        if (Test-Path $optionalDiagPath) {
            try {
                $diagObj = Get-Content -Path $optionalDiagPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $diagError = [string]$diagObj.error
                if (-not [string]::IsNullOrWhiteSpace($diagError)) {
                    $diagError = ($diagError -replace "[\r\n]+", " ").Trim()
                    if ($diagError.Length -gt 220) {
                        $diagError = $diagError.Substring(0, 220)
                    }
                    $diagDetails = " diag_error=$diagError"
                }
                $diagDetails += " diag_file=$optionalDiagPath"
            }
            catch {
                $diagDetails = " diag_file=$optionalDiagPath"
            }
        }

        throw "Optional services ensure failed (exit=$LASTEXITCODE)$diagDetails"
    }

    Write-Host "[1/3] Run full-auto acceptance pipeline" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $pipelineScript
    if ($LASTEXITCODE -ne 0) {
        throw "Full-auto acceptance pipeline failed (exit=$LASTEXITCODE)"
    }

    Write-Host "[2/3] Verify strict PASS verdict" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $strictCheckScript -RequirePass
    if ($LASTEXITCODE -ne 0) {
        throw "Strict PASS verification failed (exit=$LASTEXITCODE)"
    }

    if (-not $SkipNotify) {
        Write-Host "[3/3] Notify latest verdict" -ForegroundColor Cyan
        powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile -SendWebhook
        if ($LASTEXITCODE -ne 0) {
            throw "Verdict notification failed (exit=$LASTEXITCODE)"
        }
    }
    else {
        Write-Host "[3/3] Notify latest verdict skipped" -ForegroundColor Yellow
    }

    Write-Host "[OK] OpenWebUI acceptance daily job completed" -ForegroundColor Green
    exit 0
}
catch {
    $reason = $_.Exception.Message
    Write-Host "[NG] OpenWebUI acceptance daily job failed: $reason" -ForegroundColor Red

    $reasonForNotify = [string]$reason
    $reasonForNotify = $reasonForNotify -replace "[\r\n]+", " | "
    $reasonForNotify = $reasonForNotify -replace '"', "'"
    if ($reasonForNotify.Length -gt 500) {
        $reasonForNotify = $reasonForNotify.Substring(0, 500)
    }

    if (-not $SkipNotify -and (Test-Path $notifyScript)) {
        try {
            powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile -SendWebhook -ForceVerdict FAIL -Reason $reasonForNotify
        }
        catch {
            Write-Host "[WARN] failure notification invocation failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    exit 1
}
