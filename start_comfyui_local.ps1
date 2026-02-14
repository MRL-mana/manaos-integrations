# ComfyUI local launcher (Windows host)

param(
    [int]$Port = 8188,
    [string]$ComfyUIPath = "",
    [switch]$CPU,
    [switch]$LowVRAM,
    [switch]$Background,
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ComfyUIPath([string]$pathHint) {
    if (-not [string]::IsNullOrWhiteSpace($pathHint)) {
        if (-not (Test-Path -LiteralPath $pathHint)) {
            throw "ComfyUIPath not found: $pathHint"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $pathHint 'main.py'))) {
            throw "main.py not found under: $pathHint"
        }
        return $pathHint
    }

    $candidates = @(
        'C:\ComfyUI',
        (Join-Path $env:USERPROFILE 'ComfyUI'),
        (Join-Path $env:USERPROFILE 'Desktop\ComfyUI'),
        'D:\ComfyUI',
        'E:\ComfyUI',
        (Join-Path $env:USERPROFILE 'Documents\ComfyUI')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'main.py')) {
            return $candidate
        }
    }

    throw "ComfyUI not found. Specify -ComfyUIPath (folder containing main.py)."
}

function Get-ListeningProcessId([int]$listenPort) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($null -ne $conn) { return [int]$conn.OwningProcess }
    } catch {
        return $null
    }

    return $null
}

$ComfyUIPath = Resolve-ComfyUIPath $ComfyUIPath

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "ComfyUI local launcher" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ("Path: {0}" -f $ComfyUIPath) -ForegroundColor Gray
Write-Host ("Port: {0}" -f $Port) -ForegroundColor Gray

$venvPython = Join-Path $ComfyUIPath '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
    Write-Host ("Python: {0} (venv)" -f $pythonExe) -ForegroundColor Gray
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "python not found in PATH (and no ComfyUI .venv found). Create a venv under ComfyUI or add python to PATH."
    }
    $pythonExe = $pythonCmd.Source
    Write-Host ("Python: {0}" -f $pythonExe) -ForegroundColor Gray
}

$forceCpu = [bool]$CPU
if (-not $forceCpu) {
    try {
        $cudaAvailable = & $pythonExe -c "import torch; print('1' if torch.cuda.is_available() else '0')" 2>$null
        if ($cudaAvailable -and ($cudaAvailable | Select-Object -First 1).Trim() -ne '1') {
            $forceCpu = $true
            Write-Host "CUDA not available; forcing --cpu" -ForegroundColor Yellow
        }
    } catch {
        # If detection fails, keep the user's choice (GPU default).
    }
}

$pidInUse = Get-ListeningProcessId -listenPort $Port
if ($pidInUse) {
    if ($Background) {
        Write-Host ("Already listening: http://127.0.0.1:{0} (pid {1})" -f $Port, $pidInUse) -ForegroundColor Green
        exit 0
    }

    Write-Host ("Port {0} is already in use (pid {1})." -f $Port, $pidInUse) -ForegroundColor Yellow
    Write-Host "Stop the owning process? (Y/N): " -NoNewline -ForegroundColor Yellow
    $resp = Read-Host
    if ($resp -eq 'Y' -or $resp -eq 'y') {
        Stop-Process -Id $pidInUse -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Canceled." -ForegroundColor Yellow
        exit 0
    }
}

$arguments = @('main.py', '--port', $Port.ToString())
if ($forceCpu) { $arguments += '--cpu' }
if ($LowVRAM) { $arguments += '--lowvram' }

# Reduce some Windows console-related issues
$env:TQDM_DISABLE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONLEGACYWINDOWSSTDIO = '1'
$env:PYTHONUTF8 = '1'

if ([string]::IsNullOrWhiteSpace($LogDir)) {
    $LogDir = Join-Path $PSScriptRoot 'logs'
}

if ($Background) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $LogDir ("comfyui_{0}_stdout.log" -f $ts)
    $stderr = Join-Path $LogDir ("comfyui_{0}_stderr.log" -f $ts)

    Write-Host ""
    Write-Host "Starting ComfyUI in background..." -ForegroundColor Green
    Write-Host ("STDOUT: {0}" -f $stdout) -ForegroundColor Gray
    Write-Host ("STDERR: {0}" -f $stderr) -ForegroundColor Gray

    $p = Start-Process -FilePath $pythonExe -ArgumentList $arguments -WorkingDirectory $ComfyUIPath -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Write-Host ("STARTED_PID={0} URL=http://127.0.0.1:{1}" -f $p.Id, $Port) -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host ("Open: http://127.0.0.1:{0}" -f $Port) -ForegroundColor Cyan
Write-Host "Stop: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

Push-Location $ComfyUIPath
try {
    & $pythonExe @arguments
} finally {
    Pop-Location
}

