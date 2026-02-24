param(
    [int]$Port = 9502
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $current = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-ListenerPids([int]$port) {
    try {
        return (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop |
            Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        return @()
    }
}

$pids = @(Get-ListenerPids -port $Port)
if ($pids.Count -eq 0) {
    Write-Host ("[OK] Port {0} is not listening." -f $Port) -ForegroundColor Green
    exit 0
}

$pidList = ($pids -join ', ')
Write-Host ("[INFO] Port {0} LISTEN PID(s): {1}" -f $Port, $pidList) -ForegroundColor Cyan

if (-not (Test-IsAdmin)) {
    Write-Host "[ACTION] Admin required. Relaunching elevated (kill only)." -ForegroundColor Yellow
    $argList = @(
        '-NoProfile'
        '-ExecutionPolicy', 'Bypass'
        '-File', $PSCommandPath
        '-Port', $Port
    )
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argList
    exit 0
}

foreach ($procId in $pids) {
    try {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { 'unknown' }
        Write-Host ("[KILL] Stopping PID {0} ({1})" -f $procId, $name) -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction Stop
    } catch {
        Write-Host ("[FAIL] Failed to stop PID {0}: {1}" -f $procId, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

Start-Sleep -Seconds 1
$remaining = Get-ListenerPids -port $Port
if ($remaining -and $remaining.Count -gt 0) {
    $remainingList = ($remaining -join ', ')
    Write-Host ("[WARN] Still listening: {0}" -f $remainingList) -ForegroundColor Yellow
    exit 2
}

Write-Host ("[OK] Port {0} released. Start Unified API (non-admin) next." -f $Port) -ForegroundColor Green
exit 0