param(
    [int]$GalleryPort = 5559,
    [int]$MoltbotPort = 8088,
    [int]$StartupTimeoutSec = 90
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptDir "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$diagLatestPath = Join-Path $logsDir "optional_services_diag_latest.json"
$diagHistoryPath = Join-Path $logsDir "optional_services_diag_history.jsonl"

function Write-Diagnostic {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Succeeded,
        [string]$ErrorMessage = ""
    )

    $diag = [ordered]@{
        timestamp = (Get-Date).ToString("o")
        succeeded = $Succeeded
        gallery_port = $GalleryPort
        moltbot_port = $MoltbotPort
        startup_timeout_sec = $StartupTimeoutSec
        gallery_health_url = "http://127.0.0.1:$GalleryPort/health"
        moltbot_health_url = "http://127.0.0.1:$MoltbotPort/moltbot/health"
        gallery_stdout_log = (Join-Path $logsDir "gallery_api_stdout.log")
        gallery_stderr_log = (Join-Path $logsDir "gallery_api_stderr.log")
        moltbot_stdout_log = (Join-Path $logsDir "moltbot_gateway_stdout.log")
        moltbot_stderr_log = (Join-Path $logsDir "moltbot_gateway_stderr.log")
        error = $ErrorMessage
    }

    $diag | ConvertTo-Json -Depth 6 | Set-Content -Path $diagLatestPath -Encoding UTF8
    ($diag | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Path $diagHistoryPath -Encoding UTF8
}

function Get-LogTailText {
    param(
        [string]$Path,
        [int]$TailLines = 20
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or (-not (Test-Path $Path))) {
        return ""
    }

    try {
        $tail = Get-Content -Path $Path -Tail $TailLines -ErrorAction Stop
        $text = ($tail -join " `u{00B7} ").Trim()
        if ($text.Length -gt 280) {
            $text = $text.Substring(0, 280)
        }
        return $text
    }
    catch {
        return ""
    }
}

function Test-EndpointOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSec = 12
    )

    try {
        $null = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Wait-Endpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$WaitSec = 60
    )

    $deadline = (Get-Date).AddSeconds($WaitSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-EndpointOk -Url $Url -TimeoutSec 12) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Test-ProcessCommandContains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Needle
    )

    $needleLower = $Needle.ToLowerInvariant()
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    foreach ($proc in $procs) {
        $cmd = [string]$proc.CommandLine
        if (-not [string]::IsNullOrWhiteSpace($cmd) -and $cmd.ToLowerInvariant().Contains($needleLower)) {
            return $true
        }
    }
    return $false
}

function Ensure-GalleryApi {
    param(
        [int]$Port,
        [int]$TimeoutSec
    )

    $healthUrl = "http://127.0.0.1:$Port/health"
    if (Test-EndpointOk -Url $healthUrl) {
        Write-Host "[OK] Gallery API already healthy on :$Port" -ForegroundColor Green
        return
    }

    $stdout = Join-Path $logsDir "gallery_api_stdout.log"
    $stderr = Join-Path $logsDir "gallery_api_stderr.log"

    if (-not (Test-ProcessCommandContains -Needle "gallery_api_server.py")) {
        Write-Host "[INFO] Starting Gallery API..." -ForegroundColor Cyan
        $galleryScript = Join-Path $scriptDir "scripts\misc\gallery_api_server.py"
        if (-not (Test-Path $galleryScript)) {
            throw "Gallery API script not found: $galleryScript"
        }

        $cmdLine = "set PYTHONPATH=$scriptDir&& python `"$galleryScript`""
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmdLine) -WorkingDirectory $scriptDir -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    }
    else {
        Write-Host "[INFO] Gallery API process exists; waiting for health..." -ForegroundColor Gray
    }

    if (-not (Wait-Endpoint -Url $healthUrl -WaitSec $TimeoutSec)) {
        $diag = Get-LogTailText -Path $stderr
        if ([string]::IsNullOrWhiteSpace($diag)) {
            throw "Gallery API failed to become healthy on :$Port"
        }
        throw "Gallery API failed on :$Port; stderr_tail=$diag"
    }

    Write-Host "[OK] Gallery API recovered on :$Port" -ForegroundColor Green
}

function Ensure-MoltbotGateway {
    param(
        [int]$Port,
        [int]$TimeoutSec
    )

    $healthUrl = "http://127.0.0.1:$Port/moltbot/health"
    if (Test-EndpointOk -Url $healthUrl) {
        Write-Host "[OK] Moltbot Gateway already healthy on :$Port" -ForegroundColor Green
        return
    }

    $stdout = Join-Path $logsDir "moltbot_gateway_stdout.log"
    $stderr = Join-Path $logsDir "moltbot_gateway_stderr.log"

    if (-not (Test-ProcessCommandContains -Needle "moltbot_gateway.gateway_app:app")) {
        $startScript = Join-Path $scriptDir "moltbot_gateway\deploy\run_gateway_wrapper_production.ps1"
        if (-not (Test-Path $startScript)) {
            throw "Moltbot start script not found: $startScript"
        }

        Write-Host "[INFO] Starting Moltbot Gateway..." -ForegroundColor Cyan
        Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $startScript) -WorkingDirectory $scriptDir -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    }
    else {
        Write-Host "[INFO] Moltbot Gateway process exists; waiting for health..." -ForegroundColor Gray
    }

    if (-not (Wait-Endpoint -Url $healthUrl -WaitSec $TimeoutSec)) {
        $diag = Get-LogTailText -Path $stderr
        if ([string]::IsNullOrWhiteSpace($diag)) {
            throw "Moltbot Gateway failed to become healthy on :$Port"
        }
        throw "Moltbot Gateway failed on :$Port; stderr_tail=$diag"
    }

    Write-Host "[OK] Moltbot Gateway recovered on :$Port" -ForegroundColor Green
}

Write-Host "=== Ensure Optional Services ===" -ForegroundColor Cyan
try {
    Ensure-GalleryApi -Port $GalleryPort -TimeoutSec $StartupTimeoutSec
    Ensure-MoltbotGateway -Port $MoltbotPort -TimeoutSec $StartupTimeoutSec
    Write-Diagnostic -Succeeded $true
    Write-Host "[OK] Optional services ready" -ForegroundColor Green
    exit 0
}
catch {
    $errorMessage = [string]$_.Exception.Message
    Write-Diagnostic -Succeeded $false -ErrorMessage $errorMessage
    Write-Host "[NG] Optional services ensure failed: $errorMessage" -ForegroundColor Red
    Write-Host "[INFO] Diagnostic: $diagLatestPath" -ForegroundColor Yellow
    exit 1
}
