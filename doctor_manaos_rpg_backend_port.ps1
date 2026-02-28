param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 9510,
    [switch]$AsJson,
    [switch]$RequirePass
)

$ErrorActionPreference = "Stop"

function Get-HealthCode {
    param([string]$HostName, [int]$PortNumber)

    try {
        $code = & curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 2 --max-time 4 "http://${HostName}:${PortNumber}/health"
        if ($LASTEXITCODE -ne 0) {
            return "000"
        }
        return [string]$code
    }
    catch {
        return "000"
    }
}

function Get-ListenerDetails {
    param([int]$PortNumber)

    $rows = @(Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction SilentlyContinue)
    if ($rows.Count -eq 0) {
        return @()
    }

    $pids = @($rows | Select-Object -ExpandProperty OwningProcess -Unique)
    $out = @()
    foreach ($p in $pids) {
        $pidInt = [int]$p
        $exists = $false
        $name = ""
        $path = ""
        $cmd = ""
        try {
            $proc = Get-Process -Id $pidInt -ErrorAction Stop
            $exists = $true
            $name = [string]$proc.ProcessName
            $path = [string]$proc.Path
        }
        catch {
        }

        try {
            $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$pidInt" -ErrorAction Stop
            $cmd = [string]$wmi.CommandLine
            if (-not $exists) {
                $exists = $true
                if ([string]::IsNullOrWhiteSpace($name)) { $name = [string]$wmi.Name }
                if ([string]::IsNullOrWhiteSpace($path)) { $path = [string]$wmi.ExecutablePath }
            }
        }
        catch {
        }

        $cmdLower = $cmd.ToLowerInvariant()
        $looksLikeUvicorn = $cmdLower.Contains("uvicorn")
        $looksLikeAppEntry = $cmdLower.Contains("app:app")
        $looksLikeBackend = $looksLikeUvicorn -and $looksLikeAppEntry

        $out += [pscustomobject]@{
            pid = $pidInt
            process_exists = $exists
            process_name = $name
            process_path = $path
            command_line = $cmd
            looks_like_backend = $looksLikeBackend
        }
    }
    return $out
}

$listeners = @(Get-ListenerDetails -PortNumber $Port)
$healthCode = Get-HealthCode -HostName $BindAddress -PortNumber $Port

$listenerCount = $listeners.Count
$existingCount = @($listeners | Where-Object { $_.process_exists }).Count
$backendLikeCount = @($listeners | Where-Object { $_.looks_like_backend }).Count

$okReason = "ok"
if ($listenerCount -eq 0) {
    $okReason = "not_listening"
}
elseif ($existingCount -lt $listenerCount) {
    $okReason = "listener_pid_stale"
}
elseif ($listenerCount -gt 1) {
    $okReason = "multiple_listeners"
}
elseif ($healthCode -ne "200") {
    $okReason = "health_not_ok"
}
elseif ($backendLikeCount -eq 0) {
    $okReason = "healthy_listener_unclassified"
}

$pass = @("ok", "healthy_listener_unclassified") -contains $okReason

$payload = [ordered]@{
    host = $BindAddress
    port = $Port
    health_code = $healthCode
    listener_count = $listenerCount
    process_exists_count = $existingCount
    backend_like_count = $backendLikeCount
    ok_reason = $okReason
    pass = $pass
    listeners = $listeners
}

if ($AsJson) {
    $payload.require_pass = [bool]$RequirePass
    Write-Output ($payload | ConvertTo-Json -Depth 8)
    if ($RequirePass.IsPresent -and -not $pass) {
        exit 1
    }
    exit 0
}

Write-Host "=== ManaOS RPG Backend Port Doctor ===" -ForegroundColor Cyan
Write-Host "host: $BindAddress" -ForegroundColor Gray
Write-Host "port: $Port" -ForegroundColor Gray
Write-Host "health_code: $healthCode" -ForegroundColor Gray
Write-Host "listener_count: $listenerCount" -ForegroundColor Gray
Write-Host "process_exists_count: $existingCount" -ForegroundColor Gray
Write-Host "backend_like_count: $backendLikeCount" -ForegroundColor Gray
Write-Host "ok_reason: $okReason" -ForegroundColor Gray
Write-Host "pass: $pass" -ForegroundColor Gray

if ($listeners.Count -gt 0) {
    Write-Host "--- listeners ---" -ForegroundColor Cyan
    foreach ($l in $listeners) {
        Write-Host ("pid={0} exists={1} backend_like={2}" -f $l.pid, $l.process_exists, $l.looks_like_backend) -ForegroundColor Gray
        if (-not [string]::IsNullOrWhiteSpace([string]$l.command_line)) {
            Write-Host ("  cmd: {0}" -f $l.command_line) -ForegroundColor DarkGray
        }
    }
}

if ($RequirePass.IsPresent -and -not $pass) {
    Write-Host "[ALERT] RPG backend port doctor detected anomaly" -ForegroundColor Red
    exit 1
}

exit 0
