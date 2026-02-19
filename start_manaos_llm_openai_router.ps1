param(
    [int]$Port = 5211,
    [ValidateSet("ollama", "lm_studio")]
    [string]$LlmServer = "ollama",
    [switch]$AutoSelectPort
)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray

$ErrorActionPreference = "Stop"

$script:RouterAlreadyRunning = $false

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3.10")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python interpreter not found. Install Python 3.10 or ensure py/python is on PATH."
}

function Test-RouterHealth {
    param([int]$TargetPort)

    try {
        $response = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/v1/models" -f $TargetPort) -Method Get -TimeoutSec 2 -ErrorAction Stop
        return $null -ne $response
    }
    catch {
        return $false
    }
}

function Get-ListeningProcess {
    param([int]$TargetPort)

    $conn = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $conn) {
        return $null
    }

    return Get-CimInstance Win32_Process -Filter ("ProcessId=" + $conn.OwningProcess) -ErrorAction SilentlyContinue
}

function Resolve-AvailablePort {
    param(
        [int]$RequestedPort,
        [switch]$AllowAutoSelect
    )

    $listener = Get-ListeningProcess -TargetPort $RequestedPort
    if (-not $listener) {
        return $RequestedPort
    }

    $commandLine = if ($listener.CommandLine) { $listener.CommandLine } else { "" }
    if ($commandLine -match "manaos_llm_routing_api\.py") {
        if (Test-RouterHealth -TargetPort $RequestedPort) {
            Write-Host ("[INFO] Router is already running on port {0}. Reusing existing process." -f $RequestedPort) -ForegroundColor Cyan
            $script:RouterAlreadyRunning = $true
            return $RequestedPort
        }
    }

    if ($RequestedPort -ne 5211 -and (Test-RouterHealth -TargetPort 5211)) {
        Write-Host ("[WARN] Port {0} is in use. Existing router on 5211 will be reused." -f $RequestedPort) -ForegroundColor Yellow
        $script:RouterAlreadyRunning = $true
        return 5211
    }

    if (-not $AllowAutoSelect) {
        $name = if ($listener.Name) { $listener.Name } else { "unknown" }
        $ownerProcessId = if ($listener.ProcessId) { $listener.ProcessId } else { "unknown" }
        throw "Port $RequestedPort is already in use by $name (PID: $ownerProcessId). Re-run with -Port <free port> or -AutoSelectPort."
    }

    foreach ($candidate in 5211..5299) {
        if (-not (Get-ListeningProcess -TargetPort $candidate)) {
            Write-Host ("[WARN] Port {0} is in use. Auto-selected port: {1}" -f $RequestedPort, $candidate) -ForegroundColor Yellow
            return $candidate
        }
    }

    throw "No free port found in range 5211-5299."
}

$Port = Resolve-AvailablePort -RequestedPort $Port -AllowAutoSelect:$AutoSelectPort

$logsDir = Join-Path $root "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -Path $logsDir -ItemType Directory -Force | Out-Null
}

$portStatusPath = Join-Path $logsDir "manaos_llm_router_port.txt"
$portStatus = @(
    ("port={0}" -f $Port),
    ("llm_server={0}" -f $LlmServer),
    ("updated_at={0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
)
Set-Content -Path $portStatusPath -Value $portStatus -Encoding UTF8

$env:PORT = [string]$Port
$env:LLM_SERVER = $LlmServer
$env:PYTHONUTF8 = "1"

Write-Host '========================================'
Write-Host 'ManaOS OpenAI-Compatible LLM Auto Router'
Write-Host '========================================'
Write-Host ('PORT: {0}' -f $env:PORT)
Write-Host ('LLM_SERVER: {0}' -f $env:LLM_SERVER)
Write-Host ('Endpoint: http://127.0.0.1:{0}/v1/chat/completions' -f $env:PORT)
Write-Host ('Models:   http://127.0.0.1:{0}/v1/models' -f $env:PORT)
Write-Host ('Status:   {0}' -f $portStatusPath)
Write-Host ''

$apiPath = Join-Path $root 'manaos_llm_routing_api.py'
$pythonCmd = Resolve-PythonCommand
Write-Host ('Python:   {0}' -f ($pythonCmd -join ' '))

if ($script:RouterAlreadyRunning) {
    Write-Host '[OK] Router is already available. Nothing to start.' -ForegroundColor Green
    exit 0
}

if ($pythonCmd.Count -eq 2) {
    & $pythonCmd[0] $pythonCmd[1] $apiPath
}
else {
    & $pythonCmd[0] $apiPath
}

if ($LASTEXITCODE -ne 0) {
    throw "Router API process exited with code $LASTEXITCODE"
}
