param(
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$probeScript = Join-Path $scriptDir "monitor_image_pipeline.ps1"

if (-not (Test-Path $probeScript)) {
    throw "Probe script not found: $probeScript"
}

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\image_pipeline_probe_task.config.json"
}

$unifiedApiUrl = "http://127.0.0.1:9502"
$comfyUiUrl = "http://127.0.0.1:8188"
$logFile = Join-Path $scriptDir "logs\image_pipeline_probe.latest.json"

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.unified_api_url) { $unifiedApiUrl = [string]$cfg.unified_api_url }
        if ($cfg.comfyui_url) { $comfyUiUrl = [string]$cfg.comfyui_url }
        if ($cfg.log_file) { $logFile = [string]$cfg.log_file }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

$logDir = Split-Path -Parent $logFile
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

& $probeScript -ProbeGenerate -Json -UnifiedApiUrl $unifiedApiUrl -ComfyUiUrl $comfyUiUrl | Set-Content -Path $logFile -Encoding UTF8

Write-Host "[OK] Image pipeline probe saved: $logFile" -ForegroundColor Green
