param(
    [int]$EvalPort = 9601,
    [int]$ComfyPort = 8188,
    [switch]$SkipFirewall
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$evalScript = Join-Path $scriptDir "scripts\lifecycle\start_evaluation_ui_port9601.py"

if (-not (Test-Path $evalScript)) {
    throw "Evaluation UI script not found: $evalScript"
}
function Resolve-ComfyUIPath {
    $candidates = @(
        'C:\ComfyUI',
        (Join-Path $env:USERPROFILE 'ComfyUI'),
        (Join-Path $env:USERPROFILE 'Desktop\ComfyUI'),
        'D:\ComfyUI',
        'E:\ComfyUI'
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'main.py')) {
            return $candidate
        }
    }
    return ""
}

function Resolve-PythonExe {
    param([string]$ComfyPath)

    $venvPython = Join-Path $ComfyPath '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }
    return ""
}

function Get-TailscaleIPv4 {
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*Tailscale*' -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty IPAddress -First 1
        if (-not [string]::IsNullOrWhiteSpace($ip)) {
            return [string]$ip
        }
    }
    catch {
    }
    return ""
}

function Test-IsAdmin {
    $wid = [Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object Security.Principal.WindowsPrincipal($wid)
    return $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-TailscaleFirewallRule {
    param(
        [string]$Name,
        [int]$Port
    )

    if (Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue) {
        return
    }

    New-NetFirewallRule -DisplayName $Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress "100.64.0.0/10" | Out-Null
}

function Get-ListeningProcessId([int]$Port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($null -ne $conn) { return [int]$conn.OwningProcess }
    }
    catch {
    }
    return $null
}

function Wait-HttpReady {
    param([string]$Url, [int]$TimeoutSec = 35)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $code = & curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 2 --max-time 4 $Url
            if ($LASTEXITCODE -eq 0 -and $code -match '^(200|204|301|302|304|404)$') {
                return $true
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 800
    }
    return $false
}

Write-Host "=== ManaOS Image Services Tailscale Start ===" -ForegroundColor Cyan

if (-not $SkipFirewall.IsPresent) {
    if (Test-IsAdmin) {
        Ensure-TailscaleFirewallRule -Name "ManaOS-EvaluationUI-Tailscale-$EvalPort" -Port $EvalPort
        Ensure-TailscaleFirewallRule -Name "ManaOS-ComfyUI-Tailscale-$ComfyPort" -Port $ComfyPort
        Write-Host "[OK] Firewall rules ensured (Tailscale only)" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] Not admin: firewall step skipped." -ForegroundColor Yellow
    }
}

$evalPid = Get-ListeningProcessId -Port $EvalPort
if (-not $evalPid) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "python not found in PATH"
    }
    $procEval = Start-Process -FilePath $pythonCmd.Source -ArgumentList @('-u', $evalScript) -WorkingDirectory $scriptDir -PassThru -WindowStyle Hidden
    Write-Host "[INFO] Evaluation UI start requested (pid=$($procEval.Id))" -ForegroundColor Gray
} else {
    Write-Host "[INFO] Evaluation UI already listening (pid=$evalPid)" -ForegroundColor Gray
}

$comfyPid = Get-ListeningProcessId -Port $ComfyPort
if (-not $comfyPid) {
    $comfyPath = Resolve-ComfyUIPath
    if ([string]::IsNullOrWhiteSpace($comfyPath)) {
        throw "ComfyUI not found (main.py)."
    }

    $pythonExe = Resolve-PythonExe -ComfyPath $comfyPath
    if ([string]::IsNullOrWhiteSpace($pythonExe)) {
        throw "python not found for ComfyUI"
    }

    $procComfy = Start-Process -FilePath $pythonExe -ArgumentList @('main.py', '--listen', '0.0.0.0', '--port', "$ComfyPort") -WorkingDirectory $comfyPath -PassThru -WindowStyle Hidden
    Write-Host "[INFO] ComfyUI start requested (pid=$($procComfy.Id))" -ForegroundColor Gray
} else {
    Write-Host "[INFO] ComfyUI already listening (pid=$comfyPid)" -ForegroundColor Gray
}

$evalOk = Wait-HttpReady -Url "http://127.0.0.1:$EvalPort" -TimeoutSec 40
$comfyOk = Wait-HttpReady -Url "http://127.0.0.1:$ComfyPort" -TimeoutSec 40

if (-not $evalOk -or -not $comfyOk) {
    Write-Host "[ALERT] Service startup check failed (eval=$evalOk comfy=$comfyOk)" -ForegroundColor Red
    exit 1
}

$tailscaleIp = Get-TailscaleIPv4
if (-not [string]::IsNullOrWhiteSpace($tailscaleIp)) {
    Write-Host "[OK] Eval UI:  http://${tailscaleIp}:$EvalPort" -ForegroundColor Green
    Write-Host "[OK] ComfyUI:  http://${tailscaleIp}:$ComfyPort" -ForegroundColor Green
} else {
    Write-Host "[WARN] Tailscale IP not found." -ForegroundColor Yellow
}

Write-Host "[OK] Eval local:  http://127.0.0.1:$EvalPort" -ForegroundColor Green
Write-Host "[OK] Comfy local: http://127.0.0.1:$ComfyPort" -ForegroundColor Green
